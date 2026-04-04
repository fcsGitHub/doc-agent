"""Tests for ComplianceReviewer — format rules and hard constraint checks."""

from unittest.mock import AsyncMock

import pytest

from review.compliance_reviewer import ComplianceReviewer
from review.schemas import ReviewConfig, SectionData


@pytest.fixture
def reviewer() -> ComplianceReviewer:
    return ComplianceReviewer()


@pytest.fixture
def mock_llm() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def two_unnumbered_table_sections() -> list[SectionData]:
    """Two sections with unnumbered tables."""
    return [
        SectionData(
            section_id="s1",
            title="Data Analysis",
            content="Below is a table showing results:\n| Col1 | Col2 |\n|------|------|\n| A | B |",
            level=1,
            order_index=0,
        ),
        SectionData(
            section_id="s2",
            title="Summary",
            content="Another table without label:\n| X | Y |\n|---|---|\n| 1 | 2 |",
            level=1,
            order_index=1,
        ),
    ]


@pytest.mark.asyncio
async def test_compliance_violation_unnumbered_tables(
    reviewer: ComplianceReviewer,
    mock_llm: AsyncMock,
    two_unnumbered_table_sections: list[SectionData],
) -> None:
    """Test: 2 unnumbered tables → LLM returns 2 major issues with location_excerpt."""
    llm_response = {
        "status": "fail",
        "score": 35,
        "summary": "Found 2 unnumbered tables violating format rules",
        "issues": [
            {
                "severity": "major",
                "category": "compliance",
                "section_id": "s1",
                "location_excerpt": "| Col1 | Col2 |",
                "description": "Table in section 'Data Analysis' is not numbered (expected 'Table 1:')",
                "suggestion": "Add table number label: 'Table 1: Data Analysis Results'",
                "requires_human": False,
            },
            {
                "severity": "major",
                "category": "compliance",
                "section_id": "s2",
                "location_excerpt": "| X | Y |",
                "description": "Table in section 'Summary' is not numbered (expected 'Table 2:')",
                "suggestion": "Add table number label: 'Table 2: Summary Data'",
                "requires_human": False,
            },
        ],
    }
    mock_llm.complete_json = AsyncMock(return_value=llm_response)
    config = ReviewConfig(
        rules=[
            {"name": "table-numbering", "description": "All tables must be numbered"}
        ]
    )

    result = await reviewer.review(
        sections=two_unnumbered_table_sections,
        config=config,
        llm_client=mock_llm,
    )

    assert result.status == "fail"
    assert len(result.issues) == 2
    assert all(i.severity == "major" for i in result.issues)
    assert all(i.category == "compliance" for i in result.issues)
    assert result.issues[0].location_excerpt == "| Col1 | Col2 |"
    assert result.issues[1].location_excerpt == "| X | Y |"
    mock_llm.complete_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_compliance_empty_rules(
    reviewer: ComplianceReviewer,
    mock_llm: AsyncMock,
) -> None:
    """Test: empty rules list → runs without error, returns pass with generic check."""
    llm_response = {
        "status": "pass",
        "score": 90,
        "summary": "No specific rules to check; generic compliance checks passed",
        "issues": [],
    }
    mock_llm.complete_json = AsyncMock(return_value=llm_response)
    sections = [
        SectionData(
            section_id="s1",
            title="Introduction",
            content="Well-formatted introduction with Table 1: Overview.",
            level=1,
            order_index=0,
        ),
    ]
    config = ReviewConfig(rules=[])

    result = await reviewer.review(
        sections=sections,
        config=config,
        llm_client=mock_llm,
    )

    assert result.status == "pass"
    assert result.score == 90
    assert len(result.issues) == 0
    # Verify prompt was built with generic compliance note
    call_args = mock_llm.complete_json.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
    system_msg = messages[0]["content"]
    assert "No specific rules provided" in system_msg


@pytest.mark.asyncio
async def test_compliance_invalid_llm_json(
    reviewer: ComplianceReviewer,
    mock_llm: AsyncMock,
) -> None:
    """Test: LLM returns invalid JSON → graceful fallback to fail ReviewResult."""
    mock_llm.complete_json = AsyncMock(
        side_effect=ValueError("LLM returned invalid JSON: {broken")
    )
    sections = [
        SectionData(
            section_id="s1",
            title="Test",
            content="Content",
            level=1,
            order_index=0,
        ),
    ]
    config = ReviewConfig()

    result = await reviewer.review(
        sections=sections,
        config=config,
        llm_client=mock_llm,
    )

    assert result.status == "fail"
    assert result.score == 0
    assert len(result.issues) == 1
    assert result.issues[0].severity == "critical"
    assert result.issues[0].category == "compliance"
    assert "LLM call failed" in result.issues[0].description


@pytest.mark.asyncio
async def test_compliance_reviewer_name_and_criteria(
    reviewer: ComplianceReviewer,
) -> None:
    """Verify reviewer_name and criteria contain required Chinese text."""
    assert reviewer.reviewer_name == "compliance"
    assert reviewer.name == "compliance"
    assert "检查合规性" in reviewer.review_criteria
    assert "格式规则" in reviewer.review_criteria
    assert "必填字段" in reviewer.review_criteria
    assert "编号格式" in reviewer.review_criteria
    assert "表格图片" in reviewer.review_criteria
    assert "术语" in reviewer.review_criteria
