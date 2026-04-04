"""DocumentTemplate ORM model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDMixin


class DocumentTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    outline_structure: Mapped[Any] = mapped_column(JSONB, server_default="[]")
    rules: Mapped[Any] = mapped_column(JSONB, server_default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
