"""Tests for ReviewResult/ReviewIssue/ReviewAggregation schemas."""

from typing import Any, Literal, cast

import pytest
from pydantic import ValidationError

from review.schemas import ReviewAggregation, ReviewIssue, ReviewResult


def _make_result(
    status: Literal["pass", "fail", "warning"] = "pass",
    score: int = 90,
    critical: int = 0,
    major: int = 0,
    minor: int = 0,
) -> ReviewResult:
    issues: list[ReviewIssue] = []
    for _ in range(critical):
        issues.append(
            ReviewIssue(
                severity="critical",
                category="test",
                description="c",
                suggestion="fix",
            )
        )
    for _ in range(major):
        issues.append(
            ReviewIssue(
                severity="major",
                category="test",
                description="m",
                suggestion="fix",
            )
        )
    for _ in range(minor):
        issues.append(
            ReviewIssue(
                severity="minor",
                category="test",
                description="mi",
                suggestion="fix",
            )
        )
    return ReviewResult(
        reviewer_name="test_reviewer",
        status=status,
        score=score,
        summary="test",
        issues=issues,
    )


def test_review_issue_valid():
    """Valid ReviewIssue passes validation."""
    issue = ReviewIssue(
        severity="critical",
        category="structure",
        description="Missing section",
        suggestion="Add section",
    )
    assert issue.severity == "critical"
    assert issue.requires_human is False


def test_review_issue_invalid_severity():
    """Invalid severity raises ValidationError."""
    with pytest.raises(ValidationError):
        _ = ReviewIssue(
            severity=cast(Any, "unknown"),
            category="test",
            description="x",
            suggestion="y",
        )


def test_review_result_counts():
    """ReviewResult correctly counts issues by severity."""
    result = _make_result(critical=2, major=3, minor=1)
    assert result.critical_count == 2
    assert result.major_count == 3
    assert result.minor_count == 1


def test_aggregation_any_critical_fails():
    """ReviewAggregation marks fail when any critical issue exists."""
    agg = ReviewAggregation(
        results=[
            _make_result(status="pass", score=95, critical=1),
            _make_result(status="pass", score=90),
        ]
    )
    _ = agg.compute()
    assert agg.overall_status == "fail"
    assert agg.total_critical == 1


def test_aggregation_all_pass():
    """ReviewAggregation marks pass when all reviewers pass and score above threshold."""
    agg = ReviewAggregation(
        results=[
            _make_result(status="pass", score=90),
            _make_result(status="pass", score=85),
        ],
        pass_threshold=70,
    )
    _ = agg.compute()
    assert agg.overall_status == "pass"


def test_aggregation_low_score_fails():
    """ReviewAggregation fails when average score is below threshold."""
    agg = ReviewAggregation(
        results=[
            _make_result(status="pass", score=50),
            _make_result(status="pass", score=60),
        ],
        pass_threshold=70,
    )
    _ = agg.compute()
    assert agg.overall_status == "fail"
