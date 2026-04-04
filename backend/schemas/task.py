"""Pydantic schemas for Task CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    name: str = Field(..., min_length=1, max_length=500)
    doc_type: str = Field(default="report", max_length=100)
    template_id: str | None = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    name: str | None = None
    status: str | None = None


class TaskResponse(BaseModel):
    """Schema for a single task response."""

    id: str
    name: str
    doc_type: str
    status: str
    progress_pct: int
    progress_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Schema for paginated task list response."""

    tasks: list[TaskResponse]
    total: int
    skip: int
    limit: int


class TaskDetailResponse(TaskResponse):
    """Extended task response with additional detail fields."""

    error_message: str | None = None
    config: dict[str, Any] | None = None


class OutlineApprovalRequest(BaseModel):
    """Schema for outline approval / rejection."""

    approved: bool
    feedback: str | None = None


class OutlineApprovalResponse(BaseModel):
    """Schema for outline approval endpoint response."""

    message: str
    task_id: str
    approved: bool
