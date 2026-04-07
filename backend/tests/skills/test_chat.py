"""Tests for ChatSkill."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from skills.chat import ChatSkill, INTENT_EDIT, INTENT_STANDARD
from skills.base import SkillContext, SkillResult


@pytest.fixture
def mock_llm():
    client = MagicMock()
    client.complete_json = AsyncMock(return_value={
        "intent": INTENT_STANDARD,
        "reply": "已记录标准：ISO 9001",
        "standard_label": "ISO 9001",
        "standard_description": "Follow ISO 9001 quality management requirements",
        "section_id": None,
        "rewrite_instruction": None,
    })
    return client


@pytest.mark.asyncio
async def test_chat_skill_standard_intent(mock_llm):
    skill = ChatSkill()
    context = SkillContext(
        task_id="test-task",
        llm_client=mock_llm,
        input_data={
            "session_id": "session-1",
            "user_message": "按照 ISO 9001 标准审查",
            "history": [],
            "sections": [],
        },
    )
    result = await skill.execute(context)
    assert result.success is True
    assert result.output["intent"] == INTENT_STANDARD
    assert "reply" in result.output


@pytest.mark.asyncio
async def test_chat_skill_requires_llm_client():
    skill = ChatSkill()
    context = SkillContext(
        task_id="test-task",
        input_data={"session_id": "s", "user_message": "hi", "history": [], "sections": []},
    )
    result = await skill.execute(context)
    assert result.success is False
    assert "llm_client" in result.error


@pytest.mark.asyncio
async def test_chat_skill_edit_intent():
    client = MagicMock()
    client.complete_json = AsyncMock(return_value={
        "intent": INTENT_EDIT,
        "reply": "好的，我将修改该章节",
        "section_id": "sec-123",
        "rewrite_instruction": "Rewrite with more detail",
        "standard_label": None,
        "standard_description": None,
    })
    skill = ChatSkill()
    context = SkillContext(
        task_id="test-task",
        llm_client=client,
        input_data={
            "session_id": "s1",
            "user_message": "修改第一章，增加更多细节",
            "history": [],
            "sections": [{"id": "sec-123", "title": "第一章", "content": "内容"}],
        },
    )
    result = await skill.execute(context)
    assert result.success is True
    assert result.output["intent"] == INTENT_EDIT
    assert result.output["section_id"] == "sec-123"
