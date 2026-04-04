"""Section Writing Skill — LLM-driven section content generation."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportImplicitOverride=false, reportUnannotatedClassAttribute=false

from __future__ import annotations

import time
from dataclasses import dataclass, field

from skills.base import BaseSkill, SkillContext, SkillResult


@dataclass
class SectionSummary:
    """Brief preceding section summary."""

    title: str
    summary: str


@dataclass
class SectionContext:
    """Writing context for section generation."""

    requirements: list[str]
    preceding_sections: list[SectionSummary]
    style_guide: str | None = None
    knowledge_excerpts: list[str] = field(default_factory=list)


@dataclass
class WriteInput:
    """Input payload for section writing."""

    task_id: str
    section_id: str
    section_title: str
    section_description: str
    target_word_count: int
    context: SectionContext


@dataclass
class WriteOutput:
    """Output payload from section writing."""

    content: str
    word_count: int
    references_used: list[str]


SYSTEM_PROMPT = """\
你是一个专业的文档撰写专家。根据以下章节信息和上下文，撰写该章节的详细内容。
要求：
1. 内容专业、流畅，符合文档规范
2. 字数接近目标字数
3. 与前面章节保持逻辑连贯
4. 严格围绕章节主题展开
请直接输出章节正文内容，不要包含章节标题。\
"""


class SectionWritingSkill(BaseSkill):
    """Write section content using an LLM, then persist section version if possible."""

    name = "section_writing"
    description = "Write section content using LLM"

    async def _try_retrieve_knowledge(
        self, context: SkillContext, input_data: WriteInput
    ) -> list[str]:
        """Optionally call retrieval skill to fetch RAG knowledge excerpts.

        Returns a list of excerpt strings to inject into the prompt.
        On any failure or empty results, returns an empty list (never fails).
        """
        if context.db_session is None:
            return []

        try:
            from skills.registry import get_skill_registry as _get_registry

            registry = _get_registry()
            if not registry.is_registered("retrieve_knowledge"):
                return []

            retrieval_skill = registry.get("retrieve_knowledge")
            query = (
                f"{input_data.section_title} {input_data.section_description}".strip()
            )
            if not query:
                return []

            retrieval_context = SkillContext(
                task_id=input_data.task_id,
                section_id=input_data.section_id,
                input_data={"query": query, "top_k": 5},
                llm_client=context.llm_client,
                db_session=context.db_session,
            )
            retrieval_result = await retrieval_skill.execute(retrieval_context)

            if retrieval_result.success and retrieval_result.output.get("chunks"):
                formatted = retrieval_result.output.get("formatted_context", "")
                if formatted and formatted != "暂无相关知识库内容":
                    return [formatted]
        except Exception:
            pass  # Retrieval failure must not block section generation

        return []

    async def execute(self, context: SkillContext) -> SkillResult:
        """Generate section content and persist a SectionVersion best-effort."""
        start = time.time()
        try:
            input_data = self._to_write_input(context)

            # Optionally enrich with RAG knowledge if no excerpts already provided
            if not input_data.context.knowledge_excerpts:
                rag_excerpts = await self._try_retrieve_knowledge(context, input_data)
                if rag_excerpts:
                    input_data.context.knowledge_excerpts = rag_excerpts

            user_prompt = self._build_prompt(input_data)

            llm_result = await context.llm_client.complete(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )

            content = llm_result.content
            word_count = len(content.split())

            if context.db_session is not None:
                try:
                    from models.section import SectionVersion
                    import uuid as _uuid

                    sv = SectionVersion(
                        id=_uuid.uuid4(),
                        section_id=_uuid.UUID(input_data.section_id),
                        version_number=1,
                        content=content,
                        word_count=word_count,
                        change_source="generation",
                        change_summary=f"初始生成 — {input_data.section_title}",
                    )
                    context.db_session.add(sv)
                    await context.db_session.flush()
                except Exception:
                    pass

            return SkillResult(
                success=True,
                output={
                    "content": content,
                    "word_count": word_count,
                    "references_used": [],
                },
                tokens_used=getattr(llm_result, "tokens_used", 0) or 0,
                execution_time_ms=int((time.time() - start) * 1000),
            )
        except Exception as exc:
            return SkillResult(
                success=True,
                output={"content": "", "word_count": 0, "references_used": []},
                error=str(exc),
                execution_time_ms=int((time.time() - start) * 1000),
            )

    def _to_write_input(self, context: SkillContext) -> WriteInput:
        """Normalize SkillContext.input_data into WriteInput dataclass."""
        data = context.input_data or {}
        raw_ctx = data.get("context") or {}

        raw_preceding = raw_ctx.get("preceding_sections") or []
        preceding_sections = [
            SectionSummary(
                title=str(sec.get("title", "")),
                summary=str(sec.get("summary", "")),
            )
            for sec in raw_preceding
            if isinstance(sec, dict)
        ]

        section_context = SectionContext(
            requirements=[str(r) for r in (raw_ctx.get("requirements") or [])],
            preceding_sections=preceding_sections,
            style_guide=raw_ctx.get("style_guide"),
            knowledge_excerpts=[
                str(x) for x in (raw_ctx.get("knowledge_excerpts") or [])
            ],
        )

        return WriteInput(
            task_id=str(data.get("task_id", context.task_id)),
            section_id=str(data.get("section_id", context.section_id or "")),
            section_title=str(data.get("section_title", "")),
            section_description=str(data.get("section_description", "")),
            target_word_count=int(data.get("target_word_count", 500)),
            context=section_context,
        )

    def _build_prompt(self, input_data: WriteInput) -> str:
        """Build user prompt from section metadata and writing context."""
        lines = [
            f"章节标题：{input_data.section_title}",
            f"章节描述：{input_data.section_description}",
            f"目标字数：{input_data.target_word_count}字",
            "",
        ]
        if input_data.context.requirements:
            lines.append("文档需求：")
            for req in input_data.context.requirements:
                lines.append(f"- {req}")
            lines.append("")
        if input_data.context.preceding_sections:
            lines.append("前序章节摘要：")
            for sec in input_data.context.preceding_sections:
                lines.append(f"- {sec.title}: {sec.summary}")
            lines.append("")
        if input_data.context.style_guide:
            lines.append(f"写作风格要求：{input_data.context.style_guide}")
            lines.append("")
        if input_data.context.knowledge_excerpts:
            lines.append("参考资料：")
            for excerpt in input_data.context.knowledge_excerpts[:3]:
                lines.append(f"- {excerpt}")
            lines.append("")
        lines.append("请撰写该章节内容：")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from skills.registry import get_skill_registry  # noqa: E402

get_skill_registry().register(SectionWritingSkill())
