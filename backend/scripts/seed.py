"""Idempotent database seed utilities for demo and reference data."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import TypedDict, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from core.database import async_session_maker
from models import (
    KnowledgeChunk,
    Section,
    SectionVersion,
    Task,
    TaskConfig,
)
from services.template_service import TemplateService

DEMO_TASK_NAME = "示例投标书 — 智慧城市项目"
DEMO_DOC_TYPE = "投标书"
DEMO_TASK_STATUS = "approved"


class DemoSection(TypedDict):
    title: str
    content: str
    description: str
    target_word_count: int


class DemoKnowledgeDoc(TypedDict):
    document_id: uuid.UUID
    filename: str
    content: str


DEMO_SECTIONS: list[DemoSection] = [
    {
        "title": "公司概况",
        "content": "示例公司成立于 2015 年，专注智慧城市项目交付，具备完善的研发、实施与运维能力。",
        "description": "示例公司基础介绍与交付能力说明。",
        "target_word_count": 300,
    },
    {
        "title": "项目理解",
        "content": "我们理解本项目关注城市治理协同、数据互联与可持续运营，方案强调稳定、可扩展与易维护。",
        "description": "对智慧城市项目目标、范围与痛点的理解。",
        "target_word_count": 350,
    },
    {
        "title": "技术方案",
        "content": "",
        "description": "示例公司的技术架构、平台能力与集成方案。",
        "target_word_count": 900,
    },
    {
        "title": "实施计划",
        "content": "",
        "description": "分阶段实施、验收节点与资源安排。",
        "target_word_count": 700,
    },
    {
        "title": "项目团队",
        "content": "",
        "description": "项目经理、架构师与交付团队配置。",
        "target_word_count": 500,
    },
    {
        "title": "商务报价",
        "content": "",
        "description": "报价原则、费用组成与付款节点说明。",
        "target_word_count": 450,
    },
]

DEMO_KNOWLEDGE_DOCS: list[DemoKnowledgeDoc] = [
    {
        "document_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "filename": "投标书最佳实践-结构清晰.txt",
        "content": "投标书应先回应招标要求，再展开技术与商务说明；目录层级保持简洁，避免跳跃。",
    },
    {
        "document_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "filename": "投标书最佳实践-量化表达.txt",
        "content": "示例公司在投标书中应优先使用可验证的指标，如交付周期、响应时效与验收标准。",
    },
    {
        "document_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "filename": "投标书最佳实践-风险控制.txt",
        "content": "风险控制章节需要明确识别集成、进度、资源与验收风险，并给出可执行的应对措施。",
    },
    {
        "document_id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "filename": "投标书最佳实践-团队配置.txt",
        "content": "团队介绍应突出角色分工、项目经验与驻场安排，避免堆砌头衔而缺少实际职责。",
    },
    {
        "document_id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "filename": "投标书最佳实践-报价说明.txt",
        "content": "商务报价部分要清晰列示范围边界、报价口径与付款条件，确保评审方易于比较。",
    },
]

ZERO_EMBEDDING = [0.0] * 1536
T = TypeVar("T")


@dataclass(slots=True)
class SeedSummary:
    templates_inserted: int = 0
    demo_task_created: bool = False
    sections_created: int = 0
    section_versions_created: int = 0
    knowledge_chunks_created: int = 0


def _seed_demo_flag(value: str | None = None) -> bool:
    raw = os.getenv("SEED_DEMO_DATA", "true") if value is None else value
    return raw.lower() == "true"


async def _get_one(session: AsyncSession, stmt: Select[tuple[T]]) -> T | None:
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _seed_demo_task(session: AsyncSession) -> tuple[bool, int, int]:
    task = await _get_one(session, select(Task).where(Task.name == DEMO_TASK_NAME))
    created_task = False
    if task is None:
        task = Task(
            name=DEMO_TASK_NAME, doc_type=DEMO_DOC_TYPE, status=DEMO_TASK_STATUS
        )
        session.add(task)
        await session.flush()
        created_task = True
    else:
        task.doc_type = DEMO_DOC_TYPE
        task.status = DEMO_TASK_STATUS

    config = await _get_one(
        session, select(TaskConfig).where(TaskConfig.task_id == task.id)
    )
    if config is None:
        config = TaskConfig(
            task_id=task.id, outline_approved=True, final_approved=False
        )
        session.add(config)
    else:
        config.outline_approved = True
        config.final_approved = False

    await session.flush()

    sections_created = 0
    versions_created = 0
    for index, section_data in enumerate(DEMO_SECTIONS):
        section = await _get_one(
            session,
            select(Section).where(
                Section.task_id == task.id,
                Section.title == section_data["title"],
            ),
        )
        is_generated = index < 2
        if section is None:
            section = Section(
                task_id=task.id,
                title=section_data["title"],
                level=1,
                description=section_data.get("description"),
                target_word_count=section_data.get("target_word_count", 500),
                order_index=index,
                status="generated" if is_generated else "draft",
            )
            session.add(section)
            sections_created += 1
            await session.flush()
        else:
            section.level = 1
            section.description = section_data.get("description")
            section.target_word_count = section_data.get("target_word_count", 500)
            section.order_index = index
            if is_generated:
                section.status = "generated"

        if is_generated:
            version = await _get_one(
                session,
                select(SectionVersion).where(
                    SectionVersion.section_id == section.id,
                    SectionVersion.version_number == 1,
                ),
            )
            if version is None:
                session.add(
                    SectionVersion(
                        section_id=section.id,
                        version_number=1,
                        content=section_data["content"],
                        word_count=len(section_data["content"].split()),
                        change_source="seed",
                        change_summary="Seeded sample Chinese content.",
                    )
                )
                versions_created += 1
            else:
                version.content = section_data["content"]
                version.word_count = len(section_data["content"].split())
                version.change_source = "seed"
                version.change_summary = "Seeded sample Chinese content."

    return created_task, sections_created, versions_created


async def _seed_knowledge_chunks(session: AsyncSession) -> int:
    created = 0
    for doc in DEMO_KNOWLEDGE_DOCS:
        chunk = await _get_one(
            session,
            select(KnowledgeChunk).where(
                KnowledgeChunk.document_id == doc["document_id"],
                KnowledgeChunk.chunk_index == 0,
            ),
        )
        if chunk is None:
            session.add(
                KnowledgeChunk(
                    document_id=doc["document_id"],
                    filename=doc["filename"],
                    chunk_index=0,
                    content=doc["content"],
                    embedding=ZERO_EMBEDDING,
                    metadata_={"seeded": True, "topic": "bid_best_practices"},
                )
            )
            created += 1
        else:
            chunk.filename = doc["filename"]
            chunk.content = doc["content"]
            chunk.embedding = ZERO_EMBEDDING
            chunk.metadata_ = {"seeded": True, "topic": "bid_best_practices"}
    return created


async def seed_database(seed_demo_data: bool | None = None) -> SeedSummary:
    """Seed builtin templates and optional demo content."""

    demo_enabled = _seed_demo_flag() if seed_demo_data is None else seed_demo_data
    summary = SeedSummary()

    async with async_session_maker() as session:
        template_service = TemplateService()
        summary.templates_inserted = await template_service.seed_builtin_templates(
            session
        )

        if demo_enabled:
            task_created, sections_created, versions_created = await _seed_demo_task(
                session
            )
            summary.demo_task_created = task_created
            summary.sections_created = sections_created
            summary.section_versions_created = versions_created
            summary.knowledge_chunks_created = await _seed_knowledge_chunks(session)

        await session.commit()

    return summary


async def _async_main() -> int:
    summary = await seed_database()
    print(
        "[seed] templates=%s demo_task=%s sections=%s versions=%s knowledge=%s"
        % (
            summary.templates_inserted,
            "created" if summary.demo_task_created else "existing",
            summary.sections_created,
            summary.section_versions_created,
            summary.knowledge_chunks_created,
        )
    )
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
