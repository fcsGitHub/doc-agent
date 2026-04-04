"""Section and SectionVersion ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base, TimestampMixin, UUIDMixin

SectionStatusEnum = Enum(
    "draft",
    "generating",
    "generated",
    "revising",
    "approved",
    name="sectionstatus",
    create_constraint=False,
)


class Section(Base, UUIDMixin, TimestampMixin):
    __tablename__: str = "sections"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_word_count: Mapped[int] = mapped_column(Integer, server_default="500")
    order_index: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        SectionStatusEnum, nullable=False, server_default="draft"
    )

    task: Mapped["Task"] = relationship(  # pyright: ignore[reportUndefinedVariable]
        back_populates="sections"
    )
    versions: Mapped[list["SectionVersion"]] = relationship(back_populates="section")
    children: Mapped[list["Section"]] = relationship(back_populates="parent")
    parent: Mapped["Section | None"] = relationship(
        back_populates="children", remote_side="Section.id"
    )


class SectionVersion(Base, UUIDMixin):
    __tablename__: str = "section_versions"

    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, server_default="0")
    change_source: Mapped[str] = mapped_column(String(100), server_default="generation")
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    section: Mapped["Section"] = relationship(back_populates="versions")
