"""Pydantic schemas for LLM configuration endpoints."""
from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class LLMConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    api_key: str = Field(default="")
    api_base: str = Field(default="https://api.openai.com/v1")
    default_model: str = Field(default="gpt-4o-mini")
    review_model: str = Field(default="gpt-4o")
    embed_model: str = Field(default="text-embedding-3-small")

class LLMConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: str | None = None
    api_base: str | None = None
    default_model: str | None = None
    review_model: str | None = None
    embed_model: str | None = None

class LLMConfigResponse(BaseModel):
    id: str
    name: str
    api_key_masked: str  # shows only last 4 chars
    api_base: str
    default_model: str
    review_model: str
    embed_model: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
