# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportCallInDefaultInitializer=false
"""FastAPI endpoints for final human approval gate."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.approval import ApprovalRequest, ApprovalState
from services.final_approval_service import FinalApprovalService
from services.task_service import TaskService

router = APIRouter(prefix="/tasks")

_service = FinalApprovalService()
_task_service = TaskService()


@router.get("/{task_id}/approval", response_model=ApprovalState)
async def get_approval_state(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApprovalState:
    """Return final approval state derived from latest review round."""
    task = await _task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return await _service.get_approval_state(task_id=task_id, db=db)


@router.post("/{task_id}/approval")
async def submit_approval(
    task_id: str,
    body: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Submit human final decision: approve or request changes."""
    task = await _task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return await _service.submit_approval(task_id=task_id, request=body, db=db)
