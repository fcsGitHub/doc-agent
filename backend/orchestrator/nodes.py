"""Async node implementations for the LangGraph generation pipeline."""
# pyright: reportAny=false, reportExplicitAny=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnusedImport=false, reportUnusedCallResult=false, reportUnnecessaryIsInstance=false

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure skill modules register themselves on import.
import skills.extract_requirements  # noqa: F401
import skills.outline  # noqa: F401
import skills.parse  # noqa: F401
import skills.rewrite  # noqa: F401
import skills.write_section  # noqa: F401
from models.document import ParsedDocument, SourceDocument
from models.review import ReviewRound
from models.section import Section
from models.section import SectionVersion
from models.skill import SkillExecution
from orchestrator.state import DocumentState
from services.progress_service import ProgressEvent, get_progress_service
from skills.base import SkillContext, SkillResult
from skills.registry import get_skill_registry


def _to_task_uuid(task_id: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(task_id)
    except Exception:
        return None


async def _publish(
    task_id: str,
    event_type: str,
    phase: str,
    progress_pct: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    svc = get_progress_service()
    await svc.publish(
        task_id,
        ProgressEvent(
            event_type=event_type,
            task_id=task_id,
            phase=phase,
            progress_pct=progress_pct,
            message=message,
            data=data or {},
        ),
    )


async def _record_execution(
    db: AsyncSession | None,
    task_id: str,
    skill_name: str,
    result: SkillResult,
    input_data: dict[str, Any],
    duration_ms: int,
) -> None:
    if db is None:
        return
    task_uuid = _to_task_uuid(task_id)
    if task_uuid is None:
        return
    try:
        exec_record = SkillExecution(
            id=uuid.uuid4(),
            task_id=task_uuid,
            skill_name=skill_name,
            status="completed" if result.success else "failed",
            input_data=input_data,
            output_data=result.output,
            error_message=result.error,
            tokens_used=result.tokens_used or 0,
            duration_ms=duration_ms,
        )
        db.add(exec_record)
        await db.flush()
    except Exception:
        # Best effort only.
        pass


async def parse_node(
    state: DocumentState,
    db: AsyncSession,
    llm_client: Any,
) -> dict[str, object]:
    task_id = state["task_id"]
    await _publish(task_id, "phase_change", "parsing", 5, "开始解析文档...")

    try:
        task_uuid = _to_task_uuid(task_id)
        source_doc = None
        if task_uuid is not None:
            stmt = (
                select(SourceDocument)
                .where(SourceDocument.task_id == task_uuid)
                .order_by(SourceDocument.created_at)
            )
            res = await db.execute(stmt)
            source_doc = res.scalars().first()

        input_data: dict[str, Any] = {"task_id": task_id}
        if source_doc is not None:
            input_data.update(
                {
                    "source_document_id": str(source_doc.id),
                    "file_path": source_doc.file_path,
                    "file_type": source_doc.file_type,
                }
            )

        skill = get_skill_registry().get("document_parse")
        ctx = SkillContext(
            task_id=task_id,
            section_id=None,
            llm_client=llm_client,
            db_session=db,
            input_data=input_data,
        )

        start = time.time()
        result = await skill.execute(ctx)
        duration_ms = int((time.time() - start) * 1000)

        await _record_execution(
            db=db,
            task_id=task_id,
            skill_name="document_parse",
            result=result,
            input_data=input_data,
            duration_ms=duration_ms,
        )

        if result.error and not result.success:
            await _publish(
                task_id,
                "error",
                "parsing",
                10,
                f"解析失败: {result.error}",
            )
            return {
                "current_phase": "parsing",
                "progress_pct": 10,
                "progress_message": "文档解析失败",
                "error": result.error,
            }

        await _publish(task_id, "phase_change", "parsing", 10, "文档解析完成")
        return {
            "current_phase": "parsing",
            "progress_pct": 10,
            "progress_message": "文档解析完成",
        }
    except Exception as exc:
        msg = str(exc)
        await _publish(task_id, "error", "parsing", 10, f"解析失败: {msg}")
        return {
            "current_phase": "parsing",
            "progress_pct": 10,
            "progress_message": "文档解析失败",
            "error": msg,
        }


async def extract_requirements_node(
    state: DocumentState,
    db: AsyncSession,
    llm_client: Any,
) -> dict[str, object]:
    task_id = state["task_id"]
    await _publish(
        task_id,
        "phase_change",
        "extracting",
        15,
        "开始提取需求...",
    )

    try:
        task_uuid = _to_task_uuid(task_id)
        parsed_text = ""
        if task_uuid is not None:
            stmt = select(ParsedDocument).where(ParsedDocument.task_id == task_uuid)
            res = await db.execute(stmt)
            parsed_doc = res.scalars().first()
            parsed_text = (
                parsed_doc.raw_text if parsed_doc and parsed_doc.raw_text else ""
            )

        input_data = {
            "task_id": task_id,
            "parsed_text": parsed_text,
            "doc_type": "report",
        }
        skill = get_skill_registry().get("requirement_extraction")
        ctx = SkillContext(
            task_id=task_id,
            section_id=None,
            llm_client=llm_client,
            db_session=db,
            input_data=input_data,
        )

        start = time.time()
        result = await skill.execute(ctx)
        duration_ms = int((time.time() - start) * 1000)

        await _record_execution(
            db=db,
            task_id=task_id,
            skill_name="requirement_extraction",
            result=result,
            input_data=input_data,
            duration_ms=duration_ms,
        )

        if result.error and not result.success:
            await _publish(
                task_id,
                "error",
                "extracting",
                20,
                f"需求提取失败: {result.error}",
            )
            return {
                "current_phase": "extracting",
                "progress_pct": 20,
                "progress_message": "需求提取失败",
                "error": result.error,
            }

        await _publish(task_id, "phase_change", "extracting", 20, "需求提取完成")
        return {
            "current_phase": "extracting",
            "progress_pct": 20,
            "progress_message": "需求提取完成",
        }
    except Exception as exc:
        msg = str(exc)
        await _publish(task_id, "error", "extracting", 20, f"需求提取失败: {msg}")
        return {
            "current_phase": "extracting",
            "progress_pct": 20,
            "progress_message": "需求提取失败",
            "error": msg,
        }


async def plan_outline_node(
    state: DocumentState,
    db: AsyncSession,
    llm_client: Any,
) -> dict[str, object]:
    task_id = state["task_id"]
    await _publish(task_id, "phase_change", "planning", 25, "开始规划大纲...")

    try:
        task_uuid = _to_task_uuid(task_id)
        requirements: list[dict[str, Any]] = []
        if task_uuid is not None:
            stmt_req = (
                select(SkillExecution)
                .where(
                    SkillExecution.task_id == task_uuid,
                    SkillExecution.skill_name == "requirement_extraction",
                )
                .order_by(SkillExecution.created_at.desc())
            )
            req_res = await db.execute(stmt_req)
            req_exec = req_res.scalars().first()
            if req_exec and isinstance(req_exec.output_data, dict):
                raw_requirements = req_exec.output_data.get("requirements", [])
                if isinstance(raw_requirements, list):
                    requirements = [r for r in raw_requirements if isinstance(r, dict)]

        input_data = {
            "task_id": task_id,
            "doc_type": "report",
            "requirements": requirements,
        }
        skill = get_skill_registry().get("outline_planning")
        ctx = SkillContext(
            task_id=task_id,
            section_id=None,
            llm_client=llm_client,
            db_session=db,
            input_data=input_data,
        )

        start = time.time()
        result = await skill.execute(ctx)
        duration_ms = int((time.time() - start) * 1000)

        await _record_execution(
            db=db,
            task_id=task_id,
            skill_name="outline_planning",
            result=result,
            input_data=input_data,
            duration_ms=duration_ms,
        )

        if result.error and not result.success:
            await _publish(
                task_id,
                "error",
                "planning",
                35,
                f"大纲规划失败: {result.error}",
            )
            return {
                "current_phase": "planning",
                "progress_pct": 35,
                "progress_message": "大纲规划失败",
                "error": result.error,
            }

        sec_ids: list[str] = []
        if task_uuid is not None:
            stmt_sec = select(Section.id).where(Section.task_id == task_uuid)
            sec_res = await db.execute(stmt_sec)
            sec_ids = [str(r) for r in sec_res.scalars().all()]

        await _publish(task_id, "phase_change", "planning", 35, "大纲规划完成")
        return {
            "current_phase": "planning",
            "progress_pct": 35,
            "progress_message": "大纲规划完成",
            "section_ids": sec_ids,
        }
    except Exception as exc:
        msg = str(exc)
        await _publish(task_id, "error", "planning", 35, f"大纲规划失败: {msg}")
        return {
            "current_phase": "planning",
            "progress_pct": 35,
            "progress_message": "大纲规划失败",
            "error": msg,
        }


async def generate_sections_node(
    state: DocumentState,
    db: AsyncSession,
    llm_client: Any,
) -> dict[str, object]:
    task_id = state["task_id"]
    await _publish(task_id, "phase_change", "generating", 40, "开始生成章节...")

    try:
        task_uuid = _to_task_uuid(task_id)
        if task_uuid is None:
            await _publish(task_id, "error", "generating", 40, "任务ID格式无效")
            return {
                "current_phase": "generating",
                "progress_pct": 40,
                "progress_message": "章节生成失败",
                "error": "Invalid task_id",
            }

        stmt_sections = (
            select(Section)
            .where(Section.task_id == task_uuid)
            .order_by(Section.order_index.asc())
        )
        sec_res = await db.execute(stmt_sections)
        sections = sec_res.scalars().all()

        if not sections:
            await _publish(task_id, "phase_change", "generating", 90, "无章节可生成")
            return {
                "current_phase": "generating",
                "progress_pct": 90,
                "progress_message": "无章节可生成",
                "current_section_index": 0,
            }

        skill = get_skill_registry().get("section_writing")
        preceding_sections: list[dict[str, str]] = []
        total = len(sections)

        for idx, section in enumerate(sections):
            input_data = {
                "task_id": task_id,
                "section_id": str(section.id),
                "section_title": section.title,
                "section_description": section.description or "",
                "target_word_count": section.target_word_count,
                "context": {
                    "requirements": [],
                    "preceding_sections": preceding_sections,
                    "style_guide": None,
                    "knowledge_excerpts": [],
                },
            }
            ctx = SkillContext(
                task_id=task_id,
                section_id=str(section.id),
                llm_client=llm_client,
                db_session=db,
                input_data=input_data,
            )

            start = time.time()
            result = await skill.execute(ctx)
            duration_ms = int((time.time() - start) * 1000)

            await _record_execution(
                db=db,
                task_id=task_id,
                skill_name="section_writing",
                result=result,
                input_data=input_data,
                duration_ms=duration_ms,
            )

            progress_pct = min(90, 40 + int(((idx + 1) / total) * 50))

            if result.error and not result.success:
                await _publish(
                    task_id,
                    "error",
                    "generating",
                    progress_pct,
                    f"章节生成失败: {result.error}",
                )
                return {
                    "current_phase": "generating",
                    "progress_pct": progress_pct,
                    "progress_message": "章节生成失败",
                    "current_section_index": idx,
                    "error": result.error,
                }

            content = str(result.output.get("content", ""))
            preceding_sections.append(
                {
                    "title": section.title,
                    "summary": content[:160],
                }
            )

            await _publish(
                task_id,
                "section_complete",
                "generating",
                progress_pct,
                f"章节完成: {section.title}",
                data={"section_id": str(section.id), "section_index": idx + 1},
            )
            await _publish(
                task_id,
                "progress",
                "generating",
                progress_pct,
                f"章节生成进度 {idx + 1}/{total}",
            )

        return {
            "current_phase": "generating",
            "progress_pct": 90,
            "progress_message": "章节生成完成",
            "current_section_index": total,
        }
    except Exception as exc:
        msg = str(exc)
        await _publish(task_id, "error", "generating", 90, f"章节生成失败: {msg}")
        return {
            "current_phase": "generating",
            "progress_pct": 90,
            "progress_message": "章节生成失败",
            "error": msg,
        }


async def run_reviews_node(
    state: DocumentState,
    db: AsyncSession,
    llm_client: Any,
) -> dict[str, object]:
    task_id = state["task_id"]
    review_round = state["review_round"] + 1

    await _publish(
        task_id,
        "review_started",
        "reviewing",
        72,
        f"审核轮次 {review_round} 开始",
        data={"review_round": review_round},
    )

    try:
        task_uuid = _to_task_uuid(task_id)
        if task_uuid is None:
            raise ValueError("Invalid task_id")

        stmt_doc = (
            select(ParsedDocument)
            .where(ParsedDocument.task_id == task_uuid)
            .order_by(ParsedDocument.created_at.desc())
        )
        doc_res = await db.execute(stmt_doc)
        parsed_doc = doc_res.scalars().first()
        if parsed_doc is None:
            raise ValueError("Parsed document not found for task")

        from services.review_service import ReviewService

        aggregated = await ReviewService().run_all_reviews(
            task_id=task_id,
            document_id=str(parsed_doc.id),
            review_round=review_round,
            db=db,
            llm_client=llm_client,
        )

        status = aggregated.overall_status
        if status == "approved":
            review_passed = True
            revision_needed_section_ids: list[str] = []
        elif status == "needs_revision":
            review_passed = False

            issues_any: Any = getattr(aggregated, "issues", None)
            if issues_any is None:
                issues_any = [
                    issue
                    for reviewer_result in getattr(aggregated, "reviewer_results", [])
                    for issue in getattr(reviewer_result, "issues", [])
                ]
            issues: list[Any] = issues_any if isinstance(issues_any, list) else []

            section_ids: set[str] = set()
            for issue in issues:
                if isinstance(issue, dict):
                    issue_dict: dict[str, Any] = issue
                    section_id = issue_dict.get("section_id")
                    requires_human = bool(issue_dict.get("requires_human", False))
                else:
                    section_id = getattr(issue, "section_id", None)
                    requires_human = bool(getattr(issue, "requires_human", False))
                if section_id and not requires_human:
                    section_ids.add(str(section_id))
            revision_needed_section_ids = list(section_ids)
        else:
            review_passed = False
            revision_needed_section_ids = []

        await _publish(
            task_id,
            "review_complete",
            "reviewing",
            75,
            f"审核轮次 {review_round} 完成",
            data={
                "review_round": review_round,
                "overall_status": status,
                "review_passed": review_passed,
            },
        )

        return {
            "current_phase": "reviewing",
            "progress_pct": 75,
            "progress_message": "自动审核完成",
            "review_round": review_round,
            "review_passed": review_passed,
            "revision_needed_section_ids": revision_needed_section_ids,
        }
    except Exception as exc:
        msg = str(exc)
        await _publish(task_id, "error", "reviewing", 75, f"审核失败: {msg}")
        return {
            "current_phase": "reviewing",
            "progress_pct": 75,
            "progress_message": "自动审核失败",
            "review_round": review_round,
            "review_passed": False,
            "revision_needed_section_ids": [],
            "error": msg,
        }


def _extract_section_issues_from_round(
    round_results: dict[str, Any],
    section_id: str,
) -> list[dict[str, Any]]:
    reviewer_results = round_results.get("reviewer_results", [])
    if not isinstance(reviewer_results, list):
        return []

    section_issues: list[dict[str, Any]] = []
    for reviewer_result in reviewer_results:
        if not isinstance(reviewer_result, dict):
            continue
        issues = reviewer_result.get("issues", [])
        if not isinstance(issues, list):
            continue
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            issue_dict: dict[str, Any] = issue
            if str(issue_dict.get("section_id", "")) != section_id:
                continue
            if bool(issue_dict.get("requires_human", False)):
                continue
            section_issues.append(issue_dict)
    return section_issues


async def revise_sections_node(
    state: DocumentState,
    db: AsyncSession,
    llm_client: Any,
) -> dict[str, object]:
    task_id = state["task_id"]
    review_round = state["review_round"]
    section_ids = state["revision_needed_section_ids"]

    await _publish(
        task_id,
        f"revision_round_{review_round}_started",
        "revising",
        65,
        f"修订轮次 {review_round} 开始",
        data={"review_round": review_round, "section_count": len(section_ids)},
    )

    if not section_ids:
        await _publish(
            task_id,
            f"revision_round_{review_round}_complete",
            "revising",
            70,
            f"修订轮次 {review_round} 完成（无需修订）",
            data={"review_round": review_round, "revised_sections": 0},
        )
        return {
            "current_phase": "revising",
            "progress_pct": 70,
            "progress_message": "无需修订章节",
        }

    task_uuid = _to_task_uuid(task_id)
    latest_round_results: dict[str, Any] = {}
    if task_uuid is not None:
        stmt_round = (
            select(ReviewRound)
            .where(
                ReviewRound.task_id == task_uuid,
                ReviewRound.round_number == review_round,
            )
            .order_by(ReviewRound.created_at.desc())
            .limit(1)
        )
        round_res = await db.execute(stmt_round)
        round_row = round_res.scalars().first()

        if round_row is None:
            fallback_stmt = (
                select(ReviewRound)
                .where(ReviewRound.task_id == task_uuid)
                .order_by(ReviewRound.round_number.desc())
                .limit(1)
            )
            fallback_res = await db.execute(fallback_stmt)
            round_row = fallback_res.scalars().first()

        if round_row is not None and isinstance(round_row.results, dict):
            latest_round_results = round_row.results

    skill = get_skill_registry().get("rewrite_polish")

    for section_id in section_ids:
        try:
            section_uuid = uuid.UUID(section_id)
        except Exception:
            continue

        stmt_ver = (
            select(SectionVersion)
            .where(SectionVersion.section_id == section_uuid)
            .order_by(SectionVersion.version_number.desc())
            .limit(1)
        )
        ver_res = await db.execute(stmt_ver)
        latest_ver = ver_res.scalars().first()
        if latest_ver is None:
            continue

        section_issues = _extract_section_issues_from_round(
            latest_round_results, section_id
        )
        if not section_issues:
            continue

        ctx = SkillContext(
            task_id=task_id,
            section_id=section_id,
            llm_client=llm_client,
            db_session=db,
            input_data={
                "current_content": latest_ver.content,
                "section_content": latest_ver.content,
                "issues": section_issues,
            },
        )
        result = await skill.execute(ctx)

        rewritten_content = (
            result.output.get("rewritten_content") if result.success else None
        )
        if not rewritten_content:
            continue

        try:
            new_version = SectionVersion(
                id=uuid.uuid4(),
                section_id=section_uuid,
                version_number=int(latest_ver.version_number) + 1,
                content=str(rewritten_content),
                change_source="revision",
                change_summary=f"auto revision round {review_round}",
            )
            db.add(new_version)
            await db.flush()
        except Exception:
            # Best effort update: revision failures should not crash node.
            pass

    await _publish(
        task_id,
        f"revision_round_{review_round}_complete",
        "revising",
        70,
        f"修订轮次 {review_round} 完成",
        data={"review_round": review_round, "revised_sections": len(section_ids)},
    )
    return {
        "current_phase": "revising",
        "progress_pct": 70,
        "progress_message": "章节修订完成",
    }


def make_parse_node(db: AsyncSession, llm_client: Any):
    async def _node(state: DocumentState) -> dict[str, object]:
        return await parse_node(state, db, llm_client)

    return _node


def make_extract_node(db: AsyncSession, llm_client: Any):
    async def _node(state: DocumentState) -> dict[str, object]:
        return await extract_requirements_node(state, db, llm_client)

    return _node


def make_outline_node(db: AsyncSession, llm_client: Any):
    async def _node(state: DocumentState) -> dict[str, object]:
        return await plan_outline_node(state, db, llm_client)

    return _node


def make_generate_node(db: AsyncSession, llm_client: Any):
    async def _node(state: DocumentState) -> dict[str, object]:
        return await generate_sections_node(state, db, llm_client)

    return _node


def make_reviews_node(db: AsyncSession, llm_client: Any):
    async def _node(state: DocumentState) -> dict[str, object]:
        return await run_reviews_node(state, db, llm_client)

    return _node


def make_revise_node(db: AsyncSession, llm_client: Any):
    async def _node(state: DocumentState) -> dict[str, object]:
        return await revise_sections_node(state, db, llm_client)

    return _node
