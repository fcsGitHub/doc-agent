"""Tests for ConsistencyReviewer — cross-section consistency checks."""

import json

import pytest

from review.consistency_reviewer import ConsistencyReviewer
from review.schemas import ReviewConfig, SectionData


@pytest.fixture
def reviewer() -> ConsistencyReviewer:
    return ConsistencyReviewer()


@pytest.fixture
def sections_inconsistent() -> list[SectionData]:
    """Two sections using inconsistent terminology for the same concept."""
    return [
        SectionData(
            section_id="s1",
            title="Introduction",
            content="本文介绍了机器学习在医疗领域的应用。机器学习技术可以帮助医生提高诊断准确率。",
            level=1,
            order_index=0,
        ),
        SectionData(
            section_id="s2",
            title="Technical Details",
            content="ML技术在本项目中采用了深度神经网络。ML的训练数据来自公开数据集。",
            level=1,
            order_index=1,
        ),
    ]


@pytest.fixture
def sections_consistent() -> list[SectionData]:
    """Consistent sections with no issues."""
    return [
        SectionData(
            section_id="s1",
            title="Overview",
            content="本文讨论人工智能的发展。人工智能近年来取得重大突破。",
            level=1,
            order_index=0,
        ),
        SectionData(
            section_id="s2",
            title="Applications",
            content="人工智能在多个领域得到应用。人工智能技术持续演进。",
            level=1,
            order_index=1,
        ),
    ]


class _AsyncMock:
    """Minimal async mock for llm_client.complete_json."""

    def __init__(self, return_value: str | dict):
        self._return_value = return_value
        self.call_count = 0
        self.last_messages: list | None = None

    async def complete_json(self, messages: list) -> str | dict:
        self.call_count += 1
        self.last_messages = messages
        return self._return_value


class TestTermInconsistency:
    """Test 1: Term inconsistency detected across sections."""

    @pytest.mark.asyncio
    async def test_term_inconsistency_flagged(
        self, reviewer: ConsistencyReviewer, sections_inconsistent: list[SectionData]
    ):
        """LLM flags inconsistent terminology between Section A and Section B."""
        llm_response = json.dumps(
            {
                "status": "warning",
                "score": 65,
                "summary": "Terminology inconsistency detected between sections",
                "issues": [
                    {
                        "severity": "major",
                        "category": "consistency",
                        "section_id": "s1",
                        "location_excerpt": "机器学习",
                        "description": (
                            "Section s1 uses '机器学习' while Section s2 uses 'ML' "
                            "for the same concept. Terminology should be unified."
                        ),
                        "suggestion": "统一使用'机器学习'或在首次出现时定义缩写'ML（机器学习）'",
                        "requires_human": False,
                    }
                ],
            }
        )
        mock_llm = _AsyncMock(return_value=llm_response)
        config = ReviewConfig()

        result = await reviewer.review(
            sections_inconsistent, config, llm_client=mock_llm
        )

        assert result.status == "warning"
        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.severity == "major"
        assert issue.category == "consistency"
        # Issue references both sections
        assert "s1" in issue.description and "s2" in issue.description
        # LLM was called exactly once with all sections
        assert mock_llm.call_count == 1
        assert mock_llm.last_messages is not None
        # Both sections appear in the user prompt
        user_msg = mock_llm.last_messages[1]["content"]
        assert "Introduction" in user_msg
        assert "Technical Details" in user_msg


class TestConsistentDocument:
    """Test 2: Fully consistent document passes."""

    @pytest.mark.asyncio
    async def test_consistent_document_passes(
        self, reviewer: ConsistencyReviewer, sections_consistent: list[SectionData]
    ):
        """LLM returns no issues for a consistent document."""
        llm_response = json.dumps(
            {
                "status": "pass",
                "score": 95,
                "summary": "Document is internally consistent",
                "issues": [],
            }
        )
        mock_llm = _AsyncMock(return_value=llm_response)
        config = ReviewConfig()

        result = await reviewer.review(sections_consistent, config, llm_client=mock_llm)

        assert result.status == "pass"
        assert result.score == 95
        assert len(result.issues) == 0
        assert result.reviewer_name == "consistency"


class TestInvalidJsonFallback:
    """Test 3: Invalid JSON from LLM triggers graceful fallback."""

    @pytest.mark.asyncio
    async def test_invalid_json_graceful_fallback(
        self, reviewer: ConsistencyReviewer, sections_consistent: list[SectionData]
    ):
        """When LLM returns non-JSON, reviewer returns a fail result gracefully."""
        mock_llm = _AsyncMock(return_value="This is not valid JSON at all")
        config = ReviewConfig()

        result = await reviewer.review(sections_consistent, config, llm_client=mock_llm)

        assert result.status == "fail"
        assert result.score == 0
        assert len(result.issues) == 1
        assert result.issues[0].severity == "critical"
        assert result.issues[0].category == "system"
        assert result.reviewer_name == "consistency"
