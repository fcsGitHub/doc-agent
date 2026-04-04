# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false
"""Pydantic models for final human approval gate."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """Human decision submitted after automated review completion."""

    action: Literal["approve", "request_changes"]
    notes: str | None = None


class ApprovalState(BaseModel):
    """Current final approval state for a task."""

    task_id: str
    status: Literal[
        "awaiting_approval",
        "approved",
        "changes_requested",
        "no_reviews",
    ]
    review_summary: dict[str, Any] | None = None
    pending_human_issues: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None
    notes: str | None = None
