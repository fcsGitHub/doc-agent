# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

from __future__ import annotations

import uuid
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.review_aggregation import AggregatedReview
from orchestrator.nodes import revise_sections_node, run_reviews_node
from orchestrator.state import DocumentState
from review.schemas import ReviewIssue, ReviewResult
from skills.base import SkillResult


def _base_state(**overrides: object) -> DocumentState:
    state: DocumentState = {
        "task_id": str(uuid.uuid4()),
        "current_phase": "reviewing",
        "section_ids": [],
        "current_section_index": 0,
        "outline_approved": True,
        "review_round": 0,
        "review_passed": False,
        "revision_needed_section_ids": [],
        "final_approved": False,
        "error": None,
        "progress_pct": 0,
        "progress_message": "start",
    }
    for key, value in overrides.items():
        state[key] = value  # type: ignore[index]
    return state


def _mock_execute_result(first: object = None):
    res = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = first
    res.scalars.return_value = scalars
    return res


def _aggregated(
    status: str, issues: list[ReviewIssue] | None = None
) -> AggregatedReview:
    review_result = ReviewResult(
        reviewer_name="structure",
        status="pass",
        issues=issues or [],
        summary="ok",
        score=90,
    )
    return AggregatedReview(
        task_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        review_round=1,
        reviewer_results=[review_result],
        overall_status=status,
    )


@pytest.mark.asyncio
async def test_run_reviews_approved() -> None:
    state = _base_state(review_round=1)
    parsed_doc = MagicMock(id=uuid.uuid4())

    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(first=parsed_doc))

    progress = MagicMock()
    progress.publish = AsyncMock()

    mock_service = MagicMock()
    mock_service.run_all_reviews = AsyncMock(return_value=_aggregated("approved"))

    with (
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
        patch("services.review_service.ReviewService", return_value=mock_service),
    ):
        result = await run_reviews_node(state, db, llm_client=AsyncMock())

    assert result["review_round"] == 2
    assert result["review_passed"] is True
    assert result["revision_needed_section_ids"] == []


@pytest.mark.asyncio
async def test_run_reviews_needs_revision() -> None:
    state = _base_state(review_round=0)
    parsed_doc = MagicMock(id=uuid.uuid4())
    sec_a = str(uuid.uuid4())
    sec_b = str(uuid.uuid4())

    issues = [
        ReviewIssue(
            severity="major",
            category="style",
            section_id=sec_a,
            description="issue a",
            suggestion="fix a",
            requires_human=False,
        ),
        ReviewIssue(
            severity="major",
            category="evidence",
            section_id=sec_b,
            description="issue b",
            suggestion="fix b",
            requires_human=False,
        ),
        ReviewIssue(
            severity="major",
            category="risk",
            section_id=sec_b,
            description="issue b2",
            suggestion="fix b2",
            requires_human=True,
        ),
    ]

    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(first=parsed_doc))

    progress = MagicMock()
    progress.publish = AsyncMock()

    mock_service = MagicMock()
    mock_service.run_all_reviews = AsyncMock(
        return_value=_aggregated("needs_revision", issues=issues)
    )

    with (
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
        patch("services.review_service.ReviewService", return_value=mock_service),
    ):
        result = await run_reviews_node(state, db, llm_client=AsyncMock())

    assert result["review_passed"] is False
    assert set(cast(list[str], result["revision_needed_section_ids"])) == {sec_a, sec_b}


@pytest.mark.asyncio
async def test_run_reviews_rejected() -> None:
    state = _base_state(review_round=2)
    parsed_doc = MagicMock(id=uuid.uuid4())

    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(first=parsed_doc))

    progress = MagicMock()
    progress.publish = AsyncMock()

    mock_service = MagicMock()
    mock_service.run_all_reviews = AsyncMock(return_value=_aggregated("rejected"))

    with (
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
        patch("services.review_service.ReviewService", return_value=mock_service),
    ):
        result = await run_reviews_node(state, db, llm_client=AsyncMock())

    assert result["review_round"] == 3
    assert result["review_passed"] is False
    assert result["revision_needed_section_ids"] == []


@pytest.mark.asyncio
async def test_revise_sections_calls_rewrite_skill() -> None:
    section_id = str(uuid.uuid4())
    state = _base_state(review_round=1, revision_needed_section_ids=[section_id])

    review_round_row = MagicMock(
        results={
            "reviewer_results": [
                {
                    "issues": [
                        {
                            "severity": "major",
                            "category": "style",
                            "section_id": section_id,
                            "description": "tighten wording",
                            "suggestion": "rewrite",
                            "requires_human": False,
                        }
                    ]
                }
            ]
        }
    )
    latest_version = MagicMock(version_number=1, content="old text")

    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _mock_execute_result(first=review_round_row),
            _mock_execute_result(first=latest_version),
        ]
    )
    db.flush = AsyncMock()

    mock_skill = MagicMock()
    mock_skill.execute = AsyncMock(
        return_value=SkillResult(
            success=True,
            output={"rewritten_content": "new polished text"},
        )
    )

    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
    ):
        mock_registry.return_value.get.return_value = mock_skill
        result = await revise_sections_node(state, db, llm_client=AsyncMock())

    assert result["current_phase"] == "revising"
    assert result["progress_pct"] == 70
    mock_skill.execute.assert_awaited_once()
    assert db.add.call_count == 1
    new_version = db.add.call_args[0][0]
    assert str(new_version.section_id) == section_id
    assert new_version.version_number == 2
    assert new_version.content == "new polished text"


@pytest.mark.asyncio
async def test_revise_sections_empty_list() -> None:
    state = _base_state(review_round=2, revision_needed_section_ids=[])
    db = MagicMock()

    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
    ):
        result = await revise_sections_node(state, db, llm_client=AsyncMock())

    assert result["current_phase"] == "revising"
    assert result["progress_pct"] == 70
    assert result["progress_message"] == "无需修订章节"
    mock_registry.assert_not_called()
