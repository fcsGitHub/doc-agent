"""Document service — file upload, parsed results, sections CRUD."""

from __future__ import annotations

import os
import uuid
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import ParsedDocument, SourceDocument
from models.section import Section, SectionVersion
from services.audit_service import AuditService

# Constraints
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".docx", ".pdf", ".md"}


class DocumentService:
    """Service encapsulating document upload and section operations."""

    _audit = AuditService()

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    async def upload_document(
        self, db: AsyncSession, task_id: str, file: UploadFile
    ) -> SourceDocument:
        """Validate file, save to uploads/{task_id}/, create SourceDocument."""
        filename = file.filename or "unnamed"

        # Validate extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}，仅支持 .docx, .pdf, .md",
            )

        # Read content and validate size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="文件过大，最大支持50MB")

        # Save to disk
        upload_dir = os.path.join("uploads", task_id)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, "wb") as f:
            f.write(content)

        # Create ORM record
        doc = SourceDocument(
            task_id=uuid.UUID(task_id),
            filename=filename,
            file_type=ext.lstrip("."),
            file_path=file_path,
            file_size=len(content),
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # Best-effort audit logging
        try:
            await self._audit.log(
                db,
                task_id=task_id,
                action="document_uploaded",
                entity_type="document",
                entity_id=str(doc.id),
                details={"filename": filename, "file_size": len(content)},
            )
        except Exception:
            pass

        return doc

    # ------------------------------------------------------------------
    # List source documents
    # ------------------------------------------------------------------
    async def get_source_documents(
        self, db: AsyncSession, task_id: str
    ) -> list[SourceDocument]:
        """List uploaded source docs for a task."""
        stmt = select(SourceDocument).where(
            SourceDocument.task_id == uuid.UUID(task_id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Get parsed document
    # ------------------------------------------------------------------
    async def get_parsed_document(
        self, db: AsyncSession, task_id: str
    ) -> ParsedDocument | None:
        """Get the most recent parsed document for a task."""
        stmt = (
            select(ParsedDocument)
            .where(ParsedDocument.task_id == uuid.UUID(task_id))
            .order_by(ParsedDocument.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------
    async def get_sections(
        self, db: AsyncSession, task_id: str
    ) -> list[dict[str, Any]]:
        """Get all sections for a task with current_content and version_count."""
        stmt = (
            select(Section)
            .where(Section.task_id == uuid.UUID(task_id))
            .order_by(Section.order_index)
        )
        result = await db.execute(stmt)
        sections = list(result.scalars().all())

        if not sections:
            return []

        # Fetch all versions for these sections
        sec_ids = [s.id for s in sections]
        v_stmt = select(SectionVersion).where(SectionVersion.section_id.in_(sec_ids))
        v_result = await db.execute(v_stmt)
        all_versions = list(v_result.scalars().all())

        # Group by section_id
        versions_by_sec: dict[uuid.UUID, list[SectionVersion]] = defaultdict(list)
        for v in all_versions:
            versions_by_sec[v.section_id].append(v)

        # Build response dicts
        items = []
        for s in sections:
            sec_versions = versions_by_sec.get(s.id, [])
            current_content = None
            if sec_versions:
                latest = max(sec_versions, key=lambda v: v.version_number)
                current_content = latest.content

            items.append(
                {
                    "id": str(s.id),
                    "task_id": str(s.task_id),
                    "title": s.title,
                    "level": s.level,
                    "description": s.description,
                    "target_word_count": s.target_word_count,
                    "order_index": s.order_index,
                    "status": s.status,
                    "current_content": current_content,
                    "version_count": len(sec_versions),
                }
            )

        return items

    async def get_section(self, db: AsyncSession, section_id: str) -> Section | None:
        """Get a single section by ID."""
        stmt = select(Section).where(Section.id == uuid.UUID(section_id))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_section_versions(
        self, db: AsyncSession, section_id: str
    ) -> list[SectionVersion]:
        """Get all versions for a section, ordered by version_number."""
        stmt = (
            select(SectionVersion)
            .where(SectionVersion.section_id == uuid.UUID(section_id))
            .order_by(SectionVersion.version_number)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Update section content (creates a new version)
    # ------------------------------------------------------------------
    async def update_section_content(
        self,
        db: AsyncSession,
        section_id: str,
        content: str,
        change_summary: str | None = None,
    ) -> SectionVersion:
        """Create a new SectionVersion. version_number = max(existing) + 1."""
        # Verify section exists
        section = await self.get_section(db, section_id)
        if section is None:
            raise HTTPException(status_code=404, detail="Section not found")

        # Determine next version number
        stmt = select(func.max(SectionVersion.version_number)).where(
            SectionVersion.section_id == uuid.UUID(section_id)
        )
        result = await db.execute(stmt)
        max_ver = result.scalar_one_or_none() or 0
        new_ver = max_ver + 1

        # Compute word count
        word_count = len(content.split())

        version = SectionVersion(
            id=uuid.uuid4(),
            section_id=uuid.UUID(section_id),
            version_number=new_ver,
            content=content,
            word_count=word_count,
            change_source="manual",
            change_summary=change_summary,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        return version
