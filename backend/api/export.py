"""FastAPI router for DOCX export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.export_service import ExportService

router = APIRouter(tags=["export"])

_service = ExportService()

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


@router.get("/tasks/{task_id}/export/docx")
async def export_docx(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export a task as a DOCX file download."""
    docx_bytes, task_name = await _service.export_docx(db, task_id)

    return Response(
        content=docx_bytes,
        media_type=DOCX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{task_name}.docx"',
        },
    )
