"""Pydantic schemas for Wiki endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WikiSourceResponse(BaseModel):
    id: str
    filename: str
    compiled: bool
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class WikiArticleResponse(BaseModel):
    id: str
    title: str
    category: str
    content: str
    summary: str
    backlinks: list[str]
    source_doc_ids: list[str]
    health_score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WikiArticleUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    content: str | None = None
    summary: str | None = None


class WikiQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    category: str | None = None


class WikiQueryResponse(BaseModel):
    answer: str
    source_article_ids: list[str]


class WikiLintReport(BaseModel):
    total_articles: int
    issues: list[dict[str, Any]]
    updated_scores: dict[str, float]
