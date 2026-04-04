"""FastAPI router for Task CRUD endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.task import (
    OutlineApprovalRequest,
    OutlineApprovalResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from services.approval_service import ApprovalService
from services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])

_service = TaskService()
_approval_service = ApprovalService()


def _task_to_response(task: Any) -> dict[str, Any]:
    """Convert ORM Task to dict with UUID serialised as string."""
    return {
        "id": str(task.id),
        "name": task.name,
        "doc_type": task.doc_type,
        "status": task.status,
        "progress_pct": task.progress_pct,
        "progress_message": task.progress_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _task_to_detail(task: Any) -> dict[str, Any]:
    """Convert ORM Task to detailed dict."""
    base = _task_to_response(task)
    base["error_message"] = task.error_message
    base["config"] = task.config
    return base


# ------------------------------------------------------------------
# POST /tasks — create
# ------------------------------------------------------------------
@router.post("", status_code=201, response_model=TaskResponse)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await _service.create_task(
        db, name=body.name, doc_type=body.doc_type, template_id=body.template_id
    )
    return TaskResponse(**_task_to_response(task))


# ------------------------------------------------------------------
# GET /tasks — list
# ------------------------------------------------------------------
@router.get("", response_model=TaskListResponse)
async def list_tasks(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    tasks, total = await _service.list_tasks(
        db, skip=skip, limit=limit, status_filter=status
    )
    return TaskListResponse(
        tasks=[TaskResponse(**_task_to_response(t)) for t in tasks],
        total=total,
        skip=skip,
        limit=limit,
    )


# ------------------------------------------------------------------
# GET /tasks/{task_id} — detail
# ------------------------------------------------------------------
@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskDetailResponse:
    task = await _service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetailResponse(**_task_to_detail(task))


# ------------------------------------------------------------------
# PUT /tasks/{task_id}/status — update status
# ------------------------------------------------------------------
@router.put("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: str,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    if body.status is None:
        raise HTTPException(status_code=400, detail="status field is required")
    task = await _service.update_task_status(db, task_id, body.status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**_task_to_response(task))


# ------------------------------------------------------------------
# POST /tasks/{task_id}/start — start pipeline (stub)
# ------------------------------------------------------------------
@router.post("/{task_id}/start", status_code=202, response_model=TaskResponse)
async def start_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await _service.start_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**_task_to_response(task))


# ------------------------------------------------------------------
# DELETE /tasks/{task_id} — delete
# ------------------------------------------------------------------
@router.delete("/{task_id}", status_code=204, response_class=Response)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    deleted = await _service.delete_task(db, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return Response(status_code=204)


# ------------------------------------------------------------------
# POST /tasks/{task_id}/approve-outline — outline approval
# ------------------------------------------------------------------
@router.post(
    "/{task_id}/approve-outline",
    status_code=200,
    response_model=OutlineApprovalResponse,
)
async def approve_outline(
    task_id: str,
    body: OutlineApprovalRequest,
    db: AsyncSession = Depends(get_db),
) -> OutlineApprovalResponse:
    """Approve or reject the document outline at the human-in-the-loop checkpoint."""
    task = await _service.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await _approval_service.approve_outline(
        task_id=task_id,
        approved=body.approved,
        feedback=body.feedback,
        db=db,
    )
    return OutlineApprovalResponse(**result)
