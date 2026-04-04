"""Tests for TechnicalReviewer — technical correctness checks."""

from unittest.mock import AsyncMock

import pytest

from review.schemas import ReviewConfig, ReviewResult, SectionData
from review.technical_reviewer import TechnicalReviewer


@pytest.fixture
def reviewer() -> TechnicalReviewer:
    return TechnicalReviewer()


@pytest.fixture
def config() -> ReviewConfig:
    return ReviewConfig(doc_type="report")


@pytest.mark.asyncio
async def test_logic_flaw_detected(
    reviewer: TechnicalReviewer,
    config: ReviewConfig,
) -> None:
    """Sections with logical gap → mock LLM returns critical issue → fail with category=technical."""
    sections = [
        SectionData(
            section_id="s1",
            title="系统架构",
            content="本系统采用微服务架构，但所有服务共享单一数据库且无隔离措施。",
            level=1,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "fail",
        "score": 20,
        "summary": "Document contains logical inconsistency in architecture claims.",
        "issues": [
            {
                "severity": "critical",
                "category": "technical",
                "section_id": "s1",
                "location_excerpt": "微服务架构，但所有服务共享单一数据库",
                "description": "声称采用微服务架构但共享单一数据库，存在逻辑矛盾",
                "suggestion": "澄清架构选型或说明数据库共享的合理性",
                "requires_human": False,
            }
        ],
    }

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "fail"
    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"
    assert result.issues[0].category == "technical"
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_sound_technical_document_passes(
    reviewer: TechnicalReviewer,
    config: ReviewConfig,
) -> None:
    """Well-argued technical document → status='pass', score=90, no issues."""
    sections = [
        SectionData(
            section_id="s1",
            title="性能优化方案",
            content=(
                "通过引入Redis缓存层，将数据库查询QPS从500降至50，"
                "缓存命中率达到90%。测试环境为4核8G云主机，"
                "使用JMeter进行压力测试，样本量10000次请求。"
            ),
            level=1,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "pass",
        "score": 90,
        "summary": "Technical content is well-supported with clear methodology and data.",
        "issues": [],
    }

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "pass"
    assert result.score == 90
    assert result.issues == []
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_bad_llm_response_graceful_fallback(
    reviewer: TechnicalReviewer,
    config: ReviewConfig,
) -> None:
    """LLM raises ValueError → graceful fallback: status=fail, score=0, category=technical."""
    sections = [
        SectionData(
            section_id="s1",
            title="概述",
            content="测试内容",
            level=1,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.side_effect = ValueError(
        "LLM returned invalid JSON: not valid json"
    )

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "fail"
    assert result.score == 0
    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"
    assert result.issues[0].category == "technical"


@pytest.mark.asyncio
async def test_prompt_contains_technical_criteria(
    reviewer: TechnicalReviewer,
) -> None:
    """Verify _build_prompt includes the Chinese technical criteria text."""
    sections = [
        SectionData(
            section_id="s1",
            title="Test",
            content="Test content",
            level=1,
            order_index=0,
        ),
    ]
    messages = reviewer._build_prompt(sections, reviewer.review_criteria)
    assert len(messages) == 2
    assert "检查技术正确性" in messages[0]["content"]
    assert "论证逻辑是否完整" in messages[0]["content"]
    assert "技术论述是否准确" in messages[0]["content"]
    assert "技术术语使用是否恰当" in messages[0]["content"]


@pytest.mark.asyncio
async def test_reviewer_registration() -> None:
    """TechnicalReviewer is registered in the skill registry at module load."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("technical")
    skill = registry.get("technical")
    assert isinstance(skill, TechnicalReviewer)
