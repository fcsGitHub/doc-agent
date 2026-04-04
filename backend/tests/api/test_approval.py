"""API integration tests for POST /api/v1/tasks/{task_id}/approve-outline."""

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
        "status": "awaiting_approval",
        "progress_pct": 40,
        "progress_message": "Outline ready for review",
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
# POST /api/v1/tasks/{task_id}/approve-outline — approval
# ---------------------------------------------------------------------------


class TestApproveOutlineEndpointApproval:
    """Tests for the approval (approved=true) path."""

    @pytest.mark.asyncio
    async def test_approve_outline_200(self):
        """POST approve-outline with approved=true returns 200 with correct body."""
        task = _make_task()
        result = {
            "message": "Outline approved, pipeline resumed.",
            "task_id": str(task.id),
            "approved": True,
        }

        with (
            patch("api.tasks._service") as mock_svc,
            patch("api.tasks._approval_service") as mock_approval,
        ):
            mock_svc.get_task = AsyncMock(return_value=task)
            mock_approval.approve_outline = AsyncMock(return_value=result)
            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{task.id}/approve-outline",
                    json={"approved": True},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["approved"] is True
        assert data["task_id"] == str(task.id)
        assert "approved" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_approve_passes_feedback_to_service(self):
        """Feedback from the request body is forwarded to ApprovalService."""
        task = _make_task()
        result = {
            "message": "Outline approved, pipeline resumed.",
            "task_id": str(task.id),
            "approved": True,
        }

        with (
            patch("api.tasks._service") as mock_svc,
            patch("api.tasks._approval_service") as mock_approval,
        ):
            mock_svc.get_task = AsyncMock(return_value=task)
            mock_approval.approve_outline = AsyncMock(return_value=result)
            async with _client() as client:
                await client.post(
                    f"/api/v1/tasks/{task.id}/approve-outline",
                    json={"approved": True, "feedback": "Looks great!"},
                )

            # Verify feedback was passed through.
            call_kwargs = mock_approval.approve_outline.call_args.kwargs
            assert call_kwargs["feedback"] == "Looks great!"
            assert call_kwargs["approved"] is True
            assert call_kwargs["task_id"] == str(task.id)


# ---------------------------------------------------------------------------
# POST /api/v1/tasks/{task_id}/approve-outline — rejection
# ---------------------------------------------------------------------------


class TestApproveOutlineEndpointRejection:
    """Tests for the rejection (approved=false) path."""

    @pytest.mark.asyncio
    async def test_reject_outline_200(self):
        """POST approve-outline with approved=false returns 200 with rejection info."""
        task = _make_task()
        result = {
            "message": "Outline rejected (1/3). Re-planning outline.",
            "task_id": str(task.id),
            "approved": False,
        }

        with (
            patch("api.tasks._service") as mock_svc,
            patch("api.tasks._approval_service") as mock_approval,
        ):
            mock_svc.get_task = AsyncMock(return_value=task)
            mock_approval.approve_outline = AsyncMock(return_value=result)
            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{task.id}/approve-outline",
                    json={"approved": False, "feedback": "Needs more detail"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["approved"] is False
        assert data["task_id"] == str(task.id)
        assert "rejected" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_force_approval_response(self):
        """After max rejections, the service returns approved=true (force-approval)."""
        task = _make_task()
        result = {
            "message": "Max rejections (3) reached. Outline force-approved, pipeline resumed.",
            "task_id": str(task.id),
            "approved": True,
        }

        with (
            patch("api.tasks._service") as mock_svc,
            patch("api.tasks._approval_service") as mock_approval,
        ):
            mock_svc.get_task = AsyncMock(return_value=task)
            mock_approval.approve_outline = AsyncMock(return_value=result)
            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{task.id}/approve-outline",
                    json={"approved": False, "feedback": "Third time no good"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["approved"] is True
        assert "force" in data["message"].lower()


# ---------------------------------------------------------------------------
# POST /api/v1/tasks/{task_id}/approve-outline — error cases
# ---------------------------------------------------------------------------


class TestApproveOutlineEndpointErrors:
    """Tests for error / edge-case responses."""

    @pytest.mark.asyncio
    async def test_404_when_task_not_found(self):
        """POST approve-outline returns 404 if the task does not exist."""
        with patch("api.tasks._service") as mock_svc:
            mock_svc.get_task = AsyncMock(return_value=None)
            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{uuid.uuid4()}/approve-outline",
                    json={"approved": True},
                )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_422_when_body_missing(self):
        """POST approve-outline returns 422 when request body is empty."""
        async with _client() as client:
            resp = await client.post(
                f"/api/v1/tasks/{uuid.uuid4()}/approve-outline",
                content=b"",
                headers={"content-type": "application/json"},
            )

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_422_when_approved_field_missing(self):
        """POST approve-outline returns 422 when 'approved' field is absent."""
        async with _client() as client:
            resp = await client.post(
                f"/api/v1/tasks/{uuid.uuid4()}/approve-outline",
                json={"feedback": "this is fine"},
            )

        assert resp.status_code == 422
