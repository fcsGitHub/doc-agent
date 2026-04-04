"""Version management service — create, list, diff, rollback section versions."""

from __future__ import annotations

import difflib
import re
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.section import Section, SectionVersion
from services.audit_service import AuditService


class VersionService:
    """Service encapsulating section version operations."""

    _audit = AuditService()

    # ------------------------------------------------------------------
    # Create version
    # ------------------------------------------------------------------
    async def create_version(
        self,
        db: AsyncSession,
        section_id: str,
        content: str,
        source: str,
        summary: str | None = None,
    ) -> SectionVersion:
        """Create a new SectionVersion. version_number = max(existing) + 1."""
        # Determine next version number
        stmt = select(func.max(SectionVersion.version_number)).where(
            SectionVersion.section_id == uuid.UUID(section_id)
        )
        result = await db.execute(stmt)
        max_ver = result.scalar_one_or_none() or 0
        new_ver = max_ver + 1

        word_count = len(content.split())

        version = SectionVersion(
            id=uuid.uuid4(),
            section_id=uuid.UUID(section_id),
            version_number=new_ver,
            content=content,
            word_count=word_count,
            change_source=source,
            change_summary=summary,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        return version

    # ------------------------------------------------------------------
    # List versions
    # ------------------------------------------------------------------
    async def get_versions(
        self, db: AsyncSession, section_id: str
    ) -> list[SectionVersion]:
        """Get all versions for a section, ordered by version_number ASC."""
        stmt = (
            select(SectionVersion)
            .where(SectionVersion.section_id == uuid.UUID(section_id))
            .order_by(SectionVersion.version_number)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Get single version
    # ------------------------------------------------------------------
    async def get_version(
        self, db: AsyncSession, version_id: str
    ) -> SectionVersion | None:
        """Get a single version by its ID."""
        stmt = select(SectionVersion).where(SectionVersion.id == uuid.UUID(version_id))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------
    async def get_diff(
        self, db: AsyncSession, version_a_id: str, version_b_id: str
    ) -> dict[str, Any]:
        """Compute a unified diff between two versions."""
        ver_a = await self.get_version(db, version_a_id)
        ver_b = await self.get_version(db, version_b_id)

        if ver_a is None or ver_b is None:
            raise HTTPException(status_code=404, detail="Version not found")

        lines_a = ver_a.content.splitlines(keepends=True)
        lines_b = ver_b.content.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(
                lines_a,
                lines_b,
                fromfile=f"v{ver_a.version_number}",
                tofile=f"v{ver_b.version_number}",
                lineterm="",
            )
        )

        return self._parse_unified_diff(diff_lines)

    def _parse_unified_diff(self, diff_lines: list[str]) -> dict[str, Any]:
        """Parse unified diff output into structured DiffResult."""
        hunks: list[dict[str, Any]] = []
        additions = 0
        deletions = 0

        current_hunk: dict[str, Any] | None = None

        for line in diff_lines:
            # Skip file headers
            if line.startswith("---") or line.startswith("+++"):
                continue

            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            hunk_match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if hunk_match:
                current_hunk = {
                    "old_start": int(hunk_match.group(1)),
                    "old_count": int(hunk_match.group(2) or "1"),
                    "new_start": int(hunk_match.group(3)),
                    "new_count": int(hunk_match.group(4) or "1"),
                    "lines": [],
                }
                hunks.append(current_hunk)
                continue

            if current_hunk is None:
                continue

            if line.startswith("+"):
                current_hunk["lines"].append({"type": "added", "content": line[1:]})
                additions += 1
            elif line.startswith("-"):
                current_hunk["lines"].append({"type": "removed", "content": line[1:]})
                deletions += 1
            else:
                # Context line (starts with space or is empty)
                content = line[1:] if line.startswith(" ") else line
                current_hunk["lines"].append({"type": "context", "content": content})

        return {
            "additions": additions,
            "deletions": deletions,
            "hunks": hunks,
        }

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------
    async def rollback_section(
        self, db: AsyncSession, section_id: str, target_version_id: str
    ) -> SectionVersion:
        """Rollback a section to a target version by creating a NEW version."""
        target = await self.get_version(db, target_version_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Target version not found")

        # Verify the target version belongs to this section
        if str(target.section_id) != section_id:
            raise HTTPException(
                status_code=400,
                detail="Target version does not belong to this section",
            )

        result = await self.create_version(
            db=db,
            section_id=section_id,
            content=target.content,
            source="manual",
            summary=f"回滚到版本 {target.version_number}",
        )

        # Best-effort audit logging
        try:
            sec_stmt = select(Section).where(Section.id == uuid.UUID(section_id))
            sec_result = await db.execute(sec_stmt)
            section = sec_result.scalar_one_or_none()
            if section and section.task_id:
                await self._audit.log(
                    db,
                    task_id=str(section.task_id),
                    action="version_rolled_back",
                    entity_type="section_version",
                    entity_id=str(result.id),
                    details={
                        "section_id": section_id,
                        "target_version": target.version_number,
                    },
                )
        except Exception:
            pass

        return result
