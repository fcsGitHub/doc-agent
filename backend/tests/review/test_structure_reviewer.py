"""Tests for StructureReviewer — document structural completeness checks."""

from unittest.mock import AsyncMock

import pytest

from review.schemas import ReviewConfig, ReviewResult, SectionData
from review.structure_reviewer import StructureReviewer


@pytest.fixture
def reviewer() -> StructureReviewer:
    return StructureReviewer()


@pytest.fixture
def well_structured_sections() -> list[SectionData]:
    return [
        SectionData(
            section_id="s1",
            title="引言",
            content="本文档介绍了系统的整体架构设计。" * 10,
            level=1,
            order_index=0,
        ),
        SectionData(
            section_id="s2",
            title="系统概述",
            content="系统采用微服务架构，包含以下核心模块。" * 10,
            level=1,
            order_index=1,
        ),
        SectionData(
            section_id="s3",
            title="详细设计",
            content="本章节详细描述各模块的设计方案。" * 10,
            level=1,
            order_index=2,
        ),
        SectionData(
            section_id="s4",
            title="总结",
            content="本文档总结了系统的整体设计方案。" * 10,
            level=1,
            order_index=3,
        ),
    ]


@pytest.fixture
def config() -> ReviewConfig:
    return ReviewConfig(doc_type="report")


@pytest.mark.asyncio
async def test_missing_required_section(
    reviewer: StructureReviewer,
    config: ReviewConfig,
) -> None:
    """Missing required section → ReviewResult with 1 issue, severity=major, category=structure."""
    sections = [
        SectionData(
            section_id="s1",
            title="详细设计",
            content="Only one section, missing introduction and conclusion.",
            level=2,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "fail",
        "score": 30,
        "summary": "Document is missing required sections: introduction and conclusion.",
        "issues": [
            {
                "severity": "major",
                "category": "structure",
                "section_id": None,
                "location_excerpt": "",
                "description": "缺少必需章节：引言和总结",
                "suggestion": "添加引言和总结章节以确保文档结构完整",
                "requires_human": False,
            }
        ],
    }

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "fail"
    assert len(result.issues) == 1
    assert result.issues[0].severity == "major"
    assert result.issues[0].category == "structure"
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_well_structured_document_passes(
    reviewer: StructureReviewer,
    well_structured_sections: list[SectionData],
    config: ReviewConfig,
) -> None:
    """Well-structured document → ReviewResult.status=pass, issues=[]."""
    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "pass",
        "score": 95,
        "summary": "Document structure is well-organized with all required sections.",
        "issues": [],
    }

    result = await reviewer.review(
        well_structured_sections, config, llm_client=mock_llm
    )

    assert isinstance(result, ReviewResult)
    assert result.status == "pass"
    assert result.issues == []
    assert result.score == 95
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_bad_llm_response_graceful_fallback(
    reviewer: StructureReviewer,
    well_structured_sections: list[SectionData],
    config: ReviewConfig,
) -> None:
    """Bad LLM response (invalid JSON) → graceful fallback ReviewResult with status=fail."""
    mock_llm = AsyncMock()
    mock_llm.complete_json.side_effect = ValueError(
        "LLM returned invalid JSON: not valid json"
    )

    result = await reviewer.review(
        well_structured_sections, config, llm_client=mock_llm
    )

    assert isinstance(result, ReviewResult)
    assert result.status == "fail"
    assert result.score == 0
    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"
    assert result.issues[0].category == "system"


@pytest.mark.asyncio
async def test_prompt_contains_criteria(
    reviewer: StructureReviewer,
) -> None:
    """Verify _build_prompt includes the Chinese criteria text."""
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
    assert "检查文档结构" in messages[0]["content"]
    assert "章节层级是否正确" in messages[0]["content"]
    assert "必需章节是否齐全" in messages[0]["content"]


@pytest.mark.asyncio
async def test_reviewer_registration() -> None:
    """StructureReviewer is registered in the skill registry at module load."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("structure")
    skill = registry.get("structure")
    assert isinstance(skill, StructureReviewer)
