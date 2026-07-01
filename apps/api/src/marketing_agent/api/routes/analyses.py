"""Persistence-aware analysis history and report routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Query
from starlette import status

from marketing_agent.api.dependencies import SettingsDep, get_analysis_repository
from marketing_agent.api.errors import ProblemException
from marketing_agent.api.security import AccessKeyDep
from marketing_agent.config import Settings
from marketing_agent.domain.models.analysis_memory import (
    AnalysisDetail,
    AnalysisListResponse,
    AnalysisMarketplaceOverrideInput,
    ManualMatchOverrideRecordView,
)
from marketing_agent.domain.models.keyword import KeywordCandidate, KeywordIntelligence
from marketing_agent.domain.models.marketplace import MarketplaceSnapshot
from marketing_agent.domain.models.run import PerceptionRun
from marketing_agent.infrastructure.persistence.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])

RepositoryDep = Annotated[SqlAlchemyAnalysisRepository, Depends(get_analysis_repository)]


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    product_id: str | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    sort: str = "-created_at",
) -> AnalysisListResponse:
    _require_persistence(settings)
    return await repository.list_analyses(
        limit=limit,
        offset=offset,
        status=status_filter,
        product_id=product_id,
        search=search,
        created_after=created_after,
        created_before=created_before,
        sort=sort,
    )


@router.get("/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis_detail(
    analysis_id: str,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> AnalysisDetail:
    _require_persistence(settings)
    detail = await repository.get_analysis_detail(analysis_id)
    if detail is None:
        _raise_not_found(analysis_id)
    return detail


@router.get("/{analysis_id}/report", response_model=PerceptionRun)
async def get_analysis_report(
    analysis_id: str,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> PerceptionRun:
    _require_persistence(settings)
    report = await repository.get_report(analysis_id)
    if report is None:
        _raise_not_found(analysis_id)
    return report


@router.get("/{analysis_id}/marketplace", response_model=MarketplaceSnapshot)
async def get_analysis_marketplace(
    analysis_id: str,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> MarketplaceSnapshot:
    _require_persistence(settings)
    report = await repository.get_report(analysis_id)
    if report is None:
        _raise_not_found(analysis_id)
    return report.marketplace_snapshot


@router.get("/{analysis_id}/keywords")
async def get_analysis_keywords(
    analysis_id: str,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> dict[str, list[KeywordCandidate] | KeywordIntelligence]:
    _require_persistence(settings)
    report = await repository.get_report(analysis_id)
    if report is None:
        _raise_not_found(analysis_id)
    return {
        "keyword_candidates": report.keyword_candidates,
        "keyword_intelligence": report.keyword_intelligence,
    }


@router.post(
    "/{analysis_id}/marketplace/{observation_id}/override",
    response_model=ManualMatchOverrideRecordView,
    status_code=status.HTTP_201_CREATED,
)
async def create_marketplace_observation_override(
    analysis_id: str,
    observation_id: str,
    payload: AnalysisMarketplaceOverrideInput,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> ManualMatchOverrideRecordView:
    _require_persistence(settings)
    override = await repository.save_analysis_observation_override(
        analysis_id=analysis_id,
        observation_id=observation_id,
        payload=payload,
    )
    if override is None:
        _raise_not_found(analysis_id)
    return override


@router.get(
    "/{analysis_id}/marketplace/{observation_id}/overrides",
    response_model=list[ManualMatchOverrideRecordView],
)
async def list_marketplace_observation_overrides(
    analysis_id: str,
    observation_id: str,
    _access_key: AccessKeyDep,
    settings: SettingsDep,
    repository: RepositoryDep,
) -> list[ManualMatchOverrideRecordView]:
    _require_persistence(settings)
    overrides = await repository.list_observation_overrides(
        analysis_id=analysis_id,
        observation_id=observation_id,
    )
    if overrides is None:
        _raise_not_found(analysis_id)
    return overrides


def _require_persistence(settings: Settings) -> None:
    if settings.persistence_enabled:
        return
    raise ProblemException(
        title="Persistence is disabled",
        detail="Set PERSISTENCE_ENABLED=true and run database migrations to use analysis memory.",
        status_code=503,
        type_="https://example.local/errors/persistence-disabled",
    )


def _raise_not_found(analysis_id: str) -> NoReturn:
    raise ProblemException(
        title="Analysis not found",
        detail=f"No persisted analysis exists for ID {analysis_id}.",
        status_code=404,
        type_="https://example.local/errors/not-found",
    )
