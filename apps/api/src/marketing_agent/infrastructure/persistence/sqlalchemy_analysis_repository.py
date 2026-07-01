"""SQLAlchemy-backed product-intelligence repository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from marketing_agent.domain.models.analysis_memory import (
    AnalysisDetail,
    AnalysisListResponse,
    AnalysisMarketplaceOverrideInput,
    AnalysisSummary,
    ManualMatchOverrideRecordView,
    MarketplaceObservationRecord,
    ProductMatchResultRecordView,
    ProviderRunRecord,
)
from marketing_agent.domain.models.keyword import KeywordCandidate, KeywordIntelligenceKeyword
from marketing_agent.domain.models.marketplace import (
    MarketplaceListingValidation,
    MarketplaceReviewDecision,
    MarketplaceReviewOverride,
)
from marketing_agent.domain.models.run import (
    SCHEMA_VERSION,
    ImageInput,
    PerceptionRun,
    ProductAnalysisRequest,
)
from marketing_agent.domain.ports.artifact_repository import ArtifactRepository
from marketing_agent.infrastructure.database.models import (
    AnalysisRun,
    IntelligenceReportSnapshot,
    KeywordCandidateRecord,
    KeywordMetric,
    ManualMatchOverride,
    MarketplaceObservation,
    MediaAsset,
    Product,
    ProductMatchResultRecord,
    ProductProfileVersion,
    ProviderRun,
)

SECRET_KEYS = {"secret", "token", "api_key", "apikey", "authorization", "password"}
MAX_STORED_STRING_LENGTH = 4_000


class SqlAlchemyAnalysisRepository(ArtifactRepository):
    """Persist immutable report snapshots and normalized read rows."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        return self._sessionmaker

    async def start_analysis_run(
        self,
        *,
        run_id: str,
        analysis_run_id: str,
        request: ProductAnalysisRequest,
        images: list[ImageInput],
    ) -> None:
        analysis_uuid = _coerce_uuid(analysis_run_id)
        now = datetime.now(UTC)
        async with self._sessionmaker() as session:
            existing = await _get_analysis(session, analysis_uuid, run_id)
            if existing is not None:
                return
            analysis = AnalysisRun(
                id=analysis_uuid,
                run_id=run_id,
                product_id=None,
                status="running",
                input_description=request.description,
                input_payload_json={
                    "request": _json(request),
                    "images": [_json(image) for image in images],
                },
                started_at=now,
                completed_at=None,
                duration_ms=None,
                error_message=None,
                schema_version=SCHEMA_VERSION,
            )
            session.add(analysis)
            for image in images:
                session.add(_media_asset_from_image(image, analysis_uuid, None))
            await session.commit()

    async def mark_analysis_failed(
        self,
        *,
        run_id: str,
        analysis_run_id: str,
        error_message: str,
    ) -> None:
        analysis_uuid = _try_uuid(analysis_run_id)
        async with self._sessionmaker() as session:
            analysis = await _get_analysis(session, analysis_uuid, run_id)
            if analysis is None:
                return
            now = datetime.now(UTC)
            analysis.status = "failed"
            analysis.completed_at = now
            analysis.duration_ms = _duration_ms(analysis.started_at, now)
            analysis.error_message = _truncate(error_message, 1_000)
            await session.commit()

    async def save_run(self, run: PerceptionRun) -> None:
        analysis_uuid = _coerce_uuid(run.analysis_run_id)
        async with self._sessionmaker() as session, session.begin():
            analysis = await _get_analysis(session, analysis_uuid, run.run_id)
            if analysis is None:
                analysis = AnalysisRun(
                    id=analysis_uuid,
                    run_id=run.run_id,
                    product_id=None,
                    status="running",
                    input_description=run.request.description,
                    input_payload_json={"request": _json(run.request)},
                    started_at=run.created_at,
                    completed_at=None,
                    duration_ms=None,
                    error_message=None,
                    schema_version=run.schema_version,
                )
                session.add(analysis)
                await session.flush()

            await _delete_saved_children(session, analysis.id)
            product = _product_from_run(run)
            session.add(product)
            await session.flush()

            analysis.product_id = product.id
            analysis.status = "partial_success" if run.errors else "completed"
            analysis.completed_at = run.completed_at
            analysis.duration_ms = (
                _duration_ms(run.created_at, run.completed_at) if run.completed_at else None
            )
            analysis.error_message = "; ".join(run.errors) if run.errors else None
            analysis.schema_version = run.schema_version
            analysis.input_description = run.request.description
            analysis.input_payload_json = {
                "request": _json(run.request),
                "images": [_json(image) for image in run.images],
                "warnings": run.warnings,
                "errors": run.errors,
            }

            for image in run.images:
                session.add(_media_asset_from_image(image, analysis.id, product.id))

            session.add(
                ProductProfileVersion(
                    product_id=product.id,
                    analysis_run_id=analysis.id,
                    profile_version=_snapshot_version("product_profile", run.schema_version),
                    provider=run.metadata.provider,
                    model_name=run.metadata.model,
                    prompt_version=run.metadata.prompt_version,
                    profile_json=_json(run.product_profile),
                    confidence_summary_json={
                        "overall_confidence": run.product_profile.overall_confidence
                    },
                )
            )

            provider_run_ids = await self._save_provider_runs(session, analysis.id, run)
            marketplace_provider_run_id = _provider_run_id_for(
                provider_run_ids,
                provider=run.marketplace_snapshot.source_provider,
                provider_type="marketplace",
            )
            observation_ids = await self._save_marketplace_rows(
                session,
                analysis.id,
                marketplace_provider_run_id,
                run,
            )
            await self._save_keyword_rows(session, analysis.id, provider_run_ids, run)
            session.add(
                IntelligenceReportSnapshot(
                    analysis_run_id=analysis.id,
                    schema_version=_snapshot_version("full_report", run.schema_version),
                    report_json=_json(run),
                )
            )
            _ = observation_ids

    async def get_run(self, run_id: str) -> PerceptionRun | None:
        async with self._sessionmaker() as session:
            analysis = await _get_analysis(session, _try_uuid(run_id), run_id)
            if analysis is None:
                return None
            run = await self._get_report_for_analysis(session, analysis.id)
            if run is None:
                return None
            overrides = await self._latest_marketplace_overrides(session, analysis.id)
            return _with_marketplace_overrides(run, overrides)

    async def save_marketplace_override(
        self, override: MarketplaceReviewOverride
    ) -> MarketplaceReviewOverride:
        async with self._sessionmaker() as session, session.begin():
            analysis = await _get_analysis(session, _try_uuid(override.run_id), override.run_id)
            if analysis is None:
                raise ValueError(f"No analysis exists for run ID {override.run_id}.")
            observation = await self._get_observation_by_listing(
                session,
                analysis.id,
                override.listing_id,
            )
            if observation is None:
                raise ValueError(f"No listing exists for ID {override.listing_id}.")
            match_result_id = await self._latest_match_result_id(session, observation.id)
            row = ManualMatchOverride(
                analysis_run_id=analysis.id,
                marketplace_observation_id=observation.id,
                product_match_result_id=match_result_id,
                override_status=override.decision.value,
                override_relationship=None,
                override_eligible_for_price_aggregation=None,
                reason=override.note,
                created_by=override.reviewer,
            )
            session.add(row)
            await session.flush()
            created_at = row.created_at
        return MarketplaceReviewOverride(
            run_id=override.run_id,
            listing_id=override.listing_id,
            decision=override.decision,
            note=override.note,
            reviewer=override.reviewer,
            created_at=created_at,
            updated_at=created_at,
        )

    async def list_marketplace_overrides(self, run_id: str) -> list[MarketplaceReviewOverride]:
        async with self._sessionmaker() as session:
            analysis = await _get_analysis(session, _try_uuid(run_id), run_id)
            if analysis is None:
                return []
            return await self._latest_marketplace_overrides(session, analysis.id)

    async def list_analyses(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        product_id: str | None = None,
        search: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        sort: str = "-created_at",
    ) -> AnalysisListResponse:
        async with self._sessionmaker() as session:
            conditions: list[ColumnElement[bool]] = []
            if status:
                conditions.append(AnalysisRun.status == status)
            product_uuid = _try_uuid(product_id) if product_id else None
            if product_uuid is not None:
                conditions.append(AnalysisRun.product_id == product_uuid)
            if created_after is not None:
                conditions.append(AnalysisRun.created_at >= created_after)
            if created_before is not None:
                conditions.append(AnalysisRun.created_at <= created_before)
            if search:
                pattern = f"%{search.strip()}%"
                conditions.append(
                    or_(
                        AnalysisRun.input_description.ilike(pattern),
                        Product.display_name.ilike(pattern),
                        Product.brand.ilike(pattern),
                    )
                )

            stmt = select(AnalysisRun).outerjoin(Product, AnalysisRun.product_id == Product.id)
            count_stmt = select(func.count(AnalysisRun.id)).outerjoin(
                Product,
                AnalysisRun.product_id == Product.id,
            )
            if conditions:
                stmt = stmt.where(*conditions)
                count_stmt = count_stmt.where(*conditions)
            if sort in {"created_at", "+created_at"}:
                stmt = stmt.order_by(AnalysisRun.created_at.asc())
            elif sort == "status":
                stmt = stmt.order_by(AnalysisRun.status.asc(), AnalysisRun.created_at.desc())
            else:
                stmt = stmt.order_by(AnalysisRun.created_at.desc())
            rows = (await session.execute(stmt.offset(offset).limit(limit))).scalars().all()
            total = await session.scalar(count_stmt)
            summaries = [await self._summary_for_analysis(session, row) for row in rows]
        return AnalysisListResponse(
            items=summaries,
            total=int(total or 0),
            limit=limit,
            offset=offset,
        )

    async def get_analysis_detail(self, analysis_id: str) -> AnalysisDetail | None:
        async with self._sessionmaker() as session:
            analysis = await _get_analysis(session, _try_uuid(analysis_id), analysis_id)
            if analysis is None:
                return None
            summary = await self._summary_for_analysis(session, analysis)
            report = await self._get_report_for_analysis(session, analysis.id)
            if report is not None:
                overrides = await self._latest_marketplace_overrides(session, analysis.id)
                report = _with_marketplace_overrides(report, overrides)
            provider_runs = await self._provider_run_records(session, analysis.id)
            observations = await self._observation_records(session, analysis.id)
            match_results = await self._match_result_records(session, analysis.id)
            overrides = await self._manual_override_records(session, analysis.id)
        return AnalysisDetail(
            summary=summary,
            product_profile=report.product_profile if report else None,
            marketplace_snapshot=report.marketplace_snapshot if report else None,
            keyword_candidates=report.keyword_candidates if report else [],
            keyword_intelligence=report.keyword_intelligence if report else None,
            provider_runs=provider_runs,
            marketplace_observations=observations,
            match_results=match_results,
            manual_overrides=overrides,
            report=report,
        )

    async def get_report(self, analysis_id: str) -> PerceptionRun | None:
        async with self._sessionmaker() as session:
            analysis = await _get_analysis(session, _try_uuid(analysis_id), analysis_id)
            if analysis is None:
                return None
            report = await self._get_report_for_analysis(session, analysis.id)
            if report is None:
                return None
            overrides = await self._latest_marketplace_overrides(session, analysis.id)
            return _with_marketplace_overrides(report, overrides)

    async def save_analysis_observation_override(
        self,
        *,
        analysis_id: str,
        observation_id: str,
        payload: AnalysisMarketplaceOverrideInput,
    ) -> ManualMatchOverrideRecordView | None:
        analysis_uuid = _try_uuid(analysis_id)
        observation_uuid = _try_uuid(observation_id)
        if observation_uuid is None:
            return None
        async with self._sessionmaker() as session, session.begin():
            analysis = await _get_analysis(session, analysis_uuid, analysis_id)
            if analysis is None:
                return None
            observation = await session.get(MarketplaceObservation, observation_uuid)
            if observation is None or observation.analysis_run_id != analysis.id:
                return None
            match_result_id = await self._latest_match_result_id(session, observation.id)
            row = ManualMatchOverride(
                analysis_run_id=analysis.id,
                marketplace_observation_id=observation.id,
                product_match_result_id=match_result_id,
                override_status=payload.override_status.value,
                override_relationship=payload.override_relationship,
                override_eligible_for_price_aggregation=(
                    payload.override_eligible_for_price_aggregation
                ),
                reason=payload.reason,
                created_by=payload.created_by,
            )
            session.add(row)
            await session.flush()
            return _manual_override_view(row, observation.listing_id)

    async def list_observation_overrides(
        self,
        *,
        analysis_id: str,
        observation_id: str,
    ) -> list[ManualMatchOverrideRecordView] | None:
        analysis_uuid = _try_uuid(analysis_id)
        observation_uuid = _try_uuid(observation_id)
        if observation_uuid is None:
            return None
        async with self._sessionmaker() as session:
            analysis = await _get_analysis(session, analysis_uuid, analysis_id)
            if analysis is None:
                return None
            observation = await session.get(MarketplaceObservation, observation_uuid)
            if observation is None or observation.analysis_run_id != analysis.id:
                return None
            rows = (
                (
                    await session.execute(
                        select(ManualMatchOverride)
                        .where(ManualMatchOverride.marketplace_observation_id == observation.id)
                        .order_by(ManualMatchOverride.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
        return [_manual_override_view(row, observation.listing_id) for row in rows]

    async def _save_provider_runs(
        self,
        session: AsyncSession,
        analysis_id: UUID,
        run: PerceptionRun,
    ) -> dict[tuple[str, str], UUID]:
        ids: dict[tuple[str, str], UUID] = {}
        perception = ProviderRun(
            analysis_run_id=analysis_id,
            provider_name=run.metadata.provider,
            provider_type="perception",
            operation="analyze_product",
            status="success",
            request_hash=None,
            request_metadata_json={"prompt_version": run.metadata.prompt_version},
            response_metadata_json=_json(run.metadata),
            result_count=1,
            started_at=run.created_at,
            completed_at=run.completed_at,
            latency_ms=run.metadata.latency_ms,
            estimated_cost_usd=None,
            actual_cost_usd=None,
            error_type=None,
            error_message=None,
            correlation_id=run.metadata.request_id,
        )
        session.add(perception)
        await session.flush()
        ids[(perception.provider_type, perception.provider_name)] = perception.id

        for telemetry in run.provider_runs:
            provider_type = _provider_type_for_operation(telemetry.operation)
            provider_run = ProviderRun(
                analysis_run_id=analysis_id,
                provider_name=telemetry.provider,
                provider_type=provider_type,
                operation=telemetry.operation,
                status=_provider_status(telemetry.status.value),
                request_hash=None,
                request_metadata_json={"cache_status": telemetry.cache_status.value},
                response_metadata_json=_json(telemetry),
                result_count=telemetry.result_count,
                started_at=telemetry.started_at,
                completed_at=telemetry.completed_at,
                latency_ms=telemetry.latency_ms,
                estimated_cost_usd=_micros_to_usd(telemetry.cost_micros),
                actual_cost_usd=None,
                error_type=telemetry.error_category,
                error_message=None,
                correlation_id=telemetry.correlation_id,
            )
            session.add(provider_run)
            await session.flush()
            ids[(provider_type, telemetry.provider)] = provider_run.id
        return ids

    async def _save_marketplace_rows(
        self,
        session: AsyncSession,
        analysis_id: UUID,
        provider_run_id: UUID | None,
        run: PerceptionRun,
    ) -> dict[str, UUID]:
        observation_ids: dict[str, UUID] = {}
        summary = run.marketplace_snapshot.validation_summary
        scoring_policy_version = (
            summary.scoring_policy_version if summary else "product-match-scoring-v1"
        )
        normalization_version = (
            summary.normalization_version if summary else "marketplace-normalization-v1"
        )
        for validation in run.marketplace_snapshot.validated_listings:
            listing = validation.listing
            observation = MarketplaceObservation(
                analysis_run_id=analysis_id,
                provider_run_id=provider_run_id,
                provider_name=listing.provider,
                platform=listing.platform,
                listing_id=listing.listing_id,
                source_url=listing.source_url,
                title=listing.title,
                normalized_title=listing.normalized_title,
                seller_name=listing.seller_name,
                brand=listing.brand,
                manufacturer=listing.manufacturer,
                model_number=listing.model_number,
                condition=listing.condition.value if listing.condition else None,
                currency=listing.currency,
                item_price=_decimal_or_none(listing.item_price),
                shipping_price=_decimal_or_none(listing.shipping_price),
                landed_price=_decimal_or_none(listing.landed_price),
                stock_status=listing.stock_status,
                rating=_decimal_or_none(listing.rating),
                review_count=listing.review_count,
                rank_signals_json=_json(listing.raw_rank_signals),
                observed_at=listing.observed_at,
                raw_payload_json=_payload_reference(listing.raw_provider_payload_reference),
            )
            session.add(observation)
            await session.flush()
            observation_ids[listing.listing_id] = observation.id
            match = validation.match_result
            session.add(
                ProductMatchResultRecord(
                    analysis_run_id=analysis_id,
                    marketplace_observation_id=observation.id,
                    status=match.status.value,
                    relationship=match.relationship.value,
                    score=_decimal_or_none(match.score) or Decimal("0"),
                    eligible_for_price_aggregation=match.eligible_for_price_aggregation,
                    aggregation_group=match.aggregation_group,
                    matched_fields_json=_json(match.matched_fields),
                    unknown_fields_json=_json(match.unknown_fields),
                    conflicts_json=_json(match.conflicts),
                    feature_scores_json=_json(match.feature_scores),
                    reason_codes_json=_json(match.reason_codes),
                    human_summary=match.human_summary,
                    matcher_version=match.matcher_version,
                    scoring_policy_version=scoring_policy_version,
                    normalization_version=normalization_version,
                    created_at=match.created_at,
                )
            )
        return observation_ids

    async def _save_keyword_rows(
        self,
        session: AsyncSession,
        analysis_id: UUID,
        provider_run_ids: dict[tuple[str, str], UUID],
        run: PerceptionRun,
    ) -> None:
        cluster_by_keyword = _cluster_id_by_keyword(run)
        intelligence_by_normalized = {
            item.normalized_text: item for item in run.keyword_intelligence.keywords
        }
        for candidate in run.keyword_candidates:
            keyword_row = KeywordCandidateRecord(
                analysis_run_id=analysis_id,
                keyword=candidate.text,
                normalized_keyword=candidate.normalized_text,
                term_type=candidate.marketing_term_type.value,
                query_family=candidate.query_family.value,
                intent=candidate.intent.value,
                origin_json=_json(candidate.origins),
                product_relevance_score=_decimal_or_none(candidate.product_relevance_score),
                query_realism_score=_decimal_or_none(candidate.query_realism_score),
                commercial_intent_score=_decimal_or_none(candidate.commercial_intent_score),
                eligible_for_live_enrichment=candidate.eligible_for_live_enrichment,
                cluster_id=cluster_by_keyword.get(candidate.normalized_text),
                score_components_json=_json(candidate.score_components),
                rejection_reasons_json=_json(candidate.rejection_reasons),
                generator_version=candidate.generator_version,
            )
            session.add(keyword_row)
            await session.flush()
            intelligence = intelligence_by_normalized.get(candidate.normalized_text)
            metric = _keyword_metric_from_candidate(
                analysis_id=analysis_id,
                provider_run_ids=provider_run_ids,
                keyword_row_id=keyword_row.id,
                candidate=candidate,
                intelligence=intelligence,
            )
            if metric is not None:
                session.add(metric)

    async def _summary_for_analysis(
        self,
        session: AsyncSession,
        analysis: AnalysisRun,
    ) -> AnalysisSummary:
        product = await session.get(Product, analysis.product_id) if analysis.product_id else None
        marketplace_count = await session.scalar(
            select(func.count(MarketplaceObservation.id)).where(
                MarketplaceObservation.analysis_run_id == analysis.id
            )
        )
        match_count = await session.scalar(
            select(func.count(ProductMatchResultRecord.id)).where(
                ProductMatchResultRecord.analysis_run_id == analysis.id
            )
        )
        keyword_count = await session.scalar(
            select(func.count(KeywordCandidateRecord.id)).where(
                KeywordCandidateRecord.analysis_run_id == analysis.id
            )
        )
        provider_statuses = (
            (
                await session.execute(
                    select(ProviderRun.status).where(ProviderRun.analysis_run_id == analysis.id)
                )
            )
            .scalars()
            .all()
        )
        return AnalysisSummary(
            analysis_id=str(analysis.id),
            run_id=analysis.run_id,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
            product_name=product.display_name if product else None,
            brand=product.brand if product else None,
            status=analysis.status,
            marketplace_observation_count=int(marketplace_count or 0),
            validated_match_count=int(match_count or 0),
            keyword_count=int(keyword_count or 0),
            provider_status=_combined_provider_status(provider_statuses),
            duration_ms=analysis.duration_ms,
        )

    async def _get_report_for_analysis(
        self,
        session: AsyncSession,
        analysis_id: UUID,
    ) -> PerceptionRun | None:
        snapshot = (
            await session.execute(
                select(IntelligenceReportSnapshot)
                .where(IntelligenceReportSnapshot.analysis_run_id == analysis_id)
                .order_by(IntelligenceReportSnapshot.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if snapshot is None:
            return None
        return PerceptionRun.model_validate(snapshot.report_json)

    async def _latest_marketplace_overrides(
        self,
        session: AsyncSession,
        analysis_id: UUID,
    ) -> list[MarketplaceReviewOverride]:
        rows = (
            await session.execute(
                select(ManualMatchOverride, MarketplaceObservation)
                .join(
                    MarketplaceObservation,
                    ManualMatchOverride.marketplace_observation_id == MarketplaceObservation.id,
                )
                .where(ManualMatchOverride.analysis_run_id == analysis_id)
                .order_by(ManualMatchOverride.created_at.asc())
            )
        ).all()
        latest: dict[str, tuple[ManualMatchOverride, MarketplaceObservation]] = {}
        for override, observation in rows:
            latest[observation.listing_id] = (override, observation)
        analysis = await session.get(AnalysisRun, analysis_id)
        run_id = analysis.run_id if analysis else str(analysis_id)
        return [
            MarketplaceReviewOverride(
                run_id=run_id,
                listing_id=observation.listing_id,
                decision=MarketplaceReviewDecision(override.override_status),
                note=override.reason,
                reviewer=override.created_by or "manual",
                created_at=override.created_at,
                updated_at=override.created_at,
            )
            for override, observation in latest.values()
        ]

    async def _get_observation_by_listing(
        self,
        session: AsyncSession,
        analysis_id: UUID,
        listing_id: str,
    ) -> MarketplaceObservation | None:
        return (
            await session.execute(
                select(MarketplaceObservation).where(
                    MarketplaceObservation.analysis_run_id == analysis_id,
                    MarketplaceObservation.listing_id == listing_id,
                )
            )
        ).scalar_one_or_none()

    async def _latest_match_result_id(
        self,
        session: AsyncSession,
        observation_id: UUID,
    ) -> UUID | None:
        row = (
            await session.execute(
                select(ProductMatchResultRecord.id)
                .where(ProductMatchResultRecord.marketplace_observation_id == observation_id)
                .order_by(ProductMatchResultRecord.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def _provider_run_records(
        self,
        session: AsyncSession,
        analysis_id: UUID,
    ) -> list[ProviderRunRecord]:
        rows = (
            (
                await session.execute(
                    select(ProviderRun)
                    .where(ProviderRun.analysis_run_id == analysis_id)
                    .order_by(ProviderRun.started_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return [
            ProviderRunRecord(
                id=str(row.id),
                provider_name=row.provider_name,
                provider_type=row.provider_type,
                operation=row.operation,
                status=row.status,
                result_count=row.result_count,
                started_at=row.started_at,
                completed_at=row.completed_at,
                latency_ms=row.latency_ms,
                estimated_cost_usd=float(row.estimated_cost_usd)
                if row.estimated_cost_usd is not None
                else None,
                actual_cost_usd=float(row.actual_cost_usd)
                if row.actual_cost_usd is not None
                else None,
                error_type=row.error_type,
                error_message=row.error_message,
                correlation_id=row.correlation_id,
            )
            for row in rows
        ]

    async def _observation_records(
        self,
        session: AsyncSession,
        analysis_id: UUID,
    ) -> list[MarketplaceObservationRecord]:
        rows = (
            (
                await session.execute(
                    select(MarketplaceObservation)
                    .where(MarketplaceObservation.analysis_run_id == analysis_id)
                    .order_by(MarketplaceObservation.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return [
            MarketplaceObservationRecord(
                id=str(row.id),
                provider_name=row.provider_name,
                platform=row.platform,
                listing_id=row.listing_id,
                source_url=row.source_url,
                title=row.title,
                normalized_title=row.normalized_title,
                brand=row.brand,
                manufacturer=row.manufacturer,
                model_number=row.model_number,
                condition=row.condition,
                currency=row.currency,
                item_price=float(row.item_price) if row.item_price is not None else None,
                landed_price=float(row.landed_price) if row.landed_price is not None else None,
                observed_at=row.observed_at,
            )
            for row in rows
        ]

    async def _match_result_records(
        self,
        session: AsyncSession,
        analysis_id: UUID,
    ) -> list[ProductMatchResultRecordView]:
        rows = (
            (
                await session.execute(
                    select(ProductMatchResultRecord)
                    .where(ProductMatchResultRecord.analysis_run_id == analysis_id)
                    .order_by(ProductMatchResultRecord.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        return [
            ProductMatchResultRecordView(
                id=str(row.id),
                marketplace_observation_id=str(row.marketplace_observation_id),
                status=row.status,
                relationship=row.relationship,
                score=float(row.score),
                eligible_for_price_aggregation=row.eligible_for_price_aggregation,
                aggregation_group=row.aggregation_group,
                human_summary=row.human_summary,
                matcher_version=row.matcher_version,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def _manual_override_records(
        self,
        session: AsyncSession,
        analysis_id: UUID,
    ) -> list[ManualMatchOverrideRecordView]:
        rows = (
            await session.execute(
                select(ManualMatchOverride, MarketplaceObservation)
                .join(
                    MarketplaceObservation,
                    ManualMatchOverride.marketplace_observation_id == MarketplaceObservation.id,
                )
                .where(ManualMatchOverride.analysis_run_id == analysis_id)
                .order_by(ManualMatchOverride.created_at.desc())
            )
        ).all()
        return [_manual_override_view(row, observation.listing_id) for row, observation in rows]


async def _get_analysis(
    session: AsyncSession,
    analysis_id: UUID | None,
    run_id: str | None,
) -> AnalysisRun | None:
    if analysis_id is not None:
        row = await session.get(AnalysisRun, analysis_id)
        if row is not None:
            return row
    if run_id:
        return (
            await session.execute(select(AnalysisRun).where(AnalysisRun.run_id == run_id))
        ).scalar_one_or_none()
    return None


async def _delete_saved_children(session: AsyncSession, analysis_id: UUID) -> None:
    await session.execute(
        delete(ManualMatchOverride).where(ManualMatchOverride.analysis_run_id == analysis_id)
    )
    await session.execute(delete(KeywordMetric).where(KeywordMetric.analysis_run_id == analysis_id))
    await session.execute(
        delete(KeywordCandidateRecord).where(KeywordCandidateRecord.analysis_run_id == analysis_id)
    )
    await session.execute(
        delete(ProductMatchResultRecord).where(
            ProductMatchResultRecord.analysis_run_id == analysis_id
        )
    )
    await session.execute(
        delete(MarketplaceObservation).where(MarketplaceObservation.analysis_run_id == analysis_id)
    )
    await session.execute(delete(ProviderRun).where(ProviderRun.analysis_run_id == analysis_id))
    await session.execute(
        delete(ProductProfileVersion).where(ProductProfileVersion.analysis_run_id == analysis_id)
    )
    await session.execute(
        delete(IntelligenceReportSnapshot).where(
            IntelligenceReportSnapshot.analysis_run_id == analysis_id
        )
    )
    await session.execute(delete(MediaAsset).where(MediaAsset.analysis_run_id == analysis_id))


def _product_from_run(run: PerceptionRun) -> Product:
    identity = run.marketplace_snapshot.product_identity
    display_name = (
        identity.product_name
        if identity is not None
        else _linked_value(run.product_profile.product_name) or "Unknown product"
    )
    brand = (
        identity.brand
        if identity is not None and identity.brand
        else _linked_value(run.product_profile.brand)
    )
    return Product(
        display_name=display_name,
        brand=brand,
        manufacturer=identity.manufacturer if identity else None,
        model_number=identity.model_number if identity else None,
        category=identity.category if identity else _linked_value(run.product_profile.category),
        product_type=identity.product_type if identity else None,
        normalized_name=identity.normalized_product_name if identity else display_name.lower(),
        gtin=identity.gtin if identity else None,
        upc=identity.upc if identity else None,
        ean=identity.ean if identity else None,
        asin=identity.asin if identity else None,
        metadata_json={
            "schema_version": _snapshot_version("product", run.schema_version),
            "marketplace_search_query": _linked_value(run.product_profile.marketplace_search_query),
        },
    )


def _media_asset_from_image(
    image: ImageInput,
    analysis_id: UUID,
    product_id: UUID | None,
) -> MediaAsset:
    return MediaAsset(
        product_id=product_id,
        analysis_run_id=analysis_id,
        asset_type="image",
        filename=image.filename,
        mime_type=image.mime_type,
        size_bytes=image.byte_size,
        width=image.width,
        height=image.height,
        duration_seconds=None,
        storage_uri=None,
        content_hash=image.content_hash,
        metadata_json={"index": image.index},
    )


def _keyword_metric_from_candidate(
    *,
    analysis_id: UUID,
    provider_run_ids: dict[tuple[str, str], UUID],
    keyword_row_id: UUID,
    candidate: KeywordCandidate,
    intelligence: KeywordIntelligenceKeyword | None,
) -> KeywordMetric | None:
    enrichment = candidate.enrichment
    provider = enrichment.provider or (
        intelligence.metrics.provider if intelligence and intelligence.metrics else None
    )
    if not provider:
        return None
    metrics = intelligence.metrics if intelligence else None
    provider_run_id = _provider_run_id_for(
        provider_run_ids,
        provider=provider,
        provider_type="keyword",
    )
    cpc_low = (
        enrichment.cpc_low
        if enrichment.cpc_low is not None
        else metrics.cpc_low
        if metrics
        else None
    )
    cpc_high = (
        enrichment.cpc_high
        if enrichment.cpc_high is not None
        else metrics.cpc_high
        if metrics
        else None
    )
    cpc_value = _average_optional(cpc_low, cpc_high)
    collected_at = enrichment.retrieved_at or (metrics.retrieved_at if metrics else None)
    return KeywordMetric(
        keyword_candidate_id=keyword_row_id,
        analysis_run_id=analysis_id,
        provider_run_id=provider_run_id,
        provider_name=provider,
        keyword=candidate.text,
        normalized_keyword=candidate.normalized_text,
        country_code=enrichment.market or (metrics.market if metrics else "US"),
        language_code=enrichment.language or (metrics.language if metrics else "en"),
        currency_code=enrichment.currency or (metrics.currency if metrics else None),
        average_monthly_searches=(
            enrichment.average_monthly_searches
            if enrichment.average_monthly_searches is not None
            else metrics.average_monthly_searches
            if metrics
            else None
        ),
        cpc_value=_decimal_or_none(cpc_value),
        low_top_of_page_bid=_decimal_or_none(cpc_low),
        high_top_of_page_bid=_decimal_or_none(cpc_high),
        paid_competition=enrichment.competition_level
        or (metrics.competition.value if metrics and metrics.competition else None),
        competition_index=_decimal_or_none(metrics.competition_index if metrics else None),
        trend_direction=enrichment.trend or (metrics.trend_direction.value if metrics else None),
        monthly_history_json=_json(metrics.monthly_history if metrics else []),
        collected_at=collected_at or datetime.now(UTC),
        expires_at=(collected_at or datetime.now(UTC)) + timedelta(days=30),
        raw_payload_json=_payload_reference(enrichment.provider_record_id),
    )


def _with_marketplace_overrides(
    run: PerceptionRun,
    overrides: list[MarketplaceReviewOverride],
) -> PerceptionRun:
    overrides_by_listing = {override.listing_id: override for override in overrides}
    validations: list[MarketplaceListingValidation] = []
    for validation in run.marketplace_snapshot.validated_listings:
        validations.append(
            validation.model_copy(
                update={"manual_override": overrides_by_listing.get(validation.listing.listing_id)}
            )
        )
    snapshot = run.marketplace_snapshot.model_copy(
        update={
            "manual_overrides": overrides,
            "validated_listings": validations,
        }
    )
    return run.model_copy(update={"marketplace_snapshot": snapshot})


def _manual_override_view(
    row: ManualMatchOverride,
    listing_id: str,
) -> ManualMatchOverrideRecordView:
    return ManualMatchOverrideRecordView(
        id=str(row.id),
        marketplace_observation_id=str(row.marketplace_observation_id),
        listing_id=listing_id,
        override_status=row.override_status,
        override_relationship=row.override_relationship,
        override_eligible_for_price_aggregation=row.override_eligible_for_price_aggregation,
        reason=row.reason,
        created_by=row.created_by,
        created_at=row.created_at,
    )


def _json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return _sanitize(value)


def _sanitize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _sanitize(value.model_dump(mode="json"))
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in cast(dict[Any, Any], value).items():
            key_text = str(key)
            if _is_secret_key(key_text):
                sanitized[key_text] = "[redacted]"
            else:
                sanitized[key_text] = _sanitize(child)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(child) for child in cast(list[Any], value)[:250]]
    if isinstance(value, str):
        return _truncate(value, MAX_STORED_STRING_LENGTH)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}..."


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in SECRET_KEYS or lowered.endswith(("_secret", "_token", "_password"))


def _coerce_uuid(value: str | None) -> UUID:
    if value is None:
        return uuid4()
    parsed = _try_uuid(value)
    return parsed or uuid4()


def _try_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _linked_value(value: Any) -> str | None:
    return value.value if value is not None else None


def _duration_ms(started_at: datetime, completed_at: datetime | None) -> int | None:
    if completed_at is None:
        return None
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    if completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=UTC)
    return max(0, int((completed_at - started_at).total_seconds() * 1000))


def _decimal_or_none(value: Decimal | float | int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _micros_to_usd(value: int | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value) / Decimal(1_000_000)


def _provider_status(value: str) -> str:
    return "success" if value == "succeeded" else value


def _provider_type_for_operation(operation: str) -> str:
    lowered = operation.lower()
    if "marketplace" in lowered or "shopping" in lowered:
        return "marketplace"
    if "keyword" in lowered:
        return "keyword"
    if "perception" in lowered or "model" in lowered:
        return "model"
    return "other"


def _provider_run_id_for(
    ids: dict[tuple[str, str], UUID],
    *,
    provider: str,
    provider_type: str,
) -> UUID | None:
    return ids.get((provider_type, provider)) or ids.get((provider_type, provider.lower()))


def _payload_reference(reference: str | None) -> dict[str, Any] | None:
    if not reference:
        return None
    return {"reference": _truncate(reference, 500)}


def _snapshot_version(name: str, schema_version: str) -> str:
    return f"{name}:{schema_version}"


def _cluster_id_by_keyword(run: PerceptionRun) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for cluster in run.keyword_clusters:
        for keyword in cluster.member_keywords:
            mapping[keyword.lower()] = cluster.id
    return mapping


def _average_optional(first: float | None, second: float | None) -> float | None:
    values = [value for value in (first, second) if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _combined_provider_status(statuses: Sequence[str]) -> str:
    if not statuses:
        return "none"
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "partial_success" for status in statuses):
        return "partial_success"
    if all(status in {"success", "succeeded", "skipped"} for status in statuses):
        return "success"
    return "unknown"
