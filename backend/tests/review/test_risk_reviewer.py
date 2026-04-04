"""Tests for RiskReviewer — sensitive content, clean docs, privacy risks."""

import json

import pytest

from review.risk_reviewer import RiskReviewer
from review.schemas import ReviewConfig, SectionData


@pytest.fixture
def reviewer() -> RiskReviewer:
    return RiskReviewer()


@pytest.fixture
def sample_sections() -> list[SectionData]:
    return [
        SectionData(
            section_id="s1",
            title="Company Overview",
            content="本公司属于行业第一，拥有全球最优秀的技术团队。",
            level=1,
            order_index=0,
        ),
    ]


@pytest.fixture
def clean_sections() -> list[SectionData]:
    return [
        SectionData(
            section_id="s1",
            title="Project Summary",
            content="This project aims to improve documentation workflows using automated review.",
            level=1,
            order_index=0,
        ),
    ]


@pytest.fixture
def privacy_sections() -> list[SectionData]:
    return [
        SectionData(
            section_id="s1",
            title="User Data Report",
            content="We collect user phone numbers, email addresses and ID card numbers for marketing.",
            level=1,
            order_index=0,
        ),
    ]


@pytest.fixture
def config() -> ReviewConfig:
    return ReviewConfig()


class MockLLMClient:
    """AsyncMock-like LLM client that returns preset responses."""

    def __init__(self, response: dict):
        self._response = response

    async def complete_json(self, messages: list[dict[str, str]]) -> dict:
        return self._response


@pytest.mark.asyncio
async def test_sensitive_content_flagged(
    reviewer: RiskReviewer,
    sample_sections: list[SectionData],
    config: ReviewConfig,
):
    """Sensitive content like '本公司属于行业第一' is flagged as major, requires_human=True."""
    mock_response = {
        "status": "warning",
        "score": 45,
        "summary": "Document contains exaggerated claims",
        "issues": [
            {
                "severity": "major",
                "category": "risk",
                "section_id": "s1",
                "location_excerpt": "本公司属于行业第一",
                "description": "Exaggerated claim without evidence: '行业第一'",
                "suggestion": "Remove absolute ranking claim or provide supporting data",
                "requires_human": True,
            }
        ],
    }
    llm_client = MockLLMClient(mock_response)

    result = await reviewer.review(sample_sections, config, llm_client=llm_client)

    assert result.status == "warning"
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity == "major"
    assert issue.category == "risk"
    assert issue.requires_human is True
    assert "行业第一" in issue.location_excerpt


@pytest.mark.asyncio
async def test_clean_document_passes(
    reviewer: RiskReviewer,
    clean_sections: list[SectionData],
    config: ReviewConfig,
):
    """Clean document with no risk content returns status='pass' and no issues."""
    mock_response = {
        "status": "pass",
        "score": 95,
        "summary": "No risk issues found",
        "issues": [],
    }
    llm_client = MockLLMClient(mock_response)

    result = await reviewer.review(clean_sections, config, llm_client=llm_client)

    assert result.status == "pass"
    assert result.score == 95
    assert len(result.issues) == 0


@pytest.mark.asyncio
async def test_privacy_risk_requires_human(
    reviewer: RiskReviewer,
    privacy_sections: list[SectionData],
    config: ReviewConfig,
):
    """All risk issues — including privacy — must have requires_human=True."""
    mock_response = {
        "status": "fail",
        "score": 30,
        "summary": "Data privacy concerns detected",
        "issues": [
            {
                "severity": "critical",
                "category": "risk",
                "section_id": "s1",
                "location_excerpt": "user phone numbers, email addresses and ID card numbers",
                "description": "Collecting PII (phone, email, ID) for marketing raises privacy risks",
                "suggestion": "Review data collection practices and ensure GDPR/privacy compliance",
                "requires_human": False,  # LLM might return False — reviewer MUST override to True
            },
            {
                "severity": "major",
                "category": "risk",
                "section_id": "s1",
                "location_excerpt": "for marketing",
                "description": "Using personal data for marketing without stated consent mechanism",
                "suggestion": "Add consent and opt-out mechanisms",
                "requires_human": False,  # Should be overridden
            },
        ],
    }
    llm_client = MockLLMClient(mock_response)

    result = await reviewer.review(privacy_sections, config, llm_client=llm_client)

    assert result.status == "fail"
    assert len(result.issues) == 2
    # ALL risk issues must have requires_human=True, even if LLM returned False
    for issue in result.issues:
        assert issue.requires_human is True, (
            f"Risk issue must have requires_human=True, got False: {issue.description}"
        )
        assert issue.category == "risk"


@pytest.mark.asyncio
async def test_prompt_contains_risk_criteria(reviewer: RiskReviewer):
    """The prompt must contain the required Chinese risk criteria string."""
    sections = [
        SectionData(
            section_id="s1",
            title="Test",
            content="Test content",
            level=1,
            order_index=0,
        ),
    ]
    config = ReviewConfig()
    messages = reviewer._build_prompt(sections, config)

    assert len(messages) == 2
    system_content = messages[0]["content"]
    assert "检查风险：是否包含敏感/机密词汇" in system_content
    assert "是否有夸大表述" in system_content
    assert "是否有未限定的绝对化表述" in system_content
    assert "是否有法律/合规风险" in system_content
    assert "是否有数据隐私问题" in system_content


@pytest.mark.asyncio
async def test_reviewer_name_and_registration(reviewer: RiskReviewer):
    """Reviewer has correct name and is registered in skill registry."""
    assert reviewer.reviewer_name == "risk"
    assert reviewer.name == "risk"

    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("risk")
