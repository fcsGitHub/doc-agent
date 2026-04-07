"""WikiRawSource and WikiArticle ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDMixin


class WikiRawSource(Base, UUIDMixin):
    __tablename__ = "wiki_raw_sources"

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    compiled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WikiArticle(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wiki_articles"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(200), nullable=False, server_default="general")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False, server_default="")
    backlinks: Mapped[list] = mapped_column(JSONB, server_default="[]")
    source_doc_ids: Mapped[list] = mapped_column(JSONB, server_default="[]")
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
