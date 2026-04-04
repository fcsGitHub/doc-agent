"""Unit tests for ProgressService — publish / subscribe event bus."""

from __future__ import annotations

import asyncio

import pytest

from services.progress_service import ProgressEvent, ProgressService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(task_id: str = "t1", **overrides) -> ProgressEvent:
    defaults = {
        "event_type": "progress",
        "task_id": task_id,
        "phase": "generating",
        "progress_pct": 50,
        "message": "Half-way there",
        "data": {},
    }
    defaults.update(overrides)
    return ProgressEvent(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPublishSubscribe:
    async def test_single_subscriber_receives_event(self):
        """publish -> subscribe delivers one event correctly."""
        svc = ProgressService()
        received: list[ProgressEvent] = []

        async def consumer():
            async for evt in svc.subscribe("t1"):
                received.append(evt)

        task = asyncio.create_task(consumer())

        # Give consumer time to register
        await asyncio.sleep(0.05)

        event = _make_event("t1", progress_pct=75)
        await svc.publish("t1", event)

        # Send sentinel to end the stream
        for q in svc._queues.get("t1", []):
            await q.put(None)

        await asyncio.wait_for(task, timeout=1.0)

        assert len(received) == 1
        assert received[0].progress_pct == 75
        assert received[0].event_type == "progress"

    async def test_fan_out_two_subscribers(self):
        """Two subscribers both receive the same published event."""
        svc = ProgressService()
        received_a: list[ProgressEvent] = []
        received_b: list[ProgressEvent] = []

        async def consumer_a():
            async for evt in svc.subscribe("t1"):
                received_a.append(evt)

        async def consumer_b():
            async for evt in svc.subscribe("t1"):
                received_b.append(evt)

        task_a = asyncio.create_task(consumer_a())
        task_b = asyncio.create_task(consumer_b())

        await asyncio.sleep(0.05)

        event = _make_event("t1", message="fan-out test")
        await svc.publish("t1", event)

        # Send sentinels
        for q in list(svc._queues.get("t1", [])):
            await q.put(None)

        await asyncio.wait_for(task_a, timeout=1.0)
        await asyncio.wait_for(task_b, timeout=1.0)

        assert len(received_a) == 1
        assert len(received_b) == 1
        assert received_a[0].message == "fan-out test"
        assert received_b[0].message == "fan-out test"

    async def test_cleanup_on_unsubscribe(self):
        """After a subscriber exits, its queue is removed."""
        svc = ProgressService()

        async def consumer():
            async for _ in svc.subscribe("t1"):
                pass  # will exit when sentinel received

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        # Verify subscriber is registered
        assert "t1" in svc._queues
        assert len(svc._queues["t1"]) == 1

        # Send sentinel to end stream
        for q in svc._queues["t1"]:
            await q.put(None)

        await asyncio.wait_for(task, timeout=1.0)

        # Queue dict should be cleaned up entirely
        assert "t1" not in svc._queues

    async def test_publish_to_nonexistent_task_is_noop(self):
        """Publishing to a task with no subscribers does not raise."""
        svc = ProgressService()
        event = _make_event("no-one-listening")
        # Should not raise
        await svc.publish("no-one-listening", event)
