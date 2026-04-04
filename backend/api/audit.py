"""FastAPI router for audit log endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.audit_service import AuditService

router = APIRouter(tags=["audit"])

_service = AuditService()


def _entry_to_dict(entry: Any) -> dict[str, Any]:
    """Convert an AuditEntry ORM object to a JSON-safe dict."""
    return {
        "id": str(entry.id),
        "task_id": str(entry.task_id) if entry.task_id else None,
        "event_type": entry.event_type,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "details": entry.details,
        "occurred_at": entry.occurred_at,
    }


@router.get("/tasks/{task_id}/audit")
async def get_audit_log(
    task_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return paginated audit log for a task."""
    entries = await _service.get_audit_log(db, task_id, limit=limit, offset=offset)
    return {
        "items": [_entry_to_dict(e) for e in entries],
        "limit": limit,
        "offset": offset,
    }
