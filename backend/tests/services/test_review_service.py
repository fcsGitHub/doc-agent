"""Unit tests for ReviewService orchestration + aggregation."""
# pyright: reportAny=false, reportExplicitAny=false, reportUnusedCallResult=false

from __future__ import annotations

import uuid
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from review.schemas import ReviewIssue, ReviewResult
from services.review_service import ReviewService
from skills.base import SkillResult


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


def _result(
    status: Literal["pass", "fail", "warning"] = "pass",
    score: int = 90,
    issues: list[ReviewIssue] | None = None,
) -> ReviewResult:
    return ReviewResult(
        reviewer_name="r",
        status=status,
        score=score,
        summary="ok",
        issues=issues or [],
    )


def _skill_result(rr: ReviewResult) -> SkillResult:
    return SkillResult(success=True, output=rr.model_dump())


def _reviewer(name: str, rr: ReviewResult) -> MagicMock:
    rv = MagicMock()
    rv.reviewer_name = name
    rv.execute = AsyncMock(return_value=_skill_result(rr))
    return rv


class TestReviewService:
    @pytest.mark.asyncio
    async def test_run_all_reviews_mixed_results(self):
        """6 pass, 1 major, 1 minor => needs_revision."""
        service = ReviewService()
        db = _mock_db()

        major_issue = ReviewIssue(
            severity="major",
            category="compliance",
            description="major",
            suggestion="fix",
        )
        minor_issue = ReviewIssue(
            severity="minor",
            category="style",
            description="minor",
            suggestion="fix",
        )

        reviewers = [_reviewer(f"r{i}", _result("pass", 90)) for i in range(6)]
        reviewers.append(_reviewer("r6", _result("warning", 80, [major_issue])))
        reviewers.append(_reviewer("r7", _result("warning", 85, [minor_issue])))

        with (
            patch.object(service, "_build_reviewers", return_value=reviewers),
            patch.object(
                service, "_load_sections_for_review", AsyncMock(return_value=[])
            ),
            patch("services.review_service.get_progress_service") as mock_get_progress,
        ):
            mock_progress = MagicMock()
            mock_progress.publish = AsyncMock()
            mock_get_progress.return_value = mock_progress

            aggregated = await service.run_all_reviews(
                task_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                review_round=1,
                db=db,
                llm_client=AsyncMock(),
            )

        assert aggregated.overall_status == "needs_revision"
        assert aggregated.major_count == 1
        assert aggregated.minor_count == 1

    @pytest.mark.asyncio
    async def test_critical_issue_forces_rejection(self):
        """Any critical issue forces rejected."""
        service = ReviewService()
        db = _mock_db()

        critical_issue = ReviewIssue(
            severity="critical",
            category="risk",
            description="critical",
            suggestion="fix",
        )

        reviewers = [_reviewer(f"r{i}", _result("pass", 95)) for i in range(7)]
        reviewers.append(_reviewer("risk", _result("fail", 30, [critical_issue])))

        with (
            patch.object(service, "_build_reviewers", return_value=reviewers),
            patch.object(
                service, "_load_sections_for_review", AsyncMock(return_value=[])
            ),
            patch("services.review_service.get_progress_service") as mock_get_progress,
        ):
            mock_progress = MagicMock()
            mock_progress.publish = AsyncMock()
            mock_get_progress.return_value = mock_progress

            aggregated = await service.run_all_reviews(
                task_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                review_round=1,
                db=db,
                llm_client=AsyncMock(),
            )

        assert aggregated.overall_status == "rejected"
        assert aggregated.critical_count == 1

    @pytest.mark.asyncio
    async def test_all_pass_approved(self):
        """All reviewers pass => approved."""
        service = ReviewService()
        db = _mock_db()
        reviewers = [_reviewer(f"r{i}", _result("pass", 100)) for i in range(8)]

        with (
            patch.object(service, "_build_reviewers", return_value=reviewers),
            patch.object(
                service, "_load_sections_for_review", AsyncMock(return_value=[])
            ),
            patch("services.review_service.get_progress_service") as mock_get_progress,
        ):
            mock_progress = MagicMock()
            mock_progress.publish = AsyncMock()
            mock_get_progress.return_value = mock_progress

            aggregated = await service.run_all_reviews(
                task_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                review_round=1,
                db=db,
                llm_client=AsyncMock(),
            )

        assert aggregated.overall_status == "approved"
        assert aggregated.critical_count == 0
        assert aggregated.major_count == 0
        assert aggregated.minor_count == 0

    @pytest.mark.asyncio
    async def test_sse_events_emitted(self):
        """Publishes review_started + 8 reviewer events + review_aggregated."""
        service = ReviewService()
        db = _mock_db()
        reviewers = [_reviewer(f"r{i}", _result("pass", 90)) for i in range(8)]

        with (
            patch.object(service, "_build_reviewers", return_value=reviewers),
            patch.object(
                service, "_load_sections_for_review", AsyncMock(return_value=[])
            ),
            patch("services.review_service.get_progress_service") as mock_get_progress,
        ):
            mock_progress = MagicMock()
            mock_progress.publish = AsyncMock()
            mock_get_progress.return_value = mock_progress

            await service.run_all_reviews(
                task_id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                review_round=1,
                db=db,
                llm_client=AsyncMock(),
            )

        assert mock_progress.publish.await_count == 10
        event_types = [
            call.args[1].event_type for call in mock_progress.publish.await_args_list
        ]
        assert event_types[0] == "review_started"
        assert event_types[-1] == "review_aggregated"
        assert event_types[1:9] == [f"reviewer_{i}_complete" for i in range(1, 9)]

    @pytest.mark.asyncio
    async def test_reviewer_failure_propagates(self):
        """Fail fast when one reviewer raises exception."""
        service = ReviewService()
        db = _mock_db()

        reviewers = [_reviewer("r1", _result("pass", 90)), _reviewer("r2", _result())]
        reviewers += [_reviewer(f"r{i}", _result("pass", 90)) for i in range(3, 9)]
        reviewers[1].execute = AsyncMock(side_effect=RuntimeError("boom"))

        with (
            patch.object(service, "_build_reviewers", return_value=reviewers),
            patch.object(
                service, "_load_sections_for_review", AsyncMock(return_value=[])
            ),
            patch("services.review_service.get_progress_service") as mock_get_progress,
        ):
            mock_progress = MagicMock()
            mock_progress.publish = AsyncMock()
            mock_get_progress.return_value = mock_progress

            with pytest.raises(RuntimeError, match="boom"):
                await service.run_all_reviews(
                    task_id=str(uuid.uuid4()),
                    document_id=str(uuid.uuid4()),
                    review_round=1,
                    db=db,
                    llm_client=AsyncMock(),
                )
