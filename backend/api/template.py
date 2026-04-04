"""FastAPI router for Template endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.template import (
    ApplyTemplateRequest,
    ApplyTemplateResponse,
    TemplateListResponse,
    TemplateResponse,
)
from services.template_service import TemplateService

router = APIRouter(tags=["templates"])

_service = TemplateService()


def _template_to_response(template: Any) -> dict[str, Any]:
    """Convert ORM DocumentTemplate to dict with UUID serialised as string."""
    return {
        "id": str(template.id),
        "name": template.name,
        "doc_type": template.doc_type,
        "description": template.description,
        "outline_structure": template.outline_structure or {},
        "rules": template.rules or [],
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


# ------------------------------------------------------------------
# GET /templates — list all templates
# ------------------------------------------------------------------
@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    doc_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> TemplateListResponse:
    templates = await _service.get_templates(db, doc_type=doc_type)
    items = [TemplateResponse(**_template_to_response(t)) for t in templates]
    return TemplateListResponse(templates=items, total=len(items))


# ------------------------------------------------------------------
# GET /templates/{template_id} — single template
# ------------------------------------------------------------------
@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    from fastapi import HTTPException

    template = await _service.get_template(db, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse(**_template_to_response(template))


# ------------------------------------------------------------------
# POST /tasks/{task_id}/apply-template — apply template to task
# ------------------------------------------------------------------
@router.post(
    "/tasks/{task_id}/apply-template",
    status_code=201,
    response_model=ApplyTemplateResponse,
)
async def apply_template(
    task_id: str,
    body: ApplyTemplateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplyTemplateResponse:
    sections = await _service.apply_template(db, task_id, body.template_id)
    return ApplyTemplateResponse(
        message="Template applied successfully",
        task_id=task_id,
        template_id=body.template_id,
        sections_created=len(sections),
    )
