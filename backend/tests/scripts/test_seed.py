"""Integration tests for the database seed script."""

from __future__ import annotations

from sqlalchemy import delete, select

import pytest

from core.database import async_session_maker, engine
from models import DocumentTemplate, KnowledgeChunk, Section, SectionVersion, Task
from scripts.seed import (
    DEMO_KNOWLEDGE_DOCS,
    DEMO_SECTIONS,
    DEMO_TASK_NAME,
    seed_database,
)
from services.template_service import BUILTIN_TEMPLATES


async def _cleanup_demo_data() -> None:
    async with async_session_maker() as db:
        _ = await db.execute(delete(Task).where(Task.name == DEMO_TASK_NAME))
        _ = await db.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.document_id.in_(
                    [doc["document_id"] for doc in DEMO_KNOWLEDGE_DOCS]
                )
            )
        )
        await db.commit()


async def _reset_engine() -> None:
    await engine.dispose()


async def _snapshot_demo_state() -> dict[str, int]:
    async with async_session_maker() as db:
        task = (
            await db.execute(select(Task).where(Task.name == DEMO_TASK_NAME))
        ).scalar_one_or_none()
        if task is None:
            return {
                "tasks": 0,
                "sections": 0,
                "generated_sections": 0,
                "versions": 0,
                "knowledge_chunks": 0,
            }

        section_rows = (
            (await db.execute(select(Section).where(Section.task_id == task.id)))
            .scalars()
            .all()
        )
        version_rows = (
            (
                await db.execute(
                    select(SectionVersion).where(
                        SectionVersion.section_id.in_(
                            [section.id for section in section_rows]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        knowledge_rows = (
            (
                await db.execute(
                    select(KnowledgeChunk).where(
                        KnowledgeChunk.document_id.in_(
                            [doc["document_id"] for doc in DEMO_KNOWLEDGE_DOCS]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )

        return {
            "tasks": 1,
            "sections": len(section_rows),
            "generated_sections": len(
                [section for section in section_rows if section.status == "generated"]
            ),
            "versions": len(version_rows),
            "knowledge_chunks": len(knowledge_rows),
        }


@pytest.mark.asyncio
async def test_seed_demo_data_false_only_seeds_templates() -> None:
    await _reset_engine()
    await _cleanup_demo_data()

    _ = await seed_database(seed_demo_data=False)

    async with async_session_maker() as db:
        templates = (
            (
                await db.execute(
                    select(DocumentTemplate).where(
                        DocumentTemplate.name.in_(
                            [tpl["name"] for tpl in BUILTIN_TEMPLATES]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        task = (
            await db.execute(select(Task).where(Task.name == DEMO_TASK_NAME))
        ).scalar_one_or_none()
        knowledge_rows = (
            (
                await db.execute(
                    select(KnowledgeChunk).where(
                        KnowledgeChunk.document_id.in_(
                            [doc["document_id"] for doc in DEMO_KNOWLEDGE_DOCS]
                        )
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(templates) == 3
    assert task is None
    assert knowledge_rows == []

    await _cleanup_demo_data()
    await _reset_engine()


@pytest.mark.asyncio
async def test_seed_demo_data_is_idempotent() -> None:
    await _reset_engine()
    await _cleanup_demo_data()

    _ = await seed_database(seed_demo_data=True)
    first = await _snapshot_demo_state()

    _ = await seed_database(seed_demo_data=True)
    second = await _snapshot_demo_state()

    assert first == second
    assert second["tasks"] == 1
    assert second["sections"] == len(DEMO_SECTIONS)
    assert second["generated_sections"] == 2
    assert second["versions"] == 2
    assert second["knowledge_chunks"] == len(DEMO_KNOWLEDGE_DOCS)

    await _cleanup_demo_data()
    await _reset_engine()
