"""API integration tests for SSE /api/v1/tasks/{id}/progress endpoint."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from httpx import ASGITransport, AsyncClient

from main import app
from services.progress_service import ProgressEvent, ProgressService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _make_event(
    task_id: str = "t1",
    event_type: str = "progress",
    phase: str = "generating",
    progress_pct: int = 50,
    message: str = "Half-way there",
    data: dict[str, Any] | None = None,
) -> ProgressEvent:
    return ProgressEvent(
        event_type=event_type,
        task_id=task_id,
        phase=phase,
        progress_pct=progress_pct,
        message=message,
        data=data or {},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSSEEndpoint:
    async def test_sse_endpoint_returns_200_event_stream(self) -> None:
        """GET /api/v1/tasks/{id}/progress returns 200 with text/event-stream."""

        async def _fake_subscribe(task_id: str):  # type: ignore[override]
            """Yield one event then stop."""
            yield _make_event(task_id)

        fake_svc = MagicMock(spec=ProgressService)
        fake_svc.subscribe = _fake_subscribe

        with patch("api.sse.get_progress_service", return_value=fake_svc):
            async with _client() as client:
                resp = await client.get("/api/v1/tasks/test-123/progress")

        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/event-stream" in content_type

    async def test_sse_endpoint_streams_event_data(self) -> None:
        """SSE response body contains the event data."""

        async def _fake_subscribe(task_id: str):  # type: ignore[override]
            yield _make_event(
                task_id, event_type="phase_change", message="Switched to reviewing"
            )

        fake_svc = MagicMock(spec=ProgressService)
        fake_svc.subscribe = _fake_subscribe

        with patch("api.sse.get_progress_service", return_value=fake_svc):
            async with _client() as client:
                resp = await client.get("/api/v1/tasks/abc/progress")

        body = resp.text
        assert "phase_change" in body
        assert "Switched to reviewing" in body
