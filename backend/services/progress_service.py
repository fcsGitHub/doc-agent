"""In-memory event bus for SSE progress streaming.

Fan-out: each subscriber gets its own asyncio.Queue so multiple
browser tabs / clients can watch the same task concurrently.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel


class ProgressEvent(BaseModel):
    """Single progress event pushed to SSE clients."""

    event_type: str  # "phase_change", "progress", "section_complete", "review_complete", "error", "done"
    task_id: str
    phase: str
    progress_pct: int
    message: str
    data: dict[str, Any] = {}


class ProgressService:
    """Publish / subscribe hub backed by per-task asyncio.Queue lists."""

    def __init__(self) -> None:
        # task_id -> list of queues (fan-out to multiple subscribers)
        self._queues: dict[str, list[asyncio.Queue[ProgressEvent | None]]] = {}

    async def publish(self, task_id: str, event: ProgressEvent) -> None:
        """Push *event* to every subscriber watching *task_id*."""
        for q in self._queues.get(task_id, []):
            await q.put(event)

    async def subscribe(self, task_id: str) -> AsyncGenerator[ProgressEvent, None]:
        """Yield events for *task_id*.  Cleans up on generator exit."""
        q: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
        self._queues.setdefault(task_id, []).append(q)
        try:
            while True:
                event = await q.get()
                if event is None:  # sentinel = stream end
                    break
                yield event
        finally:
            self._queues[task_id].remove(q)
            if not self._queues[task_id]:
                del self._queues[task_id]


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------
progress_service = ProgressService()


def get_progress_service() -> ProgressService:
    """Return the module-level singleton (handy for DI / testing)."""
    return progress_service
