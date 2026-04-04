"""Tests for CoverageReviewer — requirement coverage checking."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from review.coverage_reviewer import CoverageReviewer
from review.schemas import ReviewConfig, SectionData


@pytest.fixture
def reviewer() -> CoverageReviewer:
    return CoverageReviewer()


@pytest.fixture
def sample_sections() -> list[SectionData]:
    return [
        SectionData(
            section_id="s1",
            title="项目概述",
            content="本项目旨在开发一套文档管理系统，包含文档生成与审核功能。",
            level=1,
            order_index=0,
        ),
        SectionData(
            section_id="s2",
            title="技术架构",
            content="系统采用前后端分离架构，后端使用FastAPI，前端使用Next.js。",
            level=1,
            order_index=1,
        ),
        SectionData(
            section_id="s3",
            title="性能指标",
            content="系统需支持100并发用户，响应时间小于2秒。",
            level=1,
            order_index=2,
        ),
    ]


@pytest.mark.asyncio
async def test_uncovered_requirement_flagged(
    reviewer: CoverageReviewer,
    sample_sections: list[SectionData],
) -> None:
    """When a requirement like '安全性分析' is not covered, LLM flags it as major."""
    llm_client = AsyncMock()
    llm_client.complete_json.return_value = {
        "status": "fail",
        "score": 45,
        "summary": "需求'安全性分析'未被任何章节覆盖",
        "issues": [
            {
                "severity": "major",
                "category": "coverage",
                "section_id": None,
                "location_excerpt": "",
                "description": "需求'安全性分析'在文档中没有对应章节，属于覆盖缺失",
                "suggestion": "增加专门的安全性分析章节，覆盖安全威胁建模和防护措施",
                "requires_human": False,
            }
        ],
    }

    config = ReviewConfig(
        rules=[
            {
                "requirements": [
                    "项目概述",
                    "技术架构",
                    "性能指标",
                    "安全性分析",
                ]
            }
        ]
    )

    result = await reviewer.review(
        sections=sample_sections, config=config, llm_client=llm_client
    )

    assert result.reviewer_name == "coverage"
    assert result.status == "fail"
    assert len(result.issues) == 1
    assert result.issues[0].severity == "major"
    assert result.issues[0].category == "coverage"
    assert "安全性分析" in result.issues[0].description

    # Verify LLM was called with requirements in prompt
    llm_client.complete_json.assert_awaited_once()
    call_args = llm_client.complete_json.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
    user_msg = messages[1]["content"]
    assert "安全性分析" in user_msg
    assert "REQ" in user_msg


@pytest.mark.asyncio
async def test_full_coverage_returns_pass(
    reviewer: CoverageReviewer,
    sample_sections: list[SectionData],
) -> None:
    """When all requirements are covered, LLM returns pass with no issues."""
    llm_client = AsyncMock()
    llm_client.complete_json.return_value = {
        "status": "pass",
        "score": 95,
        "summary": "所有需求均已覆盖，无孤立章节",
        "issues": [],
    }

    config = ReviewConfig(
        rules=[
            {
                "requirements": [
                    "项目概述",
                    "技术架构",
                    "性能指标",
                ]
            }
        ]
    )

    result = await reviewer.review(
        sections=sample_sections, config=config, llm_client=llm_client
    )

    assert result.reviewer_name == "coverage"
    assert result.status == "pass"
    assert result.score == 95
    assert len(result.issues) == 0

    # Verify prompt contained requirements
    call_args = llm_client.complete_json.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
    system_msg = messages[0]["content"]
    assert "覆盖度" in system_msg


@pytest.mark.asyncio
async def test_empty_requirements_handles_gracefully(
    reviewer: CoverageReviewer,
    sample_sections: list[SectionData],
) -> None:
    """When requirements list is empty, runs generic coverage check and returns pass."""
    llm_client = AsyncMock()
    llm_client.complete_json.return_value = {
        "status": "pass",
        "score": 80,
        "summary": "文档覆盖全面，结构合理",
        "issues": [],
    }

    # Empty rules = no requirements
    config = ReviewConfig(rules=[])

    result = await reviewer.review(
        sections=sample_sections, config=config, llm_client=llm_client
    )

    assert result.reviewer_name == "coverage"
    assert result.status == "pass"
    assert len(result.issues) == 0

    # Verify generic prompt was used (no "REQ" markers)
    call_args = llm_client.complete_json.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
    user_msg = messages[1]["content"]
    assert "REQ" not in user_msg
    assert (
        "general coverage" in user_msg.lower() or "comprehensively" in user_msg.lower()
    )


@pytest.mark.asyncio
async def test_prompt_contains_required_criteria(
    reviewer: CoverageReviewer,
) -> None:
    """The review criteria prompt must contain the required Chinese criteria text."""
    assert "检查覆盖度" in reviewer.review_criteria
    assert "评分项/考核标准是否全部覆盖" in reviewer.review_criteria
    assert "孤立章节" in reviewer.review_criteria


@pytest.mark.asyncio
async def test_no_llm_client_returns_fail(
    reviewer: CoverageReviewer,
    sample_sections: list[SectionData],
) -> None:
    """When no LLM client is provided, returns fail gracefully."""
    config = ReviewConfig()
    result = await reviewer.review(
        sections=sample_sections, config=config, llm_client=None
    )

    assert result.status == "fail"
    assert result.score == 0
    assert len(result.issues) == 1
    assert result.issues[0].category == "coverage"
