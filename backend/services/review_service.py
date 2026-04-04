"""Review service — orchestrates all 8 reviewers and aggregation."""
# pyright: reportExplicitAny=false, reportAny=false

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.review import ReviewRound
from models.review_aggregation import AggregatedReview
from models.section import Section, SectionVersion
from review.compliance_reviewer import ComplianceReviewer
from review.consistency_reviewer import ConsistencyReviewer
from review.coverage_reviewer import CoverageReviewer
from review.evidence_reviewer import EvidenceReviewer
from review.risk_reviewer import RiskReviewer
from review.base import BaseReviewer
from review.schemas import ReviewResult
from review.structure_reviewer import StructureReviewer
from review.style_reviewer import StyleReviewer
from review.technical_reviewer import TechnicalReviewer
from services.progress_service import ProgressEvent, get_progress_service
from services.audit_service import AuditService
from skills.base import SkillContext, SkillResult


class ReviewService:
    """Service that runs full review rounds and aggregates reviewer outputs."""

    _audit = AuditService()

    async def run_all_reviews(
        self,
        task_id: str,
        document_id: str,
        review_round: int,
        db: AsyncSession,
        llm_client: object,
    ) -> AggregatedReview:
        """Run all 8 reviewers sequentially, aggregate, emit progress, persist round."""
        progress_svc = get_progress_service()
        await progress_svc.publish(
            task_id,
            ProgressEvent(
                event_type="review_started",
                task_id=task_id,
                phase="review",
                progress_pct=0,
                message=f"Review round {review_round} started",
                data={"document_id": document_id, "review_round": review_round},
            ),
        )

        sections = await self._load_sections_for_review(db, task_id)
        context = SkillContext(
            task_id=task_id,
            section_id=None,
            llm_client=llm_client,
            db_session=db,
            input_data={"sections": sections, "config": {}},
        )

        reviewers = self._build_reviewers()

        raw_results: list[SkillResult | BaseException] = list(
            await asyncio.gather(
                *[reviewer.execute(context) for reviewer in reviewers],
                return_exceptions=True,
            )
        )

        reviewer_results: list[ReviewResult] = []
        for reviewer, raw in zip(reviewers, raw_results):
            if isinstance(raw, BaseException):
                raise RuntimeError(
                    f"Reviewer '{reviewer.reviewer_name}' raised: {raw}"
                ) from raw
            skill_result: SkillResult = raw
            if not skill_result.success:
                raise RuntimeError(
                    skill_result.error
                    or f"Reviewer '{reviewer.reviewer_name}' execution failed"
                )
            reviewer_results.append(ReviewResult(**skill_result.output))

        await progress_svc.publish(
            task_id,
            ProgressEvent(
                event_type="all_reviewers_complete",
                task_id=task_id,
                phase="review",
                progress_pct=90,
                message="All reviewers complete",
                data={"reviewer_count": len(reviewers)},
            ),
        )

        aggregated = AggregatedReview.from_results(
            task_id=task_id,
            document_id=document_id,
            review_round=review_round,
            results=reviewer_results,
        )

        await self._persist_review_round(db, aggregated)

        await progress_svc.publish(
            task_id,
            ProgressEvent(
                event_type="review_aggregated",
                task_id=task_id,
                phase="review",
                progress_pct=100,
                message=f"Review round {review_round} aggregated",
                data={"overall_status": aggregated.overall_status},
            ),
        )

        # Best-effort audit logging
        try:
            await self._audit.log(
                db,
                task_id=task_id,
                action="review_completed",
                entity_type="review_round",
                entity_id=str(review_round),
                details={"overall_status": aggregated.overall_status},
            )
        except Exception:
            pass

        return aggregated

    async def get_review_round(
        self,
        db: AsyncSession,
        task_id: str,
        review_round: int,
    ) -> AggregatedReview | None:
        """Return aggregated review for a specific round."""
        stmt = select(ReviewRound).where(
            ReviewRound.task_id == uuid.UUID(task_id),
            ReviewRound.round_number == review_round,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._deserialize_round(row)

    async def get_latest_review(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> AggregatedReview | None:
        """Return latest aggregated review for a task."""
        stmt = (
            select(ReviewRound)
            .where(ReviewRound.task_id == uuid.UUID(task_id))
            .order_by(ReviewRound.round_number.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._deserialize_round(row)

    def _build_reviewers(self) -> list[BaseReviewer]:
        """Instantiate all 8 reviewers explicitly (fixed MVP order)."""
        return [
            StructureReviewer(),
            ComplianceReviewer(),
            TechnicalReviewer(),
            EvidenceReviewer(),
            ConsistencyReviewer(),
            StyleReviewer(),
            CoverageReviewer(),
            RiskReviewer(),
        ]

    async def _load_sections_for_review(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> list[dict[str, object]]:
        """Load section payload (with latest content) consumed by reviewers."""
        sections_stmt = (
            select(Section)
            .where(Section.task_id == uuid.UUID(task_id))
            .order_by(Section.order_index)
        )
        sections_result = await db.execute(sections_stmt)
        sections = list(sections_result.scalars().all())

        if not sections:
            return []

        section_ids = [s.id for s in sections]
        versions_stmt = select(SectionVersion).where(
            SectionVersion.section_id.in_(section_ids)
        )
        versions_result = await db.execute(versions_stmt)
        versions = list(versions_result.scalars().all())

        versions_by_section: dict[uuid.UUID, list[SectionVersion]] = defaultdict(list)
        for version in versions:
            versions_by_section[version.section_id].append(version)

        section_payload: list[dict[str, object]] = []
        for section in sections:
            latest_content = ""
            section_versions = versions_by_section.get(section.id, [])
            if section_versions:
                latest_version = max(section_versions, key=lambda v: v.version_number)
                latest_content = latest_version.content

            section_payload.append(
                {
                    "section_id": str(section.id),
                    "title": section.title,
                    "content": latest_content,
                    "level": section.level,
                    "order_index": section.order_index,
                }
            )

        return section_payload

    async def _persist_review_round(
        self,
        db: AsyncSession,
        aggregated: AggregatedReview,
    ) -> None:
        """Persist aggregated review to review_rounds table."""
        total_issues = (
            aggregated.critical_count
            + aggregated.major_count
            + aggregated.minor_count
            + aggregated.info_count
        )
        row = ReviewRound(
            task_id=uuid.UUID(aggregated.task_id),
            round_number=aggregated.review_round,
            overall_status=aggregated.overall_status,
            overall_score=int(round(aggregated.overall_score * 100)),
            total_issues=total_issues,
            critical_count=aggregated.critical_count,
            major_count=aggregated.major_count,
            minor_count=aggregated.minor_count,
            summary=(
                f"status={aggregated.overall_status}; "
                f"critical={aggregated.critical_count}; "
                f"major={aggregated.major_count}; "
                f"minor={aggregated.minor_count}; "
                f"info={aggregated.info_count}"
            ),
            results=aggregated.model_dump(mode="json"),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)

    def _deserialize_round(self, row: ReviewRound) -> AggregatedReview:
        """Deserialize persisted JSON back to AggregatedReview."""
        payload = row.results or {}
        if payload:
            return AggregatedReview.model_validate(payload)

        # Backward-compatible fallback if results JSON was absent.
        return AggregatedReview(
            task_id=str(row.task_id),
            document_id="",
            review_round=row.round_number,
            reviewer_results=[],
            overall_status=row.overall_status,
            critical_count=row.critical_count,
            major_count=row.major_count,
            minor_count=row.minor_count,
            info_count=0,
            overall_score=float(row.overall_score) / 100.0,
            created_at=row.created_at,
        )
