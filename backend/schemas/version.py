"""Pydantic schemas for version management endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SectionVersionResponse(BaseModel):
    """Response schema for a section version."""

    id: str
    section_id: str
    version_number: int
    content: str
    word_count: int
    change_source: str
    change_summary: str | None
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


class DiffLine(BaseModel):
    """A single line in a diff hunk."""

    type: str  # "added" | "removed" | "context"
    content: str


class DiffHunk(BaseModel):
    """A hunk within a unified diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]


class DiffResult(BaseModel):
    """Result of comparing two versions."""

    additions: int
    deletions: int
    hunks: list[DiffHunk]


class RollbackRequest(BaseModel):
    """Request body for rolling back a section to a target version."""

    target_version_id: str
