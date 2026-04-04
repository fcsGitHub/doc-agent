"""Pydantic schemas for Document, Section, and SectionVersion endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SourceDocumentResponse(BaseModel):
    """Response schema for an uploaded source document."""

    id: str
    task_id: str
    filename: str
    file_type: str
    file_size: int | None
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


class ParsedDocumentResponse(BaseModel):
    """Response schema for a parsed document."""

    id: str
    task_id: str
    raw_text: str | None
    structure: list[object]  # JSON tree from parse skill
    created_at: Any

    model_config = ConfigDict(from_attributes=True)


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


class SectionResponse(BaseModel):
    """Response schema for a section (list view)."""

    id: str
    task_id: str
    title: str
    level: int
    description: str | None
    target_word_count: int
    order_index: int
    status: str
    current_content: str | None  # content from latest SectionVersion
    version_count: int  # number of SectionVersions

    model_config = ConfigDict(from_attributes=True)


class SectionDetailResponse(SectionResponse):
    """Extended section response including all versions."""

    versions: list[SectionVersionResponse]


class SectionUpdateRequest(BaseModel):
    """Request body for updating section content."""

    content: str
    change_summary: str | None = None
