"""Rule, TerminologyEntry, KnowledgeChunk ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector  # pyright: ignore[reportMissingTypeStubs]

from models.base import Base, TimestampMixin, UUIDMixin


class Rule(Base, UUIDMixin, TimestampMixin):
    __tablename__: str = "rules"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="general"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), server_default="major")
    is_active: Mapped[bool] = mapped_column(server_default="true")
    doc_types: Mapped[list[str]] = mapped_column(JSONB, server_default='["report"]')


class TerminologyEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__: str = "terminology_entries"

    term: Mapped[str] = mapped_column(String(200), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), server_default="general")
    preferred_form: Mapped[str | None] = mapped_column(String(200), nullable=True)
    alternatives: Mapped[list[str]] = mapped_column(JSONB, server_default="[]")


class KnowledgeChunk(Base, UUIDMixin):
    __tablename__: str = "knowledge_chunks"

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        "source_document_id", UUID(as_uuid=True), nullable=True
    )
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, server_default="0")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
