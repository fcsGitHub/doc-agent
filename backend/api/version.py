"""FastAPI router for section version management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.version import (
    DiffResult,
    RollbackRequest,
    SectionVersionResponse,
)
from services.version_service import VersionService

router = APIRouter(prefix="/sections", tags=["versions"])

_service = VersionService()


@router.get(
    "/{section_id}/versions",
    response_model=list[SectionVersionResponse],
)
async def list_versions(
    section_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[SectionVersionResponse]:
    """List all versions for a section, ordered by version_number ASC."""
    versions = await _service.get_versions(db, section_id)
    return [
        SectionVersionResponse(
            id=str(v.id),
            section_id=str(v.section_id),
            version_number=v.version_number,
            content=v.content,
            word_count=v.word_count,
            change_source=v.change_source,
            change_summary=v.change_summary,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.get(
    "/{section_id}/versions/{version_id}/diff",
    response_model=DiffResult,
)
async def get_version_diff(
    section_id: str,
    version_id: str,
    compare_to: str,
    db: AsyncSession = Depends(get_db),
) -> DiffResult:
    """Compute diff between two versions."""
    # Validate that version_id belongs to this section
    version = await _service.get_version(db, version_id)
    if version is None or str(version.section_id) != section_id:
        raise HTTPException(status_code=404, detail="Version not found")

    diff = await _service.get_diff(db, version_id, compare_to)
    return DiffResult(**diff)


@router.post(
    "/{section_id}/rollback",
    response_model=SectionVersionResponse,
)
async def rollback_section(
    section_id: str,
    body: RollbackRequest,
    db: AsyncSession = Depends(get_db),
) -> SectionVersionResponse:
    """Rollback a section to a target version (creates a new version)."""
    version = await _service.rollback_section(db, section_id, body.target_version_id)
    return SectionVersionResponse(
        id=str(version.id),
        section_id=str(version.section_id),
        version_number=version.version_number,
        content=version.content,
        word_count=version.word_count,
        change_source=version.change_source,
        change_summary=version.change_summary,
        created_at=version.created_at,
    )
