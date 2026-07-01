"""Async SQLAlchemy session factory helpers."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


@lru_cache
def get_database_engine_cached(
    database_url: str,
    echo: bool,
    pool_size: int,
    max_overflow: int,
) -> AsyncEngine:
    options: dict[str, object] = {
        "echo": echo,
        "pool_pre_ping": True,
    }
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if database_url.endswith(":memory:") or database_url.endswith(":memory:?cache=shared"):
            options["poolclass"] = StaticPool
    else:
        options["pool_size"] = pool_size
        options["max_overflow"] = max_overflow
    return create_async_engine(database_url, **options)


@lru_cache
def get_database_sessionmaker_cached(
    database_url: str,
    echo: bool,
    pool_size: int,
    max_overflow: int,
) -> async_sessionmaker[AsyncSession]:
    engine = get_database_engine_cached(database_url, echo, pool_size, max_overflow)
    return async_sessionmaker(engine, expire_on_commit=False)


async def dispose_database_engines() -> None:
    cached = get_database_engine_cached.cache_info()
    if cached.currsize == 0:
        return
    get_database_sessionmaker_cached.cache_clear()
    get_database_engine_cached.cache_clear()
