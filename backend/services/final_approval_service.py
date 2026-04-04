# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false
"""Service for final human approval after automated review rounds."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.approval import ApprovalRequest, ApprovalState
from models.audit import AuditEntry
from models.review_aggregation import AggregatedReview
from services.progress_service import ProgressEvent, get_progress_service
from services.review_service import ReviewService


class FinalApprovalService:
    """Read and submit final approval decisions for a task."""

    def __init__(self) -> None:
        self._review_service: ReviewService = ReviewService()

    async def get_approval_state(self, task_id: str, db: AsyncSession) -> ApprovalState:
        """Return current approval state derived from latest aggregated review."""
        latest_review = await self._review_service.get_latest_review(
            db=db, task_id=task_id
        )
        if latest_review is None:
            return ApprovalState(task_id=task_id, status="no_reviews")

        review_summary = self._build_review_summary(latest_review)
        pending_human_issues = self._collect_pending_human_issues(latest_review)

        return ApprovalState(
            task_id=task_id,
            status="awaiting_approval",
            review_summary=review_summary,
            pending_human_issues=pending_human_issues,
            created_at=latest_review.created_at,
        )

    async def submit_approval(
        self,
        task_id: str,
        request: ApprovalRequest,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Submit final human decision for review-completed tasks."""
        latest_review = await self._review_service.get_latest_review(
            db=db, task_id=task_id
        )
        if latest_review is None:
            raise HTTPException(
                status_code=400,
                detail="Reviews must be completed before approval",
            )

        progress_svc = get_progress_service()

        if request.action == "approve":
            await progress_svc.publish(
                task_id,
                ProgressEvent(
                    event_type="task_approved",
                    task_id=task_id,
                    phase="approval",
                    progress_pct=100,
                    message="Human approved final review output",
                ),
            )
            result: dict[str, Any] = {
                "message": "Document approved",
                "task_id": task_id,
                "action": "approve",
            }
        else:
            await progress_svc.publish(
                task_id,
                ProgressEvent(
                    event_type="changes_requested",
                    task_id=task_id,
                    phase="approval",
                    progress_pct=95,
                    message="Human requested additional changes",
                    data={"notes": request.notes} if request.notes else {},
                ),
            )
            result = {
                "message": "Changes requested, revision queued",
                "task_id": task_id,
                "action": "request_changes",
                "notes": request.notes,
            }

        await self._write_audit_entry(
            task_id=task_id,
            action=request.action,
            notes=request.notes,
            db=db,
        )
        return result

    def _build_review_summary(self, review: AggregatedReview) -> dict[str, Any]:
        return {
            "overall_status": review.overall_status,
            "overall_score": review.overall_score,
            "reviewer_count": len(review.reviewer_results),
            "critical_count": review.critical_count,
            "major_count": review.major_count,
            "minor_count": review.minor_count,
            "info_count": review.info_count,
        }

    def _collect_pending_human_issues(
        self, review: AggregatedReview
    ) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        for reviewer_result in review.reviewer_results:
            for issue in reviewer_result.issues:
                if issue.requires_human:
                    pending.append(issue.model_dump(mode="json"))
        return pending

    async def _write_audit_entry(
        self,
        task_id: str,
        action: str,
        notes: str | None,
        db: AsyncSession,
    ) -> None:
        """Best-effort audit logging for final approval decisions."""
        try:
            audit = AuditEntry(
                id=uuid.uuid4(),
                task_id=uuid.UUID(task_id),
                event_type="final_approval_decision",
                entity_type="final_approval",
                entity_id=task_id,
                details={"action": action, "notes": notes},
            )
            db.add(audit)
            await db.flush()
            await db.commit()
        except Exception:
            # Best effort only: approval flow should not fail because of audit write.
            pass
