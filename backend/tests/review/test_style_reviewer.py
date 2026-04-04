"""Tests for StyleReviewer — writing style and tone consistency checks."""

from unittest.mock import AsyncMock

import pytest

from review.schemas import ReviewConfig, ReviewResult, SectionData
from review.style_reviewer import StyleReviewer


@pytest.fixture
def reviewer() -> StyleReviewer:
    return StyleReviewer()


@pytest.fixture
def config() -> ReviewConfig:
    return ReviewConfig(doc_type="report")


@pytest.mark.asyncio
async def test_informal_tone_flagged(
    reviewer: StyleReviewer,
    config: ReviewConfig,
) -> None:
    """Section with casual informal Chinese → flagged with category=style, severity=major."""
    sections = [
        SectionData(
            section_id="s1",
            title="项目总结",
            content="这个项目超级棒啊！我们搞了个特别牛的系统，效果杠杠的，老板都惊呆了。",
            level=1,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "fail",
        "score": 35,
        "summary": "Document uses informal colloquial language inappropriate for a report.",
        "issues": [
            {
                "severity": "major",
                "category": "style",
                "section_id": "s1",
                "location_excerpt": "超级棒啊",
                "description": "使用了过于口语化的表达，不符合正式文档风格",
                "suggestion": "将口语化表达替换为正式的书面用语",
                "requires_human": False,
            }
        ],
    }

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "fail"
    assert len(result.issues) == 1
    assert result.issues[0].severity == "major"
    assert result.issues[0].category == "style"
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_consistent_formal_style_passes(
    reviewer: StyleReviewer,
    config: ReviewConfig,
) -> None:
    """Formal professional document → status='pass', score=88, no issues."""
    sections = [
        SectionData(
            section_id="s1",
            title="项目概述",
            content=(
                "本项目旨在通过引入自动化审核流程，提升文档质量管理效率。"
                "经过为期三个月的试运行，系统已稳定运行并取得预期效果。"
            ),
            level=1,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "pass",
        "score": 88,
        "summary": "Document maintains consistent formal tone throughout.",
        "issues": [],
    }

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "pass"
    assert result.score == 88
    assert result.issues == []
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_bad_llm_response_graceful_fallback(
    reviewer: StyleReviewer,
    config: ReviewConfig,
) -> None:
    """LLM raises Exception → graceful fallback: status=fail, score=0, category=style."""
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
    mock_llm.complete_json.side_effect = Exception("LLM error")

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "fail"
    assert result.score == 0
    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"
    assert result.issues[0].category == "style"


@pytest.mark.asyncio
async def test_empty_sections_returns_pass(
    reviewer: StyleReviewer,
) -> None:
    """Empty sections list → short-circuit: status=pass, score=100, no LLM call."""
    mock_llm = AsyncMock()

    result = await reviewer.review(
        sections=[], config=ReviewConfig(), llm_client=mock_llm
    )

    assert isinstance(result, ReviewResult)
    assert result.status == "pass"
    assert result.score == 100
    assert result.issues == []
    # LLM should NOT have been called
    mock_llm.complete_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_prompt_contains_style_criteria(
    reviewer: StyleReviewer,
) -> None:
    """Verify _build_prompt includes the Chinese style criteria text."""
    sections = [
        SectionData(
            section_id="s1",
            title="Test",
            content="Test content",
            level=1,
            order_index=0,
        ),
    ]
    messages = reviewer._build_prompt(sections, ReviewConfig())
    assert len(messages) == 2
    assert "检查文风" in messages[0]["content"]
    assert "正式程度是否适当" in messages[0]["content"]
    assert "人称视角是否一致" in messages[0]["content"]
    assert "语气是否统一" in messages[0]["content"]


@pytest.mark.asyncio
async def test_reviewer_registration() -> None:
    """StyleReviewer is registered in the skill registry at module load."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("style")
    skill = registry.get("style")
    assert isinstance(skill, StyleReviewer)
