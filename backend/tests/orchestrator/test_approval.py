"""Tests for ApprovalService — outline approval / rejection logic.

All LangGraph, checkpoint, and DB interactions are mocked.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.approval_service import ApprovalService, MAX_OUTLINE_REJECTIONS


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


TASK_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Helper: patch all heavy dependencies at once
# ---------------------------------------------------------------------------


def _patch_deps(rejection_count: int = 0):
    """Return a dict of patchers for build_async_postgres_saver, build_document_graph,
    get_progress_service, and Command."""

    # Mock saver (context manager + aget)
    mock_saver = AsyncMock()
    mock_saver.__aenter__ = AsyncMock(return_value=mock_saver)
    mock_saver.__aexit__ = AsyncMock(return_value=False)
    mock_saver.aget = AsyncMock(
        return_value={
            "channel_values": {"_rejection_count": rejection_count},
        }
    )

    # Mock compiled graph
    mock_compiled = AsyncMock()
    mock_compiled.ainvoke = AsyncMock(return_value={})

    # Mock graph builder
    mock_graph = MagicMock()
    mock_graph.compile = MagicMock(return_value=mock_compiled)

    # Mock progress service
    mock_progress = AsyncMock()
    mock_progress.publish = AsyncMock()

    patches = {
        "saver": patch(
            "services.approval_service.build_async_postgres_saver",
            return_value=mock_saver,
        ),
        "graph": patch(
            "services.approval_service.build_document_graph",
            return_value=mock_graph,
        ),
        "progress": patch(
            "services.approval_service.get_progress_service",
            return_value=mock_progress,
        ),
    }

    mocks = {
        "saver": mock_saver,
        "compiled": mock_compiled,
        "graph": mock_graph,
        "progress": mock_progress,
    }

    return patches, mocks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApproveOutlineApproval:
    """Tests for the approval (approved=True) path."""

    @pytest.mark.asyncio
    async def test_approve_resumes_graph(self):
        """Approval resumes the LangGraph pipeline via Command(resume=True)."""
        patches, mocks = _patch_deps()
        svc = ApprovalService()
        db = _mock_db()

        with patches["saver"], patches["graph"], patches["progress"]:
            result = await svc.approve_outline(
                TASK_ID, approved=True, feedback=None, db=db
            )

        assert result["approved"] is True
        assert result["task_id"] == TASK_ID
        assert (
            "approved" in result["message"].lower()
            or "resumed" in result["message"].lower()
        )
        mocks["compiled"].ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_publishes_sse_event(self):
        """Approval publishes an SSE progress event."""
        patches, mocks = _patch_deps()
        svc = ApprovalService()
        db = _mock_db()

        with patches["saver"], patches["graph"], patches["progress"]:
            await svc.approve_outline(TASK_ID, approved=True, feedback=None, db=db)

        mocks["progress"].publish.assert_awaited_once()
        event = mocks["progress"].publish.call_args[0][1]
        assert event.event_type == "phase_change"
        assert event.task_id == TASK_ID


class TestApproveOutlineRejection:
    """Tests for the rejection (approved=False) path."""

    @pytest.mark.asyncio
    async def test_reject_creates_audit_entry(self):
        """Rejection creates an AuditEntry in the DB."""
        patches, mocks = _patch_deps(rejection_count=0)
        svc = ApprovalService()
        db = _mock_db()

        with patches["saver"], patches["graph"], patches["progress"]:
            result = await svc.approve_outline(
                TASK_ID, approved=False, feedback="Needs more detail", db=db
            )

        assert result["approved"] is False
        db.add.assert_called_once()
        audit = db.add.call_args[0][0]
        assert audit.event_type == "outline_rejected"
        assert audit.details["feedback"] == "Needs more detail"
        assert audit.details["rejection_count"] == 1

    @pytest.mark.asyncio
    async def test_reject_resumes_with_false(self):
        """Rejection resumes the graph with Command(resume=False)."""
        patches, mocks = _patch_deps(rejection_count=0)
        svc = ApprovalService()
        db = _mock_db()

        with patches["saver"], patches["graph"], patches["progress"]:
            result = await svc.approve_outline(
                TASK_ID, approved=False, feedback=None, db=db
            )

        assert result["approved"] is False
        mocks["compiled"].ainvoke.assert_awaited_once()
        # The Command arg should be Command(resume=False)
        call_args = mocks["compiled"].ainvoke.call_args[0][0]
        # It should be a Command with resume=False
        assert hasattr(call_args, "resume")
        assert call_args.resume is False

    @pytest.mark.asyncio
    async def test_reject_publishes_sse_event(self):
        """Rejection publishes an SSE progress event."""
        patches, mocks = _patch_deps(rejection_count=0)
        svc = ApprovalService()
        db = _mock_db()

        with patches["saver"], patches["graph"], patches["progress"]:
            await svc.approve_outline(
                TASK_ID, approved=False, feedback="Fix intro", db=db
            )

        mocks["progress"].publish.assert_awaited_once()
        event = mocks["progress"].publish.call_args[0][1]
        assert (
            "rejected" in event.message.lower()
            or "re-planning" in event.message.lower()
        )


class TestForceApprovalAfterMaxRejections:
    """Tests for the force-approval path (rejection_count >= MAX)."""

    @pytest.mark.asyncio
    async def test_force_approve_after_max_rejections(self):
        """After MAX_OUTLINE_REJECTIONS, rejection is force-approved."""
        patches, mocks = _patch_deps(rejection_count=MAX_OUTLINE_REJECTIONS - 1)
        svc = ApprovalService()
        db = _mock_db()

        with patches["saver"], patches["graph"], patches["progress"]:
            result = await svc.approve_outline(
                TASK_ID, approved=False, feedback="Still bad", db=db
            )

        # Force approved
        assert result["approved"] is True
        assert "force" in result["message"].lower()
        # Graph resumed with resume=True
        call_args = mocks["compiled"].ainvoke.call_args[0][0]
        assert hasattr(call_args, "resume")
        assert call_args.resume is True

    @pytest.mark.asyncio
    async def test_force_approve_records_audit_with_force_flag(self):
        """Force-approval audit entry has force_approved=True."""
        patches, mocks = _patch_deps(rejection_count=MAX_OUTLINE_REJECTIONS - 1)
        svc = ApprovalService()
        db = _mock_db()

        with patches["saver"], patches["graph"], patches["progress"]:
            await svc.approve_outline(TASK_ID, approved=False, feedback=None, db=db)

        db.add.assert_called_once()
        audit = db.add.call_args[0][0]
        assert audit.details["force_approved"] is True
        assert audit.details["rejection_count"] == MAX_OUTLINE_REJECTIONS


class TestCheckpointReadFailure:
    """Edge case: checkpoint read fails gracefully."""

    @pytest.mark.asyncio
    async def test_checkpoint_read_failure_defaults_to_zero_rejections(self):
        """If checkpoint state can't be read, rejection_count defaults to 0."""
        # Saver that raises on aget
        mock_saver = AsyncMock()
        mock_saver.__aenter__ = AsyncMock(return_value=mock_saver)
        mock_saver.__aexit__ = AsyncMock(return_value=False)
        mock_saver.aget = AsyncMock(side_effect=Exception("DB down"))

        mock_compiled = AsyncMock()
        mock_compiled.ainvoke = AsyncMock(return_value={})
        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)
        mock_progress = AsyncMock()
        mock_progress.publish = AsyncMock()

        svc = ApprovalService()
        db = _mock_db()

        with (
            patch(
                "services.approval_service.build_async_postgres_saver",
                return_value=mock_saver,
            ),
            patch(
                "services.approval_service.build_document_graph",
                return_value=mock_graph,
            ),
            patch(
                "services.approval_service.get_progress_service",
                return_value=mock_progress,
            ),
        ):
            result = await svc.approve_outline(
                TASK_ID, approved=False, feedback="x", db=db
            )

        # Should treat as rejection_count=1 (0+1) — not force approve
        assert result["approved"] is False
        assert "1/" in result["message"]
