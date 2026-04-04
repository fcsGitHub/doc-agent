"""ReviewResult, ReviewIssue, ReviewRound, Approval ORM models."""
# pyright: reportUnannotatedClassAttribute=false, reportExplicitAny=false

from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin

ReviewSeverityEnum = Enum(
    "critical", "major", "minor", name="reviewseverity", create_constraint=False
)
ReviewStatusEnum = Enum(
    "pass", "fail", "pending", name="reviewstatus", create_constraint=False
)


class ReviewResultModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_results"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    reviewer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        ReviewStatusEnum, nullable=False, server_default="pending"
    )
    score: Mapped[int] = mapped_column(Integer, server_default="0")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_output: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")

    issues: Mapped[list["ReviewIssueModel"]] = relationship(
        back_populates="review_result"
    )


class ReviewIssueModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_issues"

    review_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(ReviewSeverityEnum, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    location_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human: Mapped[bool] = mapped_column(Boolean, server_default="false")
    is_resolved: Mapped[bool] = mapped_column(Boolean, server_default="false")

    review_result: Mapped["ReviewResultModel"] = relationship(back_populates="issues")


class ReviewRound(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "review_rounds"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_status: Mapped[str] = mapped_column(String(50), nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, server_default="0")
    total_issues: Mapped[int] = mapped_column(Integer, server_default="0")
    critical_count: Mapped[int] = mapped_column(Integer, server_default="0")
    major_count: Mapped[int] = mapped_column(Integer, server_default="0")
    minor_count: Mapped[int] = mapped_column(Integer, server_default="0")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    results: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")


class Approval(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approvals"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    approval_type: Mapped[str] = mapped_column(String(50), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, server_default="false")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
