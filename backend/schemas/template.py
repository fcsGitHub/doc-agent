"""Pydantic schemas for Template endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TemplateResponse(BaseModel):
    """Response schema for a document template."""

    id: str
    name: str
    doc_type: str
    description: str | None
    outline_structure: dict[str, Any] | list[Any]
    rules: list[Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    """Response schema for template list."""

    templates: list[TemplateResponse]
    total: int


class ApplyTemplateRequest(BaseModel):
    """Request body for applying a template to a task."""

    template_id: str = Field(..., min_length=1)


class ApplyTemplateResponse(BaseModel):
    """Response schema for apply-template endpoint."""

    message: str
    task_id: str
    template_id: str
    sections_created: int
