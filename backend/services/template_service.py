"""Template service — CRUD operations and template application."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.section import Section
from models.task import Task
from models.template import DocumentTemplate

# ---------------------------------------------------------------------------
# Built-in template data
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "投标书",
        "doc_type": "投标书",
        "description": "标准投标书模板，包含公司概况、项目理解、技术方案等章节",
        "outline_structure": {
            "sections": [
                {"title": "公司概况", "level": 1},
                {"title": "项目理解", "level": 1},
                {"title": "技术方案", "level": 1},
                {"title": "实施计划", "level": 1},
                {"title": "项目团队", "level": 1},
                {"title": "商务报价", "level": 1},
            ]
        },
        "is_active": True,
    },
    {
        "name": "技术方案",
        "doc_type": "技术方案",
        "description": "技术方案模板，包含背景分析、需求分析、技术架构等章节",
        "outline_structure": {
            "sections": [
                {"title": "背景分析", "level": 1},
                {"title": "需求分析", "level": 1},
                {"title": "技术架构", "level": 1},
                {"title": "实施计划", "level": 1},
                {"title": "风险管理", "level": 1},
            ]
        },
        "is_active": True,
    },
    {
        "name": "可行性报告",
        "doc_type": "可行性报告",
        "description": "可行性研究报告模板，包含项目背景、市场分析、技术可行性等章节",
        "outline_structure": {
            "sections": [
                {"title": "项目背景", "level": 1},
                {"title": "市场分析", "level": 1},
                {"title": "技术可行性", "level": 1},
                {"title": "经济分析", "level": 1},
                {"title": "结论建议", "level": 1},
            ]
        },
        "is_active": True,
    },
]


class TemplateService:
    """Service encapsulating template CRUD and application."""

    # ------------------------------------------------------------------
    # List templates (optional doc_type filter)
    # ------------------------------------------------------------------
    async def get_templates(
        self, db: AsyncSession, doc_type: str | None = None
    ) -> list[DocumentTemplate]:
        """Return all templates, optionally filtered by doc_type."""
        stmt = select(DocumentTemplate)
        if doc_type is not None:
            stmt = stmt.where(DocumentTemplate.doc_type == doc_type)
        stmt = stmt.order_by(DocumentTemplate.created_at)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Get single template
    # ------------------------------------------------------------------
    async def get_template(
        self, db: AsyncSession, template_id: str
    ) -> DocumentTemplate | None:
        """Return a single template by ID, or None."""
        stmt = select(DocumentTemplate).where(
            DocumentTemplate.id == uuid.UUID(template_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Create template
    # ------------------------------------------------------------------
    async def create_template(
        self, db: AsyncSession, data: dict[str, Any]
    ) -> DocumentTemplate:
        """Create a new template from a data dict."""
        template = DocumentTemplate(**data)
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template

    # ------------------------------------------------------------------
    # Apply template to a task — creates Section rows
    # ------------------------------------------------------------------
    async def apply_template(
        self, db: AsyncSession, task_id: str, template_id: str
    ) -> list[Section]:
        """Read template.outline_structure and create Section rows for the task."""
        # Validate task exists
        task_stmt = select(Task).where(Task.id == uuid.UUID(task_id))
        task_result = await db.execute(task_stmt)
        task = task_result.scalar_one_or_none()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        # Validate template exists
        template = await self.get_template(db, template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Template not found")

        # Read outline_structure sections
        outline = template.outline_structure or {}  # pyright: ignore[reportAttributeAccessIssue]
        section_defs: list[dict[str, Any]] = outline.get("sections", [])

        if not section_defs:
            raise HTTPException(
                status_code=400, detail="Template has no sections defined"
            )

        # Create Section rows
        created_sections: list[Section] = []
        task_uuid = uuid.UUID(task_id)

        for idx, sec_def in enumerate(section_defs):
            section = Section(
                task_id=task_uuid,
                title=sec_def.get("title", f"Section {idx + 1}"),
                level=sec_def.get("level", 1),
                order_index=idx,
                status="draft",
            )
            db.add(section)
            created_sections.append(section)

        await db.flush()  # populate IDs
        await db.commit()

        # Refresh all to get DB-generated fields
        for section in created_sections:
            await db.refresh(section)

        return created_sections

    # ------------------------------------------------------------------
    # Seed built-in templates (idempotent)
    # ------------------------------------------------------------------
    async def seed_builtin_templates(self, db: AsyncSession) -> int:
        """Insert built-in templates if they don't already exist. Returns count inserted."""
        inserted = 0
        for tpl_data in BUILTIN_TEMPLATES:
            # Check if template with same name already exists
            stmt = select(DocumentTemplate).where(
                DocumentTemplate.name == tpl_data["name"]
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing is None:
                template = DocumentTemplate(**tpl_data)
                db.add(template)
                inserted += 1

        if inserted > 0:
            await db.commit()

        return inserted
