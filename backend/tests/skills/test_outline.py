"""Tests for OutlinePlanningSkill — LLM-driven document outline generation."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skills.base import SkillContext
from skills.outline import OutlinePlanningSkill


@pytest.fixture
def skill() -> OutlinePlanningSkill:
    """Fresh OutlinePlanningSkill instance."""
    return OutlinePlanningSkill()


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock LLM client with complete_json as AsyncMock."""
    llm = AsyncMock()
    return llm


@pytest.fixture
def ctx(mock_llm: AsyncMock) -> SkillContext:
    """SkillContext wired to mock LLM client with sample requirements."""
    return SkillContext(
        task_id="test-task-outline",
        llm_client=mock_llm,
        input_data={
            "requirements": [
                {"id": "REQ-001", "description": "系统必须支持用户登录"},
                {"id": "REQ-002", "description": "系统应支持批量导出"},
                {"id": "REQ-003", "description": "数据传输需加密"},
            ],
            "doc_type": "report",
        },
    )


# ------------------------------------------------------------------
# Test 1: Successful outline generation with nested sections
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_outline_generation_success(
    skill: OutlinePlanningSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """LLM returns 1 root section with 4 children — all parsed correctly."""
    mock_llm.complete_json.return_value = {
        "sections": [
            {
                "title": "技术方案报告",
                "level": 1,
                "description": "完整的技术方案报告",
                "target_word_count": 2000,
                "depends_on": [],
                "children": [
                    {
                        "title": "概述",
                        "level": 2,
                        "description": "项目背景与目标",
                        "target_word_count": 500,
                        "depends_on": [],
                        "children": [],
                    },
                    {
                        "title": "需求分析",
                        "level": 2,
                        "description": "功能需求与非功能需求",
                        "target_word_count": 600,
                        "depends_on": ["概述"],
                        "children": [],
                    },
                    {
                        "title": "技术方案",
                        "level": 2,
                        "description": "技术选型与架构设计",
                        "target_word_count": 800,
                        "depends_on": ["需求分析"],
                        "children": [],
                    },
                    {
                        "title": "风险分析",
                        "level": 2,
                        "description": "风险识别与应对策略",
                        "target_word_count": 400,
                        "depends_on": ["技术方案"],
                        "children": [],
                    },
                ],
            }
        ]
    }

    result = await skill.execute(ctx)

    assert result.success is True
    sections = result.output["sections"]
    assert len(sections) == 1

    root = sections[0]
    assert root["title"] == "技术方案报告"
    assert root["level"] == 1
    assert root["description"] == "完整的技术方案报告"
    assert root["target_word_count"] == 2000

    children = root["children"]
    assert len(children) == 4

    for child in children:
        assert "title" in child
        assert "level" in child
        assert "description" in child
        assert "target_word_count" in child
        assert child["level"] == 2

    assert children[0]["title"] == "概述"
    assert children[2]["depends_on"] == ["需求分析"]


# ------------------------------------------------------------------
# Test 2: Empty requirements — LLM returns minimal outline
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_outline_empty_requirements(
    skill: OutlinePlanningSkill,
    mock_llm: AsyncMock,
) -> None:
    """Empty requirements: LLM returns minimal outline with 1 section."""
    ctx = SkillContext(
        task_id="test-empty-reqs",
        llm_client=mock_llm,
        input_data={"requirements": [], "doc_type": "report"},
    )
    mock_llm.complete_json.return_value = {
        "sections": [
            {
                "title": "文档概要",
                "level": 1,
                "description": "基本文档结构",
                "target_word_count": 500,
                "depends_on": [],
                "children": [],
            }
        ]
    }

    result = await skill.execute(ctx)

    assert result.success is True
    sections = result.output["sections"]
    assert len(sections) == 1
    assert sections[0]["title"] == "文档概要"


# ------------------------------------------------------------------
# Test 3: Template-constrained outline — template passed to LLM prompt
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_outline_template_constrained(
    skill: OutlinePlanningSkill,
    mock_llm: AsyncMock,
) -> None:
    """Template schema with required_sections is included in the LLM prompt."""
    ctx = SkillContext(
        task_id="test-template",
        llm_client=mock_llm,
        input_data={
            "requirements": [{"id": "REQ-001", "description": "基本功能"}],
            "doc_type": "proposal",
            "template_schema": {
                "required_sections": ["概述", "技术方案", "风险分析"],
            },
        },
    )
    mock_llm.complete_json.return_value = {
        "sections": [
            {
                "title": "概述",
                "level": 1,
                "description": "项目概述",
                "target_word_count": 500,
                "depends_on": [],
                "children": [],
            },
            {
                "title": "技术方案",
                "level": 1,
                "description": "技术方案设计",
                "target_word_count": 800,
                "depends_on": ["概述"],
                "children": [],
            },
            {
                "title": "风险分析",
                "level": 1,
                "description": "风险评估",
                "target_word_count": 400,
                "depends_on": ["技术方案"],
                "children": [],
            },
        ]
    }

    result = await skill.execute(ctx)

    assert result.success is True

    # Verify template info was passed to LLM prompt
    mock_llm.complete_json.assert_called_once()
    call_args = mock_llm.complete_json.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    if messages is None:
        messages = call_args[0][0] if call_args[0] else []

    user_msg = next((m for m in messages if m["role"] == "user"), None)
    assert user_msg is not None
    assert "概述" in user_msg["content"]
    assert "技术方案" in user_msg["content"]
    assert "风险分析" in user_msg["content"]
    assert "模板要求的章节" in user_msg["content"]


# ------------------------------------------------------------------
# Test 4: Skill registration in global registry
# ------------------------------------------------------------------
def test_skill_registration() -> None:
    """OutlinePlanningSkill is registered in the global registry."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("outline_planning")
    skill = registry.get("outline_planning")
    assert isinstance(skill, OutlinePlanningSkill)


# ------------------------------------------------------------------
# Test 5: Malformed LLM response — sections is not a list
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_outline_handles_malformed_llm_response(
    skill: OutlinePlanningSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """LLM returns malformed response — graceful degradation to empty sections."""
    mock_llm.complete_json.return_value = {"sections": "not a list"}

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["sections"] == []
