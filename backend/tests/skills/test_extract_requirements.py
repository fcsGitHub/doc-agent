"""Tests for RequirementExtractionSkill — LLM-driven requirement extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from skills.base import SkillContext
from skills.extract_requirements import RequirementExtractionSkill


@pytest.fixture
def skill() -> RequirementExtractionSkill:
    """Fresh RequirementExtractionSkill instance."""
    return RequirementExtractionSkill()


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock LLM client with complete_json as AsyncMock."""
    llm = AsyncMock()
    return llm


@pytest.fixture
def ctx(mock_llm: AsyncMock) -> SkillContext:
    """SkillContext wired to mock LLM client."""
    return SkillContext(
        task_id="test-task-001",
        llm_client=mock_llm,
        input_data={
            "parsed_text": "系统必须支持用户登录。系统应支持批量导出。",
            "doc_type": "specification",
        },
    )


# ------------------------------------------------------------------
# Test 1: Successful extraction with 3 requirements
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extract_requirements_success(
    skill: RequirementExtractionSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """LLM returns 3 requirements — all parsed correctly."""
    mock_llm.complete_json.return_value = {
        "requirements": [
            {
                "id": "REQ-001",
                "description": "系统必须支持用户登录",
                "category": "functional",
                "priority": "must",
                "source_excerpt": "系统必须支持用户登录",
            },
            {
                "id": "REQ-002",
                "description": "系统应支持批量导出",
                "category": "functional",
                "priority": "should",
                "source_excerpt": "系统应支持批量导出",
            },
            {
                "id": "REQ-003",
                "description": "数据传输需加密",
                "category": "technical",
                "priority": "must",
                "source_excerpt": "数据传输需加密",
            },
        ],
        "constraints": ["必须兼容IE11", "响应时间<2s"],
        "key_terms": ["用户登录", "批量导出", "数据加密"],
    }

    result = await skill.execute(ctx)

    assert result.success is True
    assert len(result.output["requirements"]) == 3

    req0 = result.output["requirements"][0]
    assert req0["id"] == "REQ-001"
    assert req0["description"] == "系统必须支持用户登录"
    assert req0["category"] == "functional"
    assert req0["priority"] == "must"
    assert req0["source_excerpt"] == "系统必须支持用户登录"

    assert result.output["constraints"] == ["必须兼容IE11", "响应时间<2s"]
    assert len(result.output["key_terms"]) == 3
    assert "用户登录" in result.output["key_terms"]


# ------------------------------------------------------------------
# Test 2: Empty document — LLM returns empty lists
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extract_empty_document(
    skill: RequirementExtractionSkill,
    mock_llm: AsyncMock,
) -> None:
    """Empty doc: LLM returns no requirements, result is still success."""
    ctx = SkillContext(
        task_id="test-empty",
        llm_client=mock_llm,
        input_data={"parsed_text": "", "doc_type": "report"},
    )
    mock_llm.complete_json.return_value = {
        "requirements": [],
        "constraints": [],
        "key_terms": [],
    }

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["requirements"] == []
    assert result.output["constraints"] == []
    assert result.output["key_terms"] == []


# ------------------------------------------------------------------
# Test 3: Malformed LLM response — missing expected keys
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extract_handles_malformed_llm_response(
    skill: RequirementExtractionSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """LLM returns unexpected structure — graceful degradation to empty output."""
    mock_llm.complete_json.return_value = {"random_key": "random_value"}

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["requirements"] == []
    assert result.output["constraints"] == []
    assert result.output["key_terms"] == []


# ------------------------------------------------------------------
# Test 4: Skill registration in global registry
# ------------------------------------------------------------------
def test_skill_registration() -> None:
    """RequirementExtractionSkill is registered in the global registry."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("requirement_extraction")
    skill = registry.get("requirement_extraction")
    assert isinstance(skill, RequirementExtractionSkill)


# ------------------------------------------------------------------
# Test 5: doc_type included in prompt sent to LLM
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extract_includes_doc_type_in_prompt(
    skill: RequirementExtractionSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """Verify doc_type is included in the user message sent to LLM."""
    mock_llm.complete_json.return_value = {
        "requirements": [],
        "constraints": [],
        "key_terms": [],
    }

    await skill.execute(ctx)

    mock_llm.complete_json.assert_called_once()
    call_args = mock_llm.complete_json.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    if messages is None:
        messages = call_args[0][0] if call_args[0] else []

    # Find the user message
    user_msg = next((m for m in messages if m["role"] == "user"), None)
    assert user_msg is not None
    assert "specification" in user_msg["content"]
    assert "系统必须支持用户登录" in user_msg["content"]
