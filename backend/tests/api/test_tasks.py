"""API integration tests for /api/v1/tasks endpoints — mocked DB."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from core.database import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(**overrides):
    """Return a mock Task ORM object."""
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
    for k, v in defaults.items():
        setattr(task, k, v)
    return task


async def _override_get_db():
    """Yield a mock async session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    yield db


@pytest.fixture(autouse=True)
def _override_db():
    """Override the DB dependency for every test in this module."""
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# POST /api/v1/tasks
# ---------------------------------------------------------------------------


class TestCreateTaskAPI:
    @pytest.mark.asyncio
    async def test_create_task_201(self):
        """POST /api/v1/tasks returns 201 with valid body."""
        task = _make_task(name="New Report")

        with patch("api.tasks._service") as mock_svc:
            mock_svc.create_task = AsyncMock(return_value=task)
            async with _client() as client:
                resp = await client.post(
                    "/api/v1/tasks",
                    json={"name": "New Report", "doc_type": "report"},
                )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Report"
        assert data["status"] == "created"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_task_422_missing_name(self):
        """POST /api/v1/tasks returns 422 when name is missing."""
        async with _client() as client:
            resp = await client.post("/api/v1/tasks", json={"doc_type": "report"})

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/tasks
# ---------------------------------------------------------------------------


class TestListTasksAPI:
    @pytest.mark.asyncio
    async def test_list_tasks_200(self):
        """GET /api/v1/tasks returns paginated list."""
        tasks = [_make_task(name=f"Task {i}") for i in range(2)]

        with patch("api.tasks._service") as mock_svc:
            mock_svc.list_tasks = AsyncMock(return_value=(tasks, 2))
            async with _client() as client:
                resp = await client.get("/api/v1/tasks?skip=0&limit=20")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["tasks"]) == 2


# ---------------------------------------------------------------------------
# GET /api/v1/tasks/{task_id}
# ---------------------------------------------------------------------------


class TestGetTaskAPI:
    @pytest.mark.asyncio
    async def test_get_task_200(self):
        """GET /api/v1/tasks/{id} returns task detail."""
        task = _make_task(name="Detail Task")

        with patch("api.tasks._service") as mock_svc:
            mock_svc.get_task = AsyncMock(return_value=task)
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{task.id}")

        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Task"

    @pytest.mark.asyncio
    async def test_get_task_404(self):
        """GET /api/v1/tasks/{id} returns 404 for missing task."""
        with patch("api.tasks._service") as mock_svc:
            mock_svc.get_task = AsyncMock(return_value=None)
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/tasks/{task_id}/status
# ---------------------------------------------------------------------------


class TestUpdateStatusAPI:
    @pytest.mark.asyncio
    async def test_update_status_200(self):
        """PUT /api/v1/tasks/{id}/status returns updated task."""
        task = _make_task(status="parsing")

        with patch("api.tasks._service") as mock_svc:
            mock_svc.update_task_status = AsyncMock(return_value=task)
            async with _client() as client:
                resp = await client.put(
                    f"/api/v1/tasks/{task.id}/status",
                    json={"status": "parsing"},
                )

        assert resp.status_code == 200
        assert resp.json()["status"] == "parsing"


# ---------------------------------------------------------------------------
# POST /api/v1/tasks/{task_id}/start
# ---------------------------------------------------------------------------


class TestStartTaskAPI:
    @pytest.mark.asyncio
    async def test_start_task_202(self):
        """POST /api/v1/tasks/{id}/start returns 202."""
        task = _make_task(status="parsing", progress_message="Pipeline started")

        with patch("api.tasks._service") as mock_svc:
            mock_svc.start_task = AsyncMock(return_value=task)
            async with _client() as client:
                resp = await client.post(f"/api/v1/tasks/{task.id}/start")

        assert resp.status_code == 202
        assert resp.json()["status"] == "parsing"


# ---------------------------------------------------------------------------
# DELETE /api/v1/tasks/{task_id}
# ---------------------------------------------------------------------------


class TestDeleteTaskAPI:
    @pytest.mark.asyncio
    async def test_delete_task_204(self):
        """DELETE /api/v1/tasks/{id} returns 204."""
        with patch("api.tasks._service") as mock_svc:
            mock_svc.delete_task = AsyncMock(return_value=True)
            async with _client() as client:
                resp = await client.delete(f"/api/v1/tasks/{uuid.uuid4()}")

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_task_404(self):
        """DELETE /api/v1/tasks/{id} returns 404 for missing task."""
        with patch("api.tasks._service") as mock_svc:
            mock_svc.delete_task = AsyncMock(return_value=False)
            async with _client() as client:
                resp = await client.delete(f"/api/v1/tasks/{uuid.uuid4()}")

        assert resp.status_code == 404
