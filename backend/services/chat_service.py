"""Chat service — session and message management."""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import ChatMessage, ChatSession


class ChatService:
    """CRUD operations for chat sessions and messages."""

    async def create_session(
        self,
        db: AsyncSession,
        task_id: str,
        scope: str = "task",
        section_id: str | None = None,
    ) -> ChatSession:
        session = ChatSession(
            task_id=uuid.UUID(task_id),
            scope=scope,
            section_id=uuid.UUID(section_id) if section_id else None,
            review_criteria=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_session(self, db: AsyncSession, session_id: str) -> ChatSession | None:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == uuid.UUID(session_id))
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, db: AsyncSession, task_id: str) -> Sequence[ChatSession]:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.task_id == uuid.UUID(task_id))
            .order_by(ChatSession.created_at.desc())
        )
        return result.scalars().all()

    async def list_messages(self, db: AsyncSession, session_id: str) -> Sequence[ChatMessage]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == uuid.UUID(session_id))
            .order_by(ChatMessage.created_at.asc())
        )
        return result.scalars().all()

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        action: dict[str, Any] | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=uuid.UUID(session_id),
            role=role,
            content=content,
            action=action,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def append_review_criterion(
        self, db: AsyncSession, session_id: str, label: str, description: str
    ) -> ChatSession:
        """Add a review standard to the session's criteria list."""
        session = await self.get_session(db, session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        criteria = list(session.review_criteria or [])
        criteria.append({"label": label, "description": description})
        session.review_criteria = criteria
        await db.commit()
        await db.refresh(session)
        return session

    async def get_review_criteria_for_task(
        self, db: AsyncSession, task_id: str
    ) -> list[str]:
        """Return all criteria descriptions from the most recent task session."""
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.task_id == uuid.UUID(task_id), ChatSession.scope == "task")
            .order_by(ChatSession.created_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if session is None or not session.review_criteria:
            return []
        return [c["description"] for c in session.review_criteria if "description" in c]
