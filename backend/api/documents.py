"""FastAPI router for Document upload, parsed results, and Sections CRUD."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.document import (
    ParsedDocumentResponse,
    SectionDetailResponse,
    SectionResponse,
    SectionUpdateRequest,
    SectionVersionResponse,
    SourceDocumentResponse,
)
from services.document_service import DocumentService

router = APIRouter(prefix="/tasks", tags=["documents"])

_service = DocumentService()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source_doc_to_response(doc: Any) -> dict[str, Any]:
    """Convert ORM SourceDocument to dict with UUID serialised as string."""
    return {
        "id": str(doc.id),
        "task_id": str(doc.task_id),
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "created_at": doc.created_at,
    }


def _parsed_doc_to_response(doc: Any) -> dict[str, Any]:
    """Convert ORM ParsedDocument to dict."""
    return {
        "id": str(doc.id),
        "task_id": str(doc.task_id),
        "raw_text": doc.raw_text,
        "structure": doc.structure,
        "created_at": doc.created_at,
    }


def _version_to_response(v: Any) -> dict[str, Any]:
    """Convert ORM SectionVersion to dict."""
    return {
        "id": str(v.id),
        "section_id": str(v.section_id),
        "version_number": v.version_number,
        "content": v.content,
        "word_count": v.word_count,
        "change_source": v.change_source,
        "change_summary": v.change_summary,
        "created_at": v.created_at,
    }


# ---------------------------------------------------------------------------
# POST /{task_id}/documents/upload — upload file
# ---------------------------------------------------------------------------
@router.post(
    "/{task_id}/documents/upload",
    status_code=201,
    response_model=SourceDocumentResponse,
)
async def upload_document(
    task_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> SourceDocumentResponse:
    doc = await _service.upload_document(db, task_id, file)
    return SourceDocumentResponse(**_source_doc_to_response(doc))


# ---------------------------------------------------------------------------
# GET /{task_id}/documents — list uploaded docs
# ---------------------------------------------------------------------------
@router.get("/{task_id}/documents", response_model=list[SourceDocumentResponse])
async def list_documents(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[SourceDocumentResponse]:
    docs = await _service.get_source_documents(db, task_id)
    return [SourceDocumentResponse(**_source_doc_to_response(d)) for d in docs]


# ---------------------------------------------------------------------------
# GET /{task_id}/sections — list sections
# ---------------------------------------------------------------------------
@router.get("/{task_id}/sections", response_model=list[SectionResponse])
async def list_sections(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[SectionResponse]:
    items = await _service.get_sections(db, task_id)
    return [SectionResponse(**item) for item in items]


# ---------------------------------------------------------------------------
# GET /{task_id}/sections/{section_id} — section detail
# ---------------------------------------------------------------------------
@router.get("/{task_id}/sections/{section_id}", response_model=SectionDetailResponse)
async def get_section(
    task_id: str,
    section_id: str,
    db: AsyncSession = Depends(get_db),
) -> SectionDetailResponse:
    section = await _service.get_section(db, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")

    versions = await _service.get_section_versions(db, section_id)

    # Compute current_content and version_count
    current_content = None
    if versions:
        latest = max(versions, key=lambda v: v.version_number)
        current_content = latest.content

    return SectionDetailResponse(
        id=str(section.id),
        task_id=str(section.task_id),
        title=section.title,
        level=section.level,
        description=section.description,
        target_word_count=section.target_word_count,
        order_index=section.order_index,
        status=section.status,
        current_content=current_content,
        version_count=len(versions),
        versions=[SectionVersionResponse(**_version_to_response(v)) for v in versions],
    )


# ---------------------------------------------------------------------------
# PUT /{task_id}/sections/{section_id} — update section content
# ---------------------------------------------------------------------------
@router.put("/{task_id}/sections/{section_id}", response_model=SectionVersionResponse)
async def update_section(
    task_id: str,
    section_id: str,
    body: SectionUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SectionVersionResponse:
    version = await _service.update_section_content(
        db, section_id, body.content, body.change_summary
    )
    return SectionVersionResponse(**_version_to_response(version))
