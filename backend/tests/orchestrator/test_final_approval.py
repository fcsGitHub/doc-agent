"""API tests for final approval gate endpoints."""
# pyright: reportUnusedFunction=false, reportAny=false, reportExplicitAny=false

from __future__ import annotations

import uuid
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from main import app
from models.approval import ApprovalState


async def _override_get_db():
    db = AsyncMock()
    yield db


@pytest.fixture(autouse=True)
def _override_db():
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestFinalApprovalAPI:
    @pytest.mark.asyncio
    async def test_get_approval_state_no_reviews(self):
        task_id = str(uuid.uuid4())
        approval_state = ApprovalState(task_id=task_id, status="no_reviews")

        with (
            patch("api.final_approval._task_service") as mock_task_service,
            patch("api.final_approval._service") as mock_service,
        ):
            mock_task_service.get_task = AsyncMock(return_value=object())
            mock_service.get_approval_state = AsyncMock(return_value=approval_state)

            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{task_id}/approval")

        assert resp.status_code == 200
        payload = cast(dict[str, Any], resp.json())
        assert payload["task_id"] == task_id
        assert payload["status"] == "no_reviews"

    @pytest.mark.asyncio
    async def test_get_approval_state_with_reviews(self):
        task_id = str(uuid.uuid4())
        approval_state = ApprovalState(
            task_id=task_id,
            status="awaiting_approval",
            review_summary={
                "overall_status": "needs_revision",
                "overall_score": 0.72,
                "reviewer_count": 8,
            },
            pending_human_issues=[
                {
                    "severity": "major",
                    "category": "compliance",
                    "description": "Ambiguous legal phrasing",
                    "requires_human": True,
                }
            ],
        )

        with (
            patch("api.final_approval._task_service") as mock_task_service,
            patch("api.final_approval._service") as mock_service,
        ):
            mock_task_service.get_task = AsyncMock(return_value=object())
            mock_service.get_approval_state = AsyncMock(return_value=approval_state)

            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{task_id}/approval")

        assert resp.status_code == 200
        payload = cast(dict[str, Any], resp.json())
        assert payload["status"] == "awaiting_approval"
        assert payload["review_summary"]["overall_status"] == "needs_revision"
        assert payload["review_summary"]["reviewer_count"] == 8
        assert len(cast(list[dict[str, Any]], payload["pending_human_issues"])) == 1

    @pytest.mark.asyncio
    async def test_submit_approval_approve(self):
        task_id = str(uuid.uuid4())

        with (
            patch("api.final_approval._task_service") as mock_task_service,
            patch("api.final_approval._service") as mock_service,
        ):
            mock_task_service.get_task = AsyncMock(return_value=object())
            mock_service.submit_approval = AsyncMock(
                return_value={
                    "message": "Document approved",
                    "task_id": task_id,
                    "action": "approve",
                }
            )

            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{task_id}/approval",
                    json={"action": "approve", "notes": "Looks good"},
                )

        assert resp.status_code == 200
        payload = cast(dict[str, Any], resp.json())
        assert payload["action"] == "approve"
        assert "approved" in payload["message"].lower()

    @pytest.mark.asyncio
    async def test_submit_approval_request_changes(self):
        task_id = str(uuid.uuid4())
        notes = "Please improve section 2 references"

        with (
            patch("api.final_approval._task_service") as mock_task_service,
            patch("api.final_approval._service") as mock_service,
        ):
            mock_task_service.get_task = AsyncMock(return_value=object())
            mock_service.submit_approval = AsyncMock(
                return_value={
                    "message": "Changes requested, revision queued",
                    "task_id": task_id,
                    "action": "request_changes",
                    "notes": notes,
                }
            )

            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{task_id}/approval",
                    json={"action": "request_changes", "notes": notes},
                )

        assert resp.status_code == 200
        payload = cast(dict[str, Any], resp.json())
        assert payload["action"] == "request_changes"
        assert payload["notes"] == notes

    @pytest.mark.asyncio
    async def test_submit_approval_no_reviews_blocked(self):
        task_id = str(uuid.uuid4())

        with (
            patch("api.final_approval._task_service") as mock_task_service,
            patch("api.final_approval._service") as mock_service,
        ):
            mock_task_service.get_task = AsyncMock(return_value=object())
            mock_service.submit_approval = AsyncMock(
                side_effect=HTTPException(
                    status_code=400,
                    detail="Reviews must be completed before approval",
                )
            )

            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{task_id}/approval",
                    json={"action": "approve"},
                )

        assert resp.status_code == 400
        assert "Reviews must be completed" in resp.json()["detail"]
