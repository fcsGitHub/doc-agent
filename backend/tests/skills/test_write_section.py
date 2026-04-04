"""Tests for SectionWritingSkill — LLM-driven section content writing."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from skills.base import SkillContext
from skills.write_section import SectionWritingSkill


@pytest.fixture
def skill() -> SectionWritingSkill:
    """Fresh SectionWritingSkill instance."""
    return SectionWritingSkill()


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Mock LLM client with complete as AsyncMock."""
    llm = AsyncMock()
    llm.complete = AsyncMock(
        return_value=MagicMock(content="这是 一个 测试 段落", tokens_used=100)
    )
    return llm


@pytest.fixture
def ctx(mock_llm: AsyncMock) -> SkillContext:
    """SkillContext for section writing tests."""
    return SkillContext(
        task_id="task-15",
        section_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        llm_client=mock_llm,
        input_data={
            "task_id": "task-15",
            "section_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "section_title": "系统架构设计",
            "section_description": "说明系统整体架构与关键组件。",
            "target_word_count": 300,
            "context": {
                "requirements": ["支持高并发", "具备可观测性"],
                "preceding_sections": [
                    {"title": "背景", "summary": "介绍项目目标与范围。"}
                ],
                "style_guide": "正式、简洁",
                "knowledge_excerpts": ["采用分层架构", "关键链路需监控"],
            },
        },
    )


@pytest.mark.asyncio
async def test_write_section_basic(
    skill: SectionWritingSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """LLM returns content; output contains content/word_count/references_used."""
    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["content"] == "这是 一个 测试 段落"
    assert result.output["word_count"] == 4
    assert result.output["references_used"] == []
    assert result.tokens_used == 100
    mock_llm.complete.assert_called_once()


@pytest.mark.asyncio
async def test_write_section_with_db(
    skill: SectionWritingSkill,
    ctx: SkillContext,
) -> None:
    """When db_session exists, SectionVersion is added and flushed."""
    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    ctx.db_session = mock_db

    result = await skill.execute(ctx)

    assert result.success is True
    mock_db.add.assert_called_once()
    mock_db.flush.assert_awaited_once()

    section_version = mock_db.add.call_args[0][0]
    assert section_version.change_source == "generation"
    assert section_version.change_summary == "初始生成 — 系统架构设计"
    assert section_version.content == "这是 一个 测试 段落"
    assert section_version.word_count == 4


@pytest.mark.asyncio
async def test_write_section_with_context(
    skill: SectionWritingSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """Requirements and preceding section summaries are embedded in prompt."""
    await skill.execute(ctx)

    mock_llm.complete.assert_called_once()
    call_args = mock_llm.complete.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    if messages is None:
        messages = call_args[0][0] if call_args[0] else []

    user_msg = next((m for m in messages if m["role"] == "user"), None)
    assert user_msg is not None
    content = user_msg["content"]

    assert "章节标题：系统架构设计" in content
    assert "文档需求：" in content
    assert "- 支持高并发" in content
    assert "前序章节摘要：" in content
    assert "- 背景: 介绍项目目标与范围。" in content
    assert "写作风格要求：正式、简洁" in content


def test_write_section_registration() -> None:
    """SectionWritingSkill is registered in global registry."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("section_writing")
    registered = registry.get("section_writing")
    assert isinstance(registered, SectionWritingSkill)


@pytest.mark.asyncio
async def test_write_section_llm_error_returns_graceful_success(
    skill: SectionWritingSkill,
    ctx: SkillContext,
    mock_llm: AsyncMock,
) -> None:
    """LLM failure degrades gracefully with success=True and empty content."""
    mock_llm.complete = AsyncMock(side_effect=RuntimeError("llm unavailable"))

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output == {"content": "", "word_count": 0, "references_used": []}
    assert "llm unavailable" in (result.error or "")
