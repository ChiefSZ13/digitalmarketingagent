"""Read-only database inspector for local development."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import String, Text, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from marketing_agent.domain.models.analysis_memory import (
    AdminDbRecordResponse,
    AdminDbTableListResponse,
    AdminDbTableRowsResponse,
    AdminDbTableSummary,
)
from marketing_agent.infrastructure.database.models import Base

SECRET_KEYS = {"secret", "token", "api_key", "apikey", "authorization", "password"}


class DatabaseInspector:
    """Small read-only inspector over the declared product-memory tables."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def list_tables(self) -> AdminDbTableListResponse:
        async with self._sessionmaker() as session:
            tables: list[AdminDbTableSummary] = []
            for name, table in sorted(Base.metadata.tables.items()):
                count = await session.scalar(select(func.count()).select_from(table))
                tables.append(
                    AdminDbTableSummary(
                        name=name,
                        columns=[column.name for column in table.columns],
                        record_count=int(count or 0),
                    )
                )
        return AdminDbTableListResponse(tables=tables)

    async def table_rows(
        self,
        *,
        table_name: str,
        limit: int,
        offset: int,
        search: str | None = None,
    ) -> AdminDbTableRowsResponse | None:
        table = Base.metadata.tables.get(table_name)
        if table is None:
            return None
        stmt = select(table)
        count_stmt = select(func.count()).select_from(table)
        if search:
            search_clause = _search_clause(table, search)
            if search_clause is not None:
                stmt = stmt.where(search_clause)
                count_stmt = count_stmt.where(search_clause)
        primary_key = list(table.primary_key.columns)
        if primary_key:
            stmt = stmt.order_by(primary_key[0].desc())
        stmt = stmt.offset(offset).limit(limit)
        async with self._sessionmaker() as session:
            total = await session.scalar(count_stmt)
            rows = (await session.execute(stmt)).mappings().all()
        return AdminDbTableRowsResponse(
            table_name=table_name,
            columns=[column.name for column in table.columns],
            rows=[_serialize_mapping(dict(row)) for row in rows],
            total=int(total or 0),
            limit=limit,
            offset=offset,
        )

    async def record(
        self,
        *,
        table_name: str,
        record_id: str,
    ) -> AdminDbRecordResponse | None:
        table = Base.metadata.tables.get(table_name)
        if table is None:
            return None
        primary_key = list(table.primary_key.columns)
        if not primary_key:
            return None
        pk = primary_key[0]
        value: object = _try_uuid(record_id) or record_id
        stmt = select(table).where(pk == value).limit(1)
        async with self._sessionmaker() as session:
            row = (await session.execute(stmt)).mappings().first()
        if row is None:
            return None
        return AdminDbRecordResponse(
            table_name=table_name,
            record=_serialize_mapping(dict(row)),
        )


def _search_clause(table: Any, search: str) -> Any:
    pattern = f"%{search.strip()}%"
    columns = [column for column in table.columns if isinstance(column.type, (String, Text))]
    if not columns:
        return None
    return or_(*(sql_cast(column, String).ilike(pattern) for column in columns))


def _serialize_mapping(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize_value(key, value) for key, value in row.items()}


def _serialize_value(key: str, value: Any) -> Any:
    if _is_secret_key(key):
        return "[redacted]"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {
            str(child_key): _serialize_value(str(child_key), child)
            for child_key, child in cast(dict[Any, Any], value).items()
        }
    if isinstance(value, list):
        return [_serialize_value(key, child) for child in cast(list[Any], value)]
    return value


def _try_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in SECRET_KEYS or lowered.endswith(("_secret", "_token", "_password"))
