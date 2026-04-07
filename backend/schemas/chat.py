"""Pydantic schemas for Chat endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    scope: str = Field(default="task", pattern="^(task|section)$")
    section_id: str | None = None


class ChatSessionResponse(BaseModel):
    id: str
    task_id: str
    scope: str
    section_id: str | None
    review_criteria: list[dict[str, str]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    action: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}
