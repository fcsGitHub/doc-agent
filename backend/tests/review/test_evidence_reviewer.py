"""Tests for EvidenceReviewer — evidence quality checks for document claims."""

from unittest.mock import AsyncMock

import pytest

from review.evidence_reviewer import EvidenceReviewer
from review.schemas import ReviewConfig, ReviewResult, SectionData


@pytest.fixture
def reviewer() -> EvidenceReviewer:
    return EvidenceReviewer()


@pytest.fixture
def config() -> ReviewConfig:
    return ReviewConfig(doc_type="report")


@pytest.mark.asyncio
async def test_unsupported_claim_detected(
    reviewer: EvidenceReviewer,
    config: ReviewConfig,
) -> None:
    """Section with unsupported '300%' claim → flagged with location_excerpt containing '300%'."""
    sections = [
        SectionData(
            section_id="s1",
            title="方案效果",
            content="本方案可提升效率300%，大幅降低运营成本。",
            level=1,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "fail",
        "score": 25,
        "summary": "Document contains unsupported claims lacking data or evidence.",
        "issues": [
            {
                "severity": "major",
                "category": "evidence",
                "section_id": "s1",
                "location_excerpt": "本方案可提升效率300%",
                "description": "声称效率提升300%但未提供任何数据来源或实验依据",
                "suggestion": "补充效率提升的具体测试数据、对比实验结果或权威来源引用",
                "requires_human": False,
            }
        ],
    }

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "fail"
    assert len(result.issues) == 1
    assert result.issues[0].severity == "major"
    assert result.issues[0].category == "evidence"
    assert "300%" in result.issues[0].location_excerpt
    assert result.issues[0].suggestion != ""
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_well_evidenced_document_passes(
    reviewer: EvidenceReviewer,
    config: ReviewConfig,
) -> None:
    """Well-evidenced document → status='pass', no issues."""
    sections = [
        SectionData(
            section_id="s1",
            title="实验结果",
            content=(
                "根据2024年Q1的A/B测试数据（样本量N=5000），"
                "实验组响应时间从320ms降低至210ms，降幅34.4%（p<0.01）。"
                "数据来源：内部监控平台Grafana，采集周期2024-01-01至2024-03-31。"
            ),
            level=1,
            order_index=0,
        ),
    ]

    mock_llm = AsyncMock()
    mock_llm.complete_json.return_value = {
        "status": "pass",
        "score": 92,
        "summary": "All claims are well-supported with specific data and clear citations.",
        "issues": [],
    }

    result = await reviewer.review(sections, config, llm_client=mock_llm)

    assert isinstance(result, ReviewResult)
    assert result.status == "pass"
    assert result.issues == []
    assert result.score == 92
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_json_from_llm_graceful_fallback(
    reviewer: EvidenceReviewer,
    config: ReviewConfig,
) -> None:
    """LLM returns invalid JSON → graceful fallback to fail ReviewResult."""
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
    assert result.issues[0].category == "system"


@pytest.mark.asyncio
async def test_prompt_contains_evidence_criteria(
    reviewer: EvidenceReviewer,
) -> None:
    """Verify _build_prompt includes the Chinese evidence criteria text."""
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
    assert "检查证据支撑" in messages[0]["content"]
    assert "结论是否有数据/证据支持" in messages[0]["content"]
    assert "引用是否明确" in messages[0]["content"]
    assert "是否存在空泛表述" in messages[0]["content"]
    assert "论据与论点是否对应" in messages[0]["content"]


@pytest.mark.asyncio
async def test_reviewer_registration() -> None:
    """EvidenceReviewer is registered in the skill registry at module load."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("evidence")
    skill = registry.get("evidence")
    assert isinstance(skill, EvidenceReviewer)
