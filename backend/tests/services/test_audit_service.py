"""Unit tests for AuditService — log, get_audit_log, get_task_timeline."""
# pyright: reportAny=false, reportExplicitAny=false, reportUnusedCallResult=false

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.audit_service import AuditService


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_audit_entry(
    task_id: uuid.UUID,
    event_type: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
    occurred_at: str | None = None,
    entry_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock AuditEntry object."""
    e = MagicMock()
    e.id = entry_id or uuid.uuid4()
    e.task_id = task_id
    e.event_type = event_type
    e.entity_type = entity_type
    e.entity_id = entity_id
    e.details = details or {}
    e.occurred_at = occurred_at
    return e


class TestAuditService:
    @pytest.mark.asyncio
    async def test_log_creates_entry(self) -> None:
        """log() should create an AuditEntry with correct fields and commit."""
        service = AuditService()
        db = _mock_db()
        task_id = str(uuid.uuid4())

        added_objects: list[MagicMock] = []
        db.add = lambda obj: added_objects.append(obj)

        await service.log(
            db,
            task_id=task_id,
            action="document_uploaded",
            entity_type="document",
            entity_id="doc-123",
            details={"filename": "report.docx"},
        )

        assert db.commit.await_count == 1
        assert db.refresh.await_count == 1
        assert len(added_objects) == 1

        created = added_objects[0]
        assert str(created.task_id) == task_id
        assert created.event_type == "document_uploaded"
        assert created.entity_type == "document"
        assert created.entity_id == "doc-123"
        assert created.details == {"filename": "report.docx"}
        assert created.occurred_at is not None

    @pytest.mark.asyncio
    async def test_log_defaults_details_to_empty_dict(self) -> None:
        """log() without details should store empty dict."""
        service = AuditService()
        db = _mock_db()
        task_id = str(uuid.uuid4())

        added_objects: list[MagicMock] = []
        db.add = lambda obj: added_objects.append(obj)

        await service.log(
            db,
            task_id=task_id,
            action="review_completed",
        )

        assert len(added_objects) == 1
        assert added_objects[0].details == {}
        assert added_objects[0].entity_type is None
        assert added_objects[0].entity_id is None

    @pytest.mark.asyncio
    async def test_get_audit_log_paginated(self) -> None:
        """get_audit_log() should return paginated entries."""
        service = AuditService()
        db = _mock_db()
        task_id = uuid.uuid4()

        e1 = _make_audit_entry(task_id, "document_uploaded")
        e2 = _make_audit_entry(task_id, "review_completed")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [e2, e1]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        entries = await service.get_audit_log(db, str(task_id), limit=10, offset=0)

        assert len(entries) == 2
        assert entries[0].event_type == "review_completed"
        assert entries[1].event_type == "document_uploaded"
        assert db.execute.await_count == 1

    @pytest.mark.asyncio
    async def test_get_task_timeline_returns_all(self) -> None:
        """get_task_timeline() should return all entries oldest first."""
        service = AuditService()
        db = _mock_db()
        task_id = uuid.uuid4()

        e1 = _make_audit_entry(
            task_id, "document_uploaded", occurred_at="2026-01-01T00:00:00Z"
        )
        e2 = _make_audit_entry(
            task_id, "review_completed", occurred_at="2026-01-02T00:00:00Z"
        )
        e3 = _make_audit_entry(
            task_id, "document_exported", occurred_at="2026-01-03T00:00:00Z"
        )

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [e1, e2, e3]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        entries = await service.get_task_timeline(db, str(task_id))

        assert len(entries) == 3
        assert entries[0].event_type == "document_uploaded"
        assert entries[1].event_type == "review_completed"
        assert entries[2].event_type == "document_exported"

    @pytest.mark.asyncio
    async def test_get_audit_log_empty(self) -> None:
        """get_audit_log() should return empty list when no entries."""
        service = AuditService()
        db = _mock_db()
        task_id = uuid.uuid4()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        entries = await service.get_audit_log(db, str(task_id))

        assert entries == []
