"""Tests for BaseReviewer prompt building and response parsing."""
# pyright: reportPrivateUsage=false

import json

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewResult, SectionData


class ConcreteReviewer(BaseReviewer):
    """Concrete reviewer for testing."""

    name: str = "test_reviewer"
    reviewer_name: str = "test_reviewer"
    description: str = "Test reviewer"
    review_criteria: str = "Check document quality"

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: object | None = None,
    ) -> ReviewResult:
        prompt = self._build_prompt(sections, self.review_criteria, config.rules)
        # In tests, simulate LLM returning JSON
        fake_llm_output = json.dumps(
            {
                "status": "pass",
                "score": 88,
                "summary": "Looks good",
                "issues": [],
            }
        )
        _ = prompt
        return self._parse_response(fake_llm_output)


def test_build_prompt_has_sections():
    """_build_prompt() produces messages with section content."""
    reviewer = ConcreteReviewer()
    sections = [
        SectionData(
            section_id="s1",
            title="Introduction",
            content="This is the intro.",
            level=1,
            order_index=0,
        )
    ]
    messages = reviewer._build_prompt(sections, "Check structure")
    assert len(messages) == 2
    assert "Introduction" in messages[1]["content"]
    assert "This is the intro." in messages[1]["content"]


def test_parse_response_valid_json():
    """_parse_response() correctly parses valid LLM JSON output."""
    reviewer = ConcreteReviewer()
    output = json.dumps(
        {
            "status": "fail",
            "score": 40,
            "summary": "Has issues",
            "issues": [
                {
                    "severity": "critical",
                    "category": "structure",
                    "description": "Missing intro",
                    "suggestion": "Add intro",
                    "location_excerpt": "",
                    "requires_human": False,
                }
            ],
        }
    )
    result = reviewer._parse_response(output)
    assert result.status == "fail"
    assert result.score == 40
    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"


def test_build_prompt_with_extra_criteria():
    """_build_prompt() injects extra_criteria into system prompt."""
    reviewer = ConcreteReviewer()
    sections = [
        SectionData(
            section_id="s1",
            title="Intro",
            content="Hello",
            order_index=0,
        )
    ]
    messages = reviewer._build_prompt(sections, "base criteria", extra_criteria=["Follow ISO 9001"])
    system = messages[0]["content"]
    assert "ISO 9001" in system


def test_parse_response_invalid_json():
    """_parse_response() returns fail result gracefully on invalid JSON."""
    reviewer = ConcreteReviewer()
    result = reviewer._parse_response("This is not JSON")
    assert result.status == "fail"
    assert result.score == 0
    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"
