"""SkillExecution ORM model."""

from __future__ import annotations

import uuid
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDMixin


class SkillExecution(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "skill_executions"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="running"
    )
    input_data: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    output_data: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, server_default="0")
    cost_usd: Mapped[float] = mapped_column(Float, server_default="0.0")
    duration_ms: Mapped[int] = mapped_column(Integer, server_default="0")
