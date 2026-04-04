"""Tests for real async LangGraph generation pipeline nodes."""
# pyright: reportAny=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedCallResult=false

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestrator.state import DocumentState
from orchestrator.nodes import (
    extract_requirements_node,
    generate_sections_node,
    parse_node,
)
from skills.base import SkillResult


def _base_state(**overrides: object) -> DocumentState:
    state: DocumentState = {
        "task_id": str(uuid.uuid4()),
        "current_phase": "parsing",
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


def _mock_execute_result(first: object = None, all_values: list[object] | None = None):
    res = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = first
    scalars.all.return_value = all_values or []
    res.scalars.return_value = scalars
    return res


@pytest.mark.asyncio
async def test_parse_node_calls_skill() -> None:
    """parse_node calls document_parse skill and returns state update."""
    task_id = str(uuid.uuid4())
    state = _base_state(task_id=task_id)

    source_doc = MagicMock(
        id=uuid.uuid4(),
        file_path="/tmp/input.md",
        file_type="md",
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(first=source_doc))
    db.flush = AsyncMock()

    mock_skill = MagicMock()
    mock_skill.execute = AsyncMock(
        return_value=SkillResult(
            success=True, output={"raw_text": "ok"}, tokens_used=22
        )
    )
    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
    ):
        mock_registry.return_value.get.return_value = mock_skill
        result = await parse_node(state, db, llm_client=MagicMock())

    assert result["current_phase"] == "parsing"
    assert result["progress_pct"] == 10
    assert result["progress_message"] == "文档解析完成"
    mock_skill.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_parse_node_records_skill_execution() -> None:
    """parse_node creates SkillExecution record in DB."""
    state = _base_state()
    source_doc = MagicMock(
        id=uuid.uuid4(),
        file_path="/tmp/input.md",
        file_type="md",
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(first=source_doc))
    db.flush = AsyncMock()

    mock_skill = MagicMock()
    mock_skill.execute = AsyncMock(
        return_value=SkillResult(
            success=True, output={"raw_text": "ok"}, tokens_used=50
        )
    )
    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
    ):
        mock_registry.return_value.get.return_value = mock_skill
        await parse_node(state, db, llm_client=MagicMock())

    assert db.add.call_count == 1
    execution = db.add.call_args[0][0]
    assert execution.skill_name == "document_parse"
    assert execution.status == "completed"
    assert execution.tokens_used == 50
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_generate_sections_node_iterates() -> None:
    """generate_sections_node calls section_writing once per section."""
    task_id = str(uuid.uuid4())
    state = _base_state(task_id=task_id)
    section_a = MagicMock(
        id=uuid.uuid4(),
        title="A",
        description="desc A",
        target_word_count=120,
        order_index=0,
    )
    section_b = MagicMock(
        id=uuid.uuid4(),
        title="B",
        description="desc B",
        target_word_count=140,
        order_index=1,
    )

    db = MagicMock()
    db.execute = AsyncMock(
        return_value=_mock_execute_result(all_values=[section_a, section_b])
    )
    db.flush = AsyncMock()

    mock_skill = MagicMock()
    mock_skill.execute = AsyncMock(
        side_effect=[
            SkillResult(success=True, output={"content": "first"}, tokens_used=10),
            SkillResult(success=True, output={"content": "second"}, tokens_used=20),
        ]
    )
    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
    ):
        mock_registry.return_value.get.return_value = mock_skill
        result = await generate_sections_node(state, db, llm_client=MagicMock())

    assert mock_skill.execute.await_count == 2
    assert result["current_phase"] == "generating"
    assert result["progress_pct"] == 90
    assert result["current_section_index"] == 2


@pytest.mark.asyncio
async def test_parse_node_publishes_sse_events() -> None:
    """parse_node publishes progress events to ProgressService."""
    state = _base_state()
    source_doc = MagicMock(
        id=uuid.uuid4(),
        file_path="/tmp/input.md",
        file_type="md",
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(first=source_doc))
    db.flush = AsyncMock()

    mock_skill = MagicMock()
    mock_skill.execute = AsyncMock(return_value=SkillResult(success=True, output={}))
    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
    ):
        mock_registry.return_value.get.return_value = mock_skill
        await parse_node(state, db, llm_client=MagicMock())

    assert progress.publish.await_count >= 2
    first_event = progress.publish.await_args_list[0].args[1]
    second_event = progress.publish.await_args_list[1].args[1]
    assert first_event.event_type == "phase_change"
    assert first_event.progress_pct == 5
    assert second_event.progress_pct == 10


@pytest.mark.asyncio
async def test_extract_requirements_node() -> None:
    """extract_requirements_node calls requirement_extraction skill."""
    task_id = str(uuid.uuid4())
    state = _base_state(task_id=task_id)

    parsed = MagicMock(raw_text="parsed body")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(first=parsed))
    db.flush = AsyncMock()

    mock_skill = MagicMock()
    mock_skill.execute = AsyncMock(
        return_value=SkillResult(
            success=True, output={"requirements": []}, tokens_used=8
        )
    )
    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
    ):
        mock_registry.return_value.get.return_value = mock_skill
        result = await extract_requirements_node(state, db, llm_client=MagicMock())

    assert result["current_phase"] == "extracting"
    assert result["progress_pct"] == 20
    assert mock_skill.execute.await_count == 1


@pytest.mark.asyncio
async def test_generate_sections_node_returns_error_on_failed_skill() -> None:
    """generate_sections_node returns error state when skill fails."""
    task_id = str(uuid.uuid4())
    state = _base_state(task_id=task_id)
    section = MagicMock(
        id=uuid.uuid4(),
        title="Only Section",
        description="desc",
        target_word_count=100,
        order_index=0,
    )

    db = MagicMock()
    db.execute = AsyncMock(return_value=_mock_execute_result(all_values=[section]))
    db.flush = AsyncMock()

    mock_skill = MagicMock()
    mock_skill.execute = AsyncMock(
        return_value=SkillResult(success=False, output={}, error="boom")
    )
    progress = MagicMock()
    progress.publish = AsyncMock()

    with (
        patch("orchestrator.nodes.get_skill_registry") as mock_registry,
        patch("orchestrator.nodes.get_progress_service", return_value=progress),
    ):
        mock_registry.return_value.get.return_value = mock_skill
        result = await generate_sections_node(state, db, llm_client=MagicMock())

    assert result["current_phase"] == "generating"
    assert result["error"] == "boom"
