"""Unit tests for TaskService — mocked async DB session."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.task_service import TaskService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(**overrides):
    """Return a mock Task ORM object with sensible defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Task",
        "doc_type": "report",
        "status": "created",
        "progress_pct": 0,
        "progress_message": None,
        "error_message": None,
        "config": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    task = MagicMock(**defaults)
    # Make attribute access work (not just .return_value)
    for k, v in defaults.items():
        setattr(task, k, v)
    return task


def _mock_db() -> AsyncMock:
    """Create a fully mocked AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_task_basic(self):
        """create_task persists a Task and returns it."""
        db = _mock_db()
        service = TaskService()

        # When db.refresh is called, populate the mock task attributes
        created_task = _make_task(name="My Doc", doc_type="report")

        async def fake_refresh(obj):
            for attr in (
                "id",
                "name",
                "doc_type",
                "status",
                "progress_pct",
                "progress_message",
                "error_message",
                "config",
                "created_at",
                "updated_at",
            ):
                setattr(obj, attr, getattr(created_task, attr))

        db.refresh.side_effect = fake_refresh

        result = await service.create_task(db, name="My Doc", doc_type="report")

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()
        assert result.name == "My Doc"

    @pytest.mark.asyncio
    async def test_create_task_with_template(self):
        """create_task with template_id also creates TaskConfig."""
        db = _mock_db()
        service = TaskService()
        template_uuid = str(uuid.uuid4())

        created_task = _make_task(name="Templated")

        async def fake_refresh(obj):
            for attr in (
                "id",
                "name",
                "doc_type",
                "status",
                "progress_pct",
                "progress_message",
                "error_message",
                "config",
                "created_at",
                "updated_at",
            ):
                setattr(obj, attr, getattr(created_task, attr))

        db.refresh.side_effect = fake_refresh

        result = await service.create_task(
            db, name="Templated", doc_type="report", template_id=template_uuid
        )

        # db.add called twice: Task + TaskConfig
        assert db.add.call_count == 2
        assert result.name == "Templated"


class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task_found(self):
        """get_task returns the task when found."""
        db = _mock_db()
        service = TaskService()
        task = _make_task(name="Found")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        db.execute.return_value = mock_result

        result = await service.get_task(db, str(task.id))
        assert result is not None
        assert result.name == "Found"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """get_task returns None when task does not exist."""
        db = _mock_db()
        service = TaskService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await service.get_task(db, str(uuid.uuid4()))
        assert result is None


class TestListTasks:
    @pytest.mark.asyncio
    async def test_list_tasks_returns_paginated(self):
        """list_tasks returns tasks and total count."""
        db = _mock_db()
        service = TaskService()

        tasks = [_make_task(name=f"Task {i}") for i in range(3)]

        # First execute call returns count, second returns tasks
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 3

        mock_tasks_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = tasks
        mock_tasks_result.scalars.return_value = mock_scalars

        db.execute.side_effect = [mock_count_result, mock_tasks_result]

        result_tasks, total = await service.list_tasks(db, skip=0, limit=20)
        assert total == 3
        assert len(result_tasks) == 3


class TestUpdateTaskStatus:
    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """update_task_status changes status and commits."""
        db = _mock_db()
        service = TaskService()
        task = _make_task(name="Updatable", status="created")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        db.execute.return_value = mock_result

        result = await service.update_task_status(db, str(task.id), "parsing")
        assert result is not None
        assert result.status == "parsing"
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_status_not_found(self):
        """update_task_status returns None for missing task."""
        db = _mock_db()
        service = TaskService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await service.update_task_status(db, str(uuid.uuid4()), "parsing")
        assert result is None


class TestDeleteTask:
    @pytest.mark.asyncio
    async def test_delete_existing(self):
        """delete_task returns True for existing task."""
        db = _mock_db()
        service = TaskService()
        task = _make_task()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        db.execute.return_value = mock_result

        result = await service.delete_task(db, str(task.id))
        assert result is True
        db.delete.assert_awaited_once_with(task)
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """delete_task returns False for missing task."""
        db = _mock_db()
        service = TaskService()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        result = await service.delete_task(db, str(uuid.uuid4()))
        assert result is False


class TestStartTask:
    @pytest.mark.asyncio
    async def test_start_task_sets_parsing(self):
        """start_task moves task to 'parsing' status."""
        db = _mock_db()
        service = TaskService()
        task = _make_task(status="created")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = task
        db.execute.return_value = mock_result

        result = await service.start_task(db, str(task.id))
        assert result is not None
        assert result.status == "parsing"
        assert result.progress_message == "Pipeline started"
        db.commit.assert_awaited()
