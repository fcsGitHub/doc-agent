"""Approval service — handles outline approval / rejection via LangGraph resume."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditEntry
from orchestrator.checkpoint import build_async_postgres_saver
from orchestrator.graph import build_document_graph
from services.progress_service import ProgressEvent, get_progress_service

# Maximum outline rejections before forcing approval (G8).
MAX_OUTLINE_REJECTIONS = 3


class ApprovalService:
    """Service for handling human-in-the-loop outline approvals."""

    async def approve_outline(
        self,
        task_id: str,
        approved: bool,
        feedback: str | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Approve or reject an outline waiting at the interrupt node.

        If *approved* is True the graph resumes forward.
        If *approved* is False:
          - An AuditEntry is recorded.
          - Rejection count is tracked.  After *MAX_OUTLINE_REJECTIONS*
            the outline is force-approved.
          - Otherwise the graph is resumed with ``Command(resume=False)``
            so the conditional logic in the interrupt node records
            ``outline_approved=False`` and the pipeline can re-plan.
        """
        from langgraph.types import (
            Command,
        )  # local import to avoid top-level dep issues

        saver = build_async_postgres_saver()

        config: dict[str, Any] = {"configurable": {"thread_id": task_id}}

        # Retrieve current checkpoint state to read rejection count.
        rejection_count = 0
        try:
            async with saver as _saver:
                state_snapshot = await _saver.aget(config)
                if state_snapshot and state_snapshot.get("channel_values"):
                    channel = state_snapshot["channel_values"]
                    rejection_count = channel.get("_rejection_count", 0)
        except Exception:
            # If checkpoint read fails, proceed with 0.
            pass

        progress_svc = get_progress_service()

        if approved:
            # Resume graph — outline approved.
            graph = build_document_graph(db=None, llm_client=None)
            compiled = graph.compile(checkpointer=saver)

            async with saver:
                await compiled.ainvoke(Command(resume=True), config=config)

            await progress_svc.publish(
                task_id,
                ProgressEvent(
                    event_type="phase_change",
                    task_id=task_id,
                    phase="planning",
                    progress_pct=45,
                    message="Outline approved — resuming pipeline",
                ),
            )

            return {
                "message": "Outline approved, pipeline resumed.",
                "task_id": task_id,
                "approved": True,
            }
        else:
            # --- Rejection path ---
            rejection_count += 1
            force_approve = rejection_count >= MAX_OUTLINE_REJECTIONS

            # Record audit entry for the rejection.
            try:
                audit = AuditEntry(
                    id=uuid.uuid4(),
                    task_id=uuid.UUID(task_id),
                    event_type="outline_rejected",
                    entity_type="outline",
                    entity_id=task_id,
                    details={
                        "feedback": feedback,
                        "rejection_count": rejection_count,
                        "force_approved": force_approve,
                    },
                )
                db.add(audit)
                await db.flush()
                await db.commit()
            except Exception:
                # Best effort audit logging — don't block the flow.
                pass

            if force_approve:
                # Max rejections reached — force resume.
                graph = build_document_graph(db=None, llm_client=None)
                compiled = graph.compile(checkpointer=saver)

                async with saver:
                    await compiled.ainvoke(Command(resume=True), config=config)

                await progress_svc.publish(
                    task_id,
                    ProgressEvent(
                        event_type="phase_change",
                        task_id=task_id,
                        phase="planning",
                        progress_pct=45,
                        message=f"Max rejections ({MAX_OUTLINE_REJECTIONS}) reached — outline force-approved",
                    ),
                )

                return {
                    "message": f"Max rejections ({MAX_OUTLINE_REJECTIONS}) reached. Outline force-approved, pipeline resumed.",
                    "task_id": task_id,
                    "approved": True,
                }
            else:
                # Resume with False to trigger rejection branch.
                graph = build_document_graph(db=None, llm_client=None)
                compiled = graph.compile(checkpointer=saver)

                async with saver:
                    await compiled.ainvoke(Command(resume=False), config=config)

                await progress_svc.publish(
                    task_id,
                    ProgressEvent(
                        event_type="phase_change",
                        task_id=task_id,
                        phase="planning",
                        progress_pct=35,
                        message=f"Outline rejected ({rejection_count}/{MAX_OUTLINE_REJECTIONS}) — re-planning",
                    ),
                )

                return {
                    "message": f"Outline rejected ({rejection_count}/{MAX_OUTLINE_REJECTIONS}). Re-planning outline.",
                    "task_id": task_id,
                    "approved": False,
                }
