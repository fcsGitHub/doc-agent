"""Outline Planning Skill — LLM-driven hierarchical document outline generation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from skills.base import BaseSkill, SkillContext, SkillResult


@dataclass
class OutlineSection:
    """A single section in the document outline."""

    title: str
    level: int
    description: str
    target_word_count: int
    depends_on: list[str] = field(default_factory=list)
    children: list["OutlineSection"] = field(default_factory=list)


@dataclass
class OutlineInput:
    """Input specification for outline planning."""

    task_id: str
    requirements: list[dict[str, Any]]
    doc_type: str
    template_schema: dict[str, Any] | None = None


@dataclass
class OutlineOutput:
    """Output from outline planning."""

    sections: list[OutlineSection] = field(default_factory=list)


SYSTEM_PROMPT = """\
你是一个文档规划专家。请根据以下需求生成文档大纲，以JSON格式返回。

JSON格式如下：
{
  "sections": [
    {
      "title": "章节标题",
      "level": 1,
      "description": "章节描述",
      "target_word_count": 500,
      "depends_on": [],
      "children": [
        {
          "title": "子章节标题",
          "level": 2,
          "description": "子章节描述",
          "target_word_count": 300,
          "depends_on": [],
          "children": []
        }
      ]
    }
  ]
}

如果提供了模板结构，请确保大纲包含所有必要章节。\
"""


def _parse_section(raw: dict[str, Any]) -> OutlineSection:
    """Parse a raw dict into an OutlineSection, handling nested children."""
    raw_children = raw.get("children", [])
    if not isinstance(raw_children, list):
        raw_children = []

    children = [_parse_section(c) for c in raw_children if isinstance(c, dict)]

    raw_depends = raw.get("depends_on", [])
    if not isinstance(raw_depends, list):
        raw_depends = []

    return OutlineSection(
        title=raw.get("title", ""),
        level=raw.get("level", 1),
        description=raw.get("description", ""),
        target_word_count=raw.get("target_word_count", 500),
        depends_on=[str(d) for d in raw_depends],
        children=children,
    )


def _parse_outline(data: dict[str, Any]) -> list[OutlineSection]:
    """Parse LLM JSON response into list[OutlineSection]. Handles nested children."""
    raw_sections = data.get("sections", [])
    if not isinstance(raw_sections, list):
        return []
    return [_parse_section(s) for s in raw_sections if isinstance(s, dict)]


def _serialize_section(section: OutlineSection) -> dict[str, Any]:
    """Recursively serialize an OutlineSection to a JSON-compatible dict."""
    return {
        "title": section.title,
        "level": section.level,
        "description": section.description,
        "target_word_count": section.target_word_count,
        "depends_on": section.depends_on,
        "children": [_serialize_section(c) for c in section.children],
    }


def _sections_to_flat_dicts(
    sections: list[OutlineSection],
    parent_title: str | None = None,
) -> list[dict[str, Any]]:
    """Flatten hierarchical sections to ordered list with parent info for DB insert."""
    result: list[dict[str, Any]] = []
    for section in sections:
        result.append(
            {
                "title": section.title,
                "level": section.level,
                "description": section.description,
                "target_word_count": section.target_word_count,
                "parent_title": parent_title,
            }
        )
        if section.children:
            result.extend(
                _sections_to_flat_dicts(section.children, parent_title=section.title)
            )
    return result


class OutlinePlanningSkill(BaseSkill):
    """Generate hierarchical document outline from requirements using LLM."""

    name = "outline_planning"
    description = "Generate hierarchical document outline from requirements using LLM"
    prerequisites: list[str] = []

    SYSTEM_PROMPT: str = SYSTEM_PROMPT

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute outline planning via single LLM call."""
        start_ms = int(time.time() * 1000)
        try:
            input_data = context.input_data
            requirements: list[dict[str, Any]] = input_data.get("requirements", [])
            doc_type: str = input_data.get("doc_type", "report")
            template_schema: dict[str, Any] | None = input_data.get(
                "template_schema", None
            )

            # Build user content
            parts: list[str] = [f"文档类型: {doc_type}"]

            if requirements:
                req_text = "\n".join(
                    f"- {r.get('description', r.get('id', ''))}" for r in requirements
                )
                parts.append(f"需求列表:\n{req_text}")

            if template_schema:
                required_sections = template_schema.get("required_sections", [])
                if required_sections:
                    parts.append(f"模板要求的章节: {', '.join(required_sections)}")

            user_content = "\n\n".join(parts)

            result = await context.llm_client.complete_json(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ]
            )

            sections = _parse_outline(result)

            # DB persistence (optional)
            if context.db_session is not None:
                await self._persist_sections(context, sections)

            return SkillResult(
                success=True,
                output={
                    "sections": [_serialize_section(s) for s in sections],
                },
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )
        except Exception as exc:
            return SkillResult(
                success=True,
                output={"sections": []},
                error=str(exc),
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

    async def _persist_sections(
        self,
        context: SkillContext,
        sections: list[OutlineSection],
    ) -> None:
        """Flatten and persist sections to the database."""
        from models.section import Section

        flat = _sections_to_flat_dicts(sections)
        for i, entry in enumerate(flat):
            section_obj = Section(
                task_id=context.task_id,
                title=entry["title"],
                level=entry["level"],
                description=entry.get("description"),
                target_word_count=entry.get("target_word_count", 500),
                order_index=i,
                parent_id=None,
                status="draft",
            )
            context.db_session.add(section_obj)
        await context.db_session.flush()


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from skills.registry import get_skill_registry  # noqa: E402

get_skill_registry().register(OutlinePlanningSkill())
