"""Pydantic model for aggregated multi-reviewer results."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from review.schemas import ReviewResult


class AggregatedReview(BaseModel):
    """Aggregated output for one review round across all reviewers."""

    task_id: str
    document_id: str
    review_round: int
    reviewer_results: list[ReviewResult] = Field(default_factory=list)
    overall_status: str
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    info_count: int = 0
    overall_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_results(
        cls,
        task_id: str,
        document_id: str,
        review_round: int,
        results: list[ReviewResult],
    ) -> "AggregatedReview":
        """Create aggregated view from individual ReviewResult objects."""
        critical_count = 0
        major_count = 0
        minor_count = 0
        info_count = 0

        for result in results:
            critical_count += sum(1 for i in result.issues if i.severity == "critical")
            major_count += sum(1 for i in result.issues if i.severity == "major")
            minor_count += sum(1 for i in result.issues if i.severity == "minor")
            info_count += sum(1 for i in result.issues if i.severity == "info")

        if critical_count > 0:
            overall_status = "rejected"
        elif major_count > 0:
            overall_status = "needs_revision"
        else:
            overall_status = "approved"

        normalized_scores = [
            (float(r.score) / 100.0) if float(r.score) > 1.0 else float(r.score)
            for r in results
        ]
        overall_score = (
            sum(normalized_scores) / len(normalized_scores)
            if normalized_scores
            else 0.0
        )

        return cls(
            task_id=task_id,
            document_id=document_id,
            review_round=review_round,
            reviewer_results=results,
            overall_status=overall_status,
            critical_count=critical_count,
            major_count=major_count,
            minor_count=minor_count,
            info_count=info_count,
            overall_score=overall_score,
        )
