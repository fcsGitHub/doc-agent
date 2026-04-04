"""Tests for RewriteSkill — rewrite section content based on review issues."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from skills.base import SkillContext
from skills.rewrite import RewriteSkill


@pytest.fixture
def skill() -> RewriteSkill:
    """Fresh RewriteSkill instance."""
    return RewriteSkill()


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock LLM client with complete as AsyncMock."""
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=MagicMock(content="重写后的优质内容。", tokens_used=80)
    )
    return llm


@pytest.fixture
def ctx(mock_llm: AsyncMock) -> SkillContext:
    """SkillContext for rewrite tests with one auto-fixable issue."""
    return SkillContext(
        task_id="task-28",
        section_id="sec-001",
        llm_client=mock_llm,
        input_data={
            "section_id": "sec-001",
            "section_content": "这是一段需要修改的原始内容。存在一些表述不清的问题。",
            "issues": [
                {
                    "issue_id": "iss-1",
                    "reviewer": "style_reviewer",
                    "severity": "major",
                    "description": "段落表述不够清晰",
                    "suggestion": "建议重新组织段落结构",
                    "requires_human": False,
                },
            ],
        },
    )


@pytest.mark.asyncio
async def test_rewrite_basic(
    skill: RewriteSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """LLM rewrites content; output contains rewritten_content and addressed count."""
    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["rewritten_content"] == "重写后的优质内容。"
    assert result.output["addressed_issues"] == 1
    assert result.output["skipped_human_required"] == []
    assert result.tokens_used == 80
    mock_llm.complete.assert_called_once()


@pytest.mark.asyncio
async def test_skip_human_required_issues(
    skill: RewriteSkill,
    mock_llm: AsyncMock,
) -> None:
    """Human-required issues are skipped; only auto-fixable ones reach the LLM prompt."""
    ctx = SkillContext(
        task_id="task-28",
        section_id="sec-002",
        llm_client=mock_llm,
        input_data={
            "section_id": "sec-002",
            "section_content": "原始章节内容，存在多种问题。",
            "issues": [
                {
                    "issue_id": "iss-a",
                    "reviewer": "technical_reviewer",
                    "severity": "major",
                    "description": "技术术语使用不当",
                    "suggestion": "使用标准术语",
                    "requires_human": False,
                },
                {
                    "issue_id": "iss-b",
                    "reviewer": "compliance_reviewer",
                    "severity": "critical",
                    "description": "涉及法律合规风险",
                    "suggestion": "需要法务审核",
                    "requires_human": True,
                },
                {
                    "issue_id": "iss-c",
                    "reviewer": "style_reviewer",
                    "severity": "minor",
                    "description": "格式不统一",
                    "suggestion": "统一标题层级",
                    "requires_human": False,
                },
            ],
        },
    )

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["addressed_issues"] == 2
    assert result.output["skipped_human_required"] == ["iss-b"]

    # Verify LLM prompt only contains the 2 auto-fixable issues
    call_args = mock_llm.complete.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    if messages is None:
        messages = call_args[0][0] if call_args[0] else []

    user_msg = next((m for m in messages if m["role"] == "user"), None)
    assert user_msg is not None
    prompt_content = user_msg["content"]

    # Auto-fixable issues should be present
    assert "技术术语使用不当" in prompt_content
    assert "格式不统一" in prompt_content
    # Human-required issue should NOT be in the prompt
    assert "涉及法律合规风险" not in prompt_content


@pytest.mark.asyncio
async def test_llm_error_returns_failure(
    skill: RewriteSkill,
    mock_llm: AsyncMock,
) -> None:
    """When LLM raises an exception, skill returns success=False without raising."""
    mock_llm.complete = AsyncMock(side_effect=RuntimeError("LLM service down"))

    ctx = SkillContext(
        task_id="task-28",
        section_id="sec-003",
        llm_client=mock_llm,
        input_data={
            "section_id": "sec-003",
            "section_content": "内容。",
            "issues": [
                {
                    "issue_id": "iss-x",
                    "reviewer": "reviewer",
                    "severity": "minor",
                    "description": "问题",
                    "suggestion": "修改",
                    "requires_human": False,
                },
            ],
        },
    )

    result = await skill.execute(ctx)

    assert result.success is False
    assert "LLM service down" in (result.error or "")
    assert result.output == {}


def test_registered_in_registry() -> None:
    """RewriteSkill is registered in global registry as 'rewrite_polish'."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("rewrite_polish")
    registered = registry.get("rewrite_polish")
    assert isinstance(registered, RewriteSkill)
