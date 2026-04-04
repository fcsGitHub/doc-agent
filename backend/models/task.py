"""Task and TaskConfig ORM models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.document import SourceDocument, ParsedDocument
    from models.section import Section

TaskStatusEnum = Enum(
    "created",
    "parsing",
    "extracting",
    "planning",
    "awaiting_approval",
    "generating",
    "reviewing",
    "revising",
    "approved",
    "exporting",
    "completed",
    "failed",
    name="taskstatus",
    create_constraint=False,
)


class Task(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tasks"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="report"
    )
    status: Mapped[str] = mapped_column(
        TaskStatusEnum, nullable=False, server_default="created"
    )
    config: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, server_default="0")
    progress_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    task_config: Mapped["TaskConfig | None"] = relationship(
        back_populates="task", uselist=False
    )
    source_documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="task"
    )
    sections: Mapped[list["Section"]] = relationship(back_populates="task")


class TaskConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "task_configs"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    outline_approved: Mapped[bool] = mapped_column(Boolean, server_default="false")
    final_approved: Mapped[bool] = mapped_column(Boolean, server_default="false")
    revision_round: Mapped[int] = mapped_column(Integer, server_default="0")
    max_revision_rounds: Mapped[int] = mapped_column(Integer, server_default="3")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}")

    task: Mapped["Task"] = relationship(back_populates="task_config")
