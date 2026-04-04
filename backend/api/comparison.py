"""FastAPI router for section comparison against requirements or reference documents."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from skills.base import SkillContext

router = APIRouter(prefix="/tasks", tags=["comparison"])


def _resolve_llm_client() -> object | None:
    """Resolve LLM client lazily to keep import-time side effects minimal in tests."""
    try:
        from core.llm import get_llm_client

        return get_llm_client()
    except ModuleNotFoundError:
        return None


class CompareRequest(BaseModel):
    """Request body for section comparison."""

    reference_content: str = Field(
        ..., min_length=1, description="Reference or requirements content"
    )
    comparison_type: str = Field(
        default="requirements_match",
        description="Type of comparison: 'requirements_match' or 'reference_alignment'",
    )


class CompareResponse(BaseModel):
    """Response body for comparison result."""

    coverage_score: int = Field(default=0, ge=0, le=100)
    missing_items: list[str] = []
    alignment_notes: str = ""
    suggestions: list[str] = []


@router.post(
    "/{task_id}/sections/{section_id}/compare",
    response_model=CompareResponse,
)
async def compare_section(
    task_id: str,
    section_id: str,
    body: CompareRequest,
    db: AsyncSession = Depends(get_db),
) -> CompareResponse:
    """Compare a section's content against reference content or requirements."""
    # Lazy import to avoid circular imports at module load
    from services.document_service import DocumentService

    service = DocumentService()

    # Fetch section to get its current content
    section = await service.get_section(db, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    # Get latest content from section versions
    versions = await service.get_section_versions(db, section_id)
    if not versions:
        raise HTTPException(status_code=400, detail="Section has no content to compare")

    latest = max(versions, key=lambda v: v.version_number)
    section_content: str = latest.content or ""

    # Resolve skill from registry
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    if not registry.is_registered("comparison"):
        # Ensure the comparison skill module is imported (triggers registration)
        import skills.comparison  # noqa: F401

    skill = registry.get("comparison")

    # Build context and execute
    context = SkillContext(
        task_id=task_id,
        section_id=section_id,
        input_data={
            "section_content": section_content,
            "reference_content": body.reference_content,
            "comparison_type": body.comparison_type,
        },
        llm_client=_resolve_llm_client(),
        db_session=db,
    )

    result = await skill.execute(context)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "Comparison failed")

    output: dict[str, Any] = result.output
    return CompareResponse(
        coverage_score=output.get("coverage_score", 0),
        missing_items=output.get("missing_items", []),
        alignment_notes=output.get("alignment_notes", ""),
        suggestions=output.get("suggestions", []),
    )
