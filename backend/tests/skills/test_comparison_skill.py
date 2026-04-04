"""Tests for ComparisonSkill — compare section content against requirements or reference."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skills.base import SkillContext
from skills.comparison import ComparisonSkill


@pytest.fixture
def skill() -> ComparisonSkill:
    """Fresh ComparisonSkill instance."""
    return ComparisonSkill()


@pytest.fixture
def mock_llm_requirements() -> AsyncMock:
    """Mock LLM client returning a requirements_match comparison result."""
    llm = AsyncMock()
    llm.complete_json = AsyncMock(
        return_value={
            "coverage_score": 75,
            "missing_items": ["安全性要求未涵盖", "性能指标缺失"],
            "alignment_notes": "章节覆盖了大部分功能需求，但缺少非功能性需求。",
            "suggestions": ["添加安全性章节", "补充性能基准测试指标"],
        }
    )
    return llm


@pytest.fixture
def mock_llm_alignment() -> AsyncMock:
    """Mock LLM client returning a reference_alignment comparison result."""
    llm = AsyncMock()
    llm.complete_json = AsyncMock(
        return_value={
            "coverage_score": 90,
            "missing_items": ["术语表缺失"],
            "alignment_notes": "章节风格与参考文档高度一致，术语使用基本统一。",
            "suggestions": ["添加术语定义表"],
        }
    )
    return llm


@pytest.mark.asyncio
async def test_requirements_match(
    skill: ComparisonSkill,
    mock_llm_requirements: AsyncMock,
) -> None:
    """requirements_match comparison returns structured coverage report."""
    ctx = SkillContext(
        task_id="task-48",
        section_id="sec-001",
        llm_client=mock_llm_requirements,
        input_data={
            "section_content": "本系统提供用户管理、数据导入导出功能。",
            "reference_content": "系统需求：用户管理、数据导入导出、安全审计、性能监控。",
            "comparison_type": "requirements_match",
        },
    )

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["coverage_score"] == 75
    assert len(result.output["missing_items"]) == 2
    assert "安全性要求未涵盖" in result.output["missing_items"]
    assert isinstance(result.output["alignment_notes"], str)
    assert len(result.output["suggestions"]) == 2
    mock_llm_requirements.complete_json.assert_called_once()


@pytest.mark.asyncio
async def test_reference_alignment(
    skill: ComparisonSkill,
    mock_llm_alignment: AsyncMock,
) -> None:
    """reference_alignment comparison returns alignment report."""
    ctx = SkillContext(
        task_id="task-48",
        section_id="sec-002",
        llm_client=mock_llm_alignment,
        input_data={
            "section_content": "本文档遵循ISO 27001标准进行信息安全管理。",
            "reference_content": "参考文档：信息安全管理体系 ISO 27001 实施指南。",
            "comparison_type": "reference_alignment",
        },
    )

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["coverage_score"] == 90
    assert result.output["missing_items"] == ["术语表缺失"]
    assert "高度一致" in result.output["alignment_notes"]
    assert result.output["suggestions"] == ["添加术语定义表"]
    mock_llm_alignment.complete_json.assert_called_once()


@pytest.mark.asyncio
async def test_llm_error_returns_failure(
    skill: ComparisonSkill,
) -> None:
    """When LLM raises an exception, skill returns success=False without raising."""
    mock_llm = AsyncMock()
    mock_llm.complete_json = AsyncMock(
        side_effect=RuntimeError("LLM service unavailable")
    )

    ctx = SkillContext(
        task_id="task-48",
        section_id="sec-003",
        llm_client=mock_llm,
        input_data={
            "section_content": "一些内容。",
            "reference_content": "参考文档内容。",
            "comparison_type": "requirements_match",
        },
    )

    result = await skill.execute(ctx)

    assert result.success is False
    assert "LLM service unavailable" in (result.error or "")
    assert result.output == {}


@pytest.mark.asyncio
async def test_prompt_contains_inputs(
    skill: ComparisonSkill,
) -> None:
    """Verify the LLM prompt contains section_content, reference_content, and comparison_type."""
    mock_llm = AsyncMock()
    mock_llm.complete_json = AsyncMock(
        return_value={
            "coverage_score": 50,
            "missing_items": [],
            "alignment_notes": "部分对齐",
            "suggestions": [],
        }
    )

    ctx = SkillContext(
        task_id="task-48",
        section_id="sec-004",
        llm_client=mock_llm,
        input_data={
            "section_content": "UNIQUE_SECTION_MARKER",
            "reference_content": "UNIQUE_REFERENCE_MARKER",
            "comparison_type": "reference_alignment",
        },
    )

    await skill.execute(ctx)

    call_args = mock_llm.complete_json.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    if messages is None:
        messages = call_args[0][0] if call_args[0] else []

    user_msg = next((m for m in messages if m["role"] == "user"), None)
    assert user_msg is not None
    assert "UNIQUE_SECTION_MARKER" in user_msg["content"]
    assert "UNIQUE_REFERENCE_MARKER" in user_msg["content"]
    assert "reference_alignment" in user_msg["content"]


def test_registered_in_registry() -> None:
    """ComparisonSkill is registered in global registry as 'comparison'."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("comparison")
    registered = registry.get("comparison")
    assert isinstance(registered, ComparisonSkill)


def test_skill_name() -> None:
    """Skill name property returns 'comparison'."""
    skill = ComparisonSkill()
    assert skill.name == "comparison"
