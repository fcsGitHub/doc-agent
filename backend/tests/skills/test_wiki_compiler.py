"""Tests for WikiCompilerSkill."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from skills.wiki_compiler import WikiCompilerSkill
from skills.base import SkillContext


@pytest.fixture
def mock_llm():
    client = MagicMock()
    client.complete_json = AsyncMock(return_value={
        "articles": [
            {
                "title": "ISO 9001 Overview",
                "category": "standards",
                "content": "## ISO 9001\nQuality management system standard.",
                "summary": "ISO 9001 overview",
                "backlinks": [],
            }
        ]
    })
    return client


@pytest.mark.asyncio
async def test_compile_returns_articles(mock_llm):
    skill = WikiCompilerSkill()
    context = SkillContext(
        task_id="test",
        llm_client=mock_llm,
        input_data={
            "operation": "compile",
            "sources": [{"id": "src-1", "filename": "iso.md", "content": "ISO 9001 content"}],
        },
    )
    result = await skill.execute(context)
    assert result.success is True
    assert len(result.output["articles"]) == 1
    assert result.output["articles"][0]["title"] == "ISO 9001 Overview"


@pytest.mark.asyncio
async def test_query_returns_answer(mock_llm):
    mock_llm.complete_json = AsyncMock(return_value={
        "answer": "ISO 9001 is a quality management standard.",
        "source_article_ids": ["article-1"],
    })
    skill = WikiCompilerSkill()
    context = SkillContext(
        task_id="test",
        llm_client=mock_llm,
        input_data={
            "operation": "query",
            "question": "What is ISO 9001?",
            "articles": [{"id": "article-1", "title": "ISO 9001", "content": "Quality standard."}],
        },
    )
    result = await skill.execute(context)
    assert result.success is True
    assert "answer" in result.output


@pytest.mark.asyncio
async def test_unknown_operation_fails():
    skill = WikiCompilerSkill()
    context = SkillContext(
        task_id="test",
        input_data={"operation": "unknown"},
    )
    result = await skill.execute(context)
    assert result.success is False


@pytest.mark.asyncio
async def test_compile_empty_sources(mock_llm):
    skill = WikiCompilerSkill()
    context = SkillContext(
        task_id="test",
        llm_client=mock_llm,
        input_data={"operation": "compile", "sources": []},
    )
    result = await skill.execute(context)
    assert result.success is True
    assert result.output["articles"] == []
