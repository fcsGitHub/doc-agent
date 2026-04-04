"""Pydantic schemas for review results and aggregation logic."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    """A single issue identified by a reviewer."""

    severity: Literal["critical", "major", "minor", "info"]
    category: str  # e.g. "structure", "compliance", "technical", "evidence"
    section_id: str | None = (
        None  # Which section the issue is in (None = document-level)
    )
    location_excerpt: str = ""  # Exact text excerpt where issue found
    description: str  # What's wrong
    suggestion: str  # How to fix it
    requires_human: bool = False  # Whether auto-fix is unsafe (human must decide)


class ReviewResult(BaseModel):
    """Output from a single reviewer pass."""

    reviewer_name: str
    status: Literal["pass", "fail", "warning"]
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str
    score: int = Field(ge=0, le=100, default=100)  # 0-100 quality score
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def major_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "major")

    @property
    def minor_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "minor")


class ReviewAggregation(BaseModel):
    """Aggregation of results from all reviewers in a round."""

    results: list[ReviewResult] = Field(default_factory=list)
    overall_status: Literal["pending", "pass", "fail", "warning"] = "pending"
    overall_score: int = Field(ge=0, le=100, default=0)
    pass_threshold: int = Field(default=70, ge=0, le=100)
    total_critical: int = 0
    total_major: int = 0
    total_minor: int = 0
    summary: str = ""

    def compute(self) -> "ReviewAggregation":
        """Compute overall status from individual reviewer results. Returns self."""
        if not self.results:
            self.overall_status = "pass"
            self.overall_score = 100
            return self

        self.total_critical = sum(r.critical_count for r in self.results)
        self.total_major = sum(r.major_count for r in self.results)
        self.total_minor = sum(r.minor_count for r in self.results)

        # Any critical = fail
        if self.total_critical > 0:
            self.overall_status = "fail"
        # Any fail reviewer = fail
        elif any(r.status == "fail" for r in self.results):
            self.overall_status = "fail"
        # Average score below threshold = fail
        elif self.results:
            avg_score = sum(r.score for r in self.results) // len(self.results)
            self.overall_score = avg_score
            if avg_score < self.pass_threshold:
                self.overall_status = "fail"
            elif (
                any(r.status == "warning" for r in self.results) or self.total_major > 0
            ):
                self.overall_status = "warning"
            else:
                self.overall_status = "pass"

        if not self.overall_score:
            self.overall_score = (
                sum(r.score for r in self.results) // len(self.results)
                if self.results
                else 0
            )

        pass_count = sum(1 for r in self.results if r.status == "pass")
        self.summary = (
            f"{pass_count}/{len(self.results)} reviewers passed. "
            f"Critical: {self.total_critical}, Major: {self.total_major}, Minor: {self.total_minor}. "
            f"Overall: {self.overall_status.upper()}"
        )
        return self


class SectionData(BaseModel):
    """Section data passed to reviewers."""

    section_id: str
    title: str
    content: str
    level: int = 1
    order_index: int = 0


class ReviewConfig(BaseModel):
    """Configuration for review execution."""

    rules: list[dict[str, Any]] = Field(
        default_factory=list
    )  # List of rule dicts from DB
    style_guide: str | None = None
    pass_threshold: int = Field(default=70, ge=0, le=100)
    doc_type: str = "report"
