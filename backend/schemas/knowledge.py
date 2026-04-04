"""Pydantic schemas for knowledge base / RAG endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    """Request body for semantic knowledge search."""

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class KnowledgeChunkResponse(BaseModel):
    """Response schema for one retrieved knowledge chunk."""

    id: str
    document_id: str | None
    filename: str | None
    chunk_index: int
    content: str


class KnowledgeDocumentResponse(BaseModel):
    """Response schema for one ingested knowledge document summary."""

    id: str
    filename: str | None
    chunk_count: int


class KnowledgeStatsResponse(BaseModel):
    """Response schema for knowledge base aggregate stats."""

    total_documents: int
    total_chunks: int
    last_updated: datetime | None
