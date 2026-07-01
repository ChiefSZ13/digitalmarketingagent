"""Development-only read-only database inspector routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Query

from marketing_agent.api.dependencies import SettingsDep, get_analysis_repository
from marketing_agent.api.errors import ProblemException
from marketing_agent.api.security import AccessKeyDep
from marketing_agent.domain.models.analysis_memory import (
    AdminDbRecordResponse,
    AdminDbTableListResponse,
    AdminDbTableRowsResponse,
)
from marketing_agent.infrastructure.database.inspector import DatabaseInspector
from marketing_agent.infrastructure.persistence.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)

router = APIRouter(prefix="/admin/db", tags=["admin-db"])

RepositoryDep = Annotated[SqlAlchemyAnalysisRepository, Depends(get_analysis_repository)]


@router.get("/tables", response_model=AdminDbTableListResponse)
async def list_database_tables(
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> AdminDbTableListResponse:
    _require_inspector(settings)
    return await DatabaseInspector(repository.sessionmaker).list_tables()


@router.get("/tables/{table_name}", response_model=AdminDbTableRowsResponse)
async def list_database_table_rows(
    table_name: str,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> AdminDbTableRowsResponse:
    _require_inspector(settings)
    response = await DatabaseInspector(repository.sessionmaker).table_rows(
        table_name=table_name,
        limit=limit,
        offset=offset,
        search=search,
    )
    if response is None:
        _raise_not_found(table_name)
    return response


@router.get("/tables/{table_name}/{record_id}", response_model=AdminDbRecordResponse)
async def get_database_record(
    table_name: str,
    record_id: str,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> AdminDbRecordResponse:
    _require_inspector(settings)
    response = await DatabaseInspector(repository.sessionmaker).record(
        table_name=table_name,
        record_id=record_id,
    )
    if response is None:
        _raise_not_found(table_name)
    return response


def _require_inspector(settings: SettingsDep) -> None:
    if settings.persistence_enabled and settings.admin_db_inspector_enabled:
        return
    raise ProblemException(
        title="Database inspector is disabled",
        detail=(
            "Set PERSISTENCE_ENABLED=true and ADMIN_DB_INSPECTOR_ENABLED=true "
            "to use the read-only development database inspector."
        ),
        status_code=403,
        type_="https://example.local/errors/admin-db-disabled",
    )


def _raise_not_found(table_name: str) -> NoReturn:
    raise ProblemException(
        title="Database record not found",
        detail=f"No database inspector record exists for {table_name}.",
        status_code=404,
        type_="https://example.local/errors/not-found",
    )
