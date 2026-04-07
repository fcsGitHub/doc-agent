"""ChatSession and ChatMessage ORM models."""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDMixin

ChatScopeEnum = Enum("task", "section", name="chatscopeenum", create_constraint=False)
ChatRoleEnum = Enum("user", "assistant", name="chatroleenum", create_constraint=False)


class ChatSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_sessions"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(ChatScopeEnum, nullable=False, server_default="task")
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    review_criteria: Mapped[list] = mapped_column(JSONB, server_default="[]")


class ChatMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(ChatRoleEnum, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
