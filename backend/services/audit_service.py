"""Audit service — create and query audit log entries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditEntry


class AuditService:
    """Service for recording and retrieving task-level audit events."""

    # ------------------------------------------------------------------
    # Log an audit event
    # ------------------------------------------------------------------
    async def log(
        self,
        db: AsyncSession,
        task_id: str,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Create an AuditEntry row.

        Args:
            db: Async database session.
            task_id: Task UUID string.
            action: Human-readable action name (stored as event_type).
            entity_type: Optional type of entity involved (e.g. "document").
            entity_id: Optional ID of the entity.
            details: Optional JSON-serialisable dict of extra data.

        Returns:
            The persisted AuditEntry.
        """
        entry = AuditEntry(
            task_id=uuid.UUID(task_id),
            event_type=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            occurred_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    # ------------------------------------------------------------------
    # Get paginated audit log
    # ------------------------------------------------------------------
    async def get_audit_log(
        self,
        db: AsyncSession,
        task_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Return paginated audit entries for a task, newest first."""
        stmt = (
            select(AuditEntry)
            .where(AuditEntry.task_id == uuid.UUID(task_id))
            .order_by(AuditEntry.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Get full task timeline (no limit)
    # ------------------------------------------------------------------
    async def get_task_timeline(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> list[AuditEntry]:
        """Return the full audit history for a task, oldest first."""
        stmt = (
            select(AuditEntry)
            .where(AuditEntry.task_id == uuid.UUID(task_id))
            .order_by(AuditEntry.id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
