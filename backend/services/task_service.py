"""Task service — async CRUD operations for Task model."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.task import Task, TaskConfig


class TaskService:
    """Service encapsulating Task CRUD and lifecycle operations."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    async def create_task(
        self,
        db: AsyncSession,
        name: str,
        doc_type: str = "report",
        template_id: str | None = None,
    ) -> Task:
        """Create a new task (and associated TaskConfig if template given)."""
        task = Task(name=name, doc_type=doc_type)
        db.add(task)
        await db.flush()  # populate task.id

        if template_id is not None:
            task_config = TaskConfig(
                task_id=task.id,
                template_id=uuid.UUID(template_id),
            )
            db.add(task_config)

        await db.commit()
        await db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    async def get_task(self, db: AsyncSession, task_id: str) -> Task | None:
        """Return a single task by its UUID, or None if not found."""
        stmt = select(Task).where(Task.id == uuid.UUID(task_id))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        status_filter: str | None = None,
    ) -> tuple[Sequence[Task], int]:
        """Return a paginated list of tasks and the total count."""
        base = select(Task)
        count_base = select(func.count(Task.id))

        if status_filter:
            base = base.where(Task.status == status_filter)
            count_base = count_base.where(Task.status == status_filter)

        # total count
        total = (await db.execute(count_base)).scalar_one()

        # paginated results
        stmt = base.order_by(Task.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        tasks = result.scalars().all()

        return tasks, total

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    async def update_task_status(
        self, db: AsyncSession, task_id: str, new_status: str
    ) -> Task | None:
        """Update a task's status. Returns None if task not found."""
        task = await self.get_task(db, task_id)
        if task is None:
            return None
        task.status = new_status
        await db.commit()
        await db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    async def delete_task(self, db: AsyncSession, task_id: str) -> bool:
        """Delete a task by UUID. Returns True if deleted, False if not found."""
        task = await self.get_task(db, task_id)
        if task is None:
            return False
        await db.delete(task)
        await db.commit()
        return True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start_task(
        self,
        db: AsyncSession,
        task_id: str,
    ) -> Task | None:
        """Move task to 'parsing' status and enqueue stub background work.

        Real pipeline execution will be wired in later tasks.
        Returns None if task not found.
        """
        task = await self.get_task(db, task_id)
        if task is None:
            return None
        task.status = "parsing"
        task.progress_pct = 0
        task.progress_message = "Pipeline started"
        await db.commit()
        await db.refresh(task)
        return task
