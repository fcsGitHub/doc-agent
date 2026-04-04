"""SourceDocument and ParsedDocument ORM models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.task import Task


class SourceDocument(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "source_documents"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="source_documents")
    parsed_documents: Mapped[list["ParsedDocument"]] = relationship(
        back_populates="source_document"
    )


class ParsedDocument(Base, UUIDMixin):
    __tablename__ = "parsed_documents"

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure: Mapped[list] = mapped_column(JSONB, server_default="[]")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}")
    created_at: Mapped[str | None] = mapped_column(nullable=True)

    source_document: Mapped["SourceDocument"] = relationship(
        back_populates="parsed_documents"
    )
