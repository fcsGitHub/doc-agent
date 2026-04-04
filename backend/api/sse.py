"""SSE endpoint for real-time task progress streaming."""

from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from services.progress_service import get_progress_service

router = APIRouter(prefix="/tasks", tags=["sse"])


@router.get("/{task_id}/progress")
async def task_progress(task_id: str) -> EventSourceResponse:
    """Stream progress events for *task_id* via Server-Sent Events."""

    async def event_generator():
        async for event in get_progress_service().subscribe(task_id):
            yield {
                "event": event.event_type,
                "data": event.model_dump_json(),
            }

    return EventSourceResponse(event_generator())
