"""Requirement Extraction Skill — LLM-driven structured requirement extraction."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from skills.base import BaseSkill, SkillContext, SkillResult


@dataclass
class Requirement:
    """A single extracted requirement."""

    id: str  # e.g., "REQ-001"
    description: str
    category: str  # e.g., "functional", "technical", "compliance"
    priority: Literal["must", "should", "nice"]
    source_excerpt: str  # excerpt from parsed text implying this requirement


@dataclass
class ExtractInput:
    """Input specification for requirement extraction."""

    task_id: str
    parsed_text: str
    doc_type: str  # e.g., "report", "proposal", "specification"


@dataclass
class ExtractOutput:
    """Output from requirement extraction."""

    requirements: list[Requirement] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    key_terms: list[str] = field(default_factory=list)


SYSTEM_PROMPT = """\
你是一个文档分析专家。请从以下文档文本中提取结构化需求信息，以JSON格式返回。

JSON格式如下：
{
  "requirements": [
    {
      "id": "REQ-001",
      "description": "需求描述",
      "category": "functional|technical|compliance",
      "priority": "must|should|nice",
      "source_excerpt": "原文摘录"
    }
  ],
  "constraints": ["约束条件1", "约束条件2"],
  "key_terms": ["关键词1", "关键词2"]
}\
"""


def _parse_requirement(raw: dict[str, Any]) -> Requirement:
    """Parse a raw dict into a Requirement dataclass, with safe defaults."""
    priority = raw.get("priority", "should")
    if priority not in ("must", "should", "nice"):
        priority = "should"
    return Requirement(
        id=raw.get("id", "REQ-???"),
        description=raw.get("description", ""),
        category=raw.get("category", "functional"),
        priority=priority,
        source_excerpt=raw.get("source_excerpt", ""),
    )


def _parse_extract_output(data: dict[str, Any]) -> ExtractOutput:
    """Parse raw LLM JSON response into ExtractOutput. Handles missing keys gracefully."""
    raw_reqs = data.get("requirements", [])
    if not isinstance(raw_reqs, list):
        raw_reqs = []

    requirements = [_parse_requirement(r) for r in raw_reqs if isinstance(r, dict)]

    raw_constraints = data.get("constraints", [])
    constraints = raw_constraints if isinstance(raw_constraints, list) else []

    raw_key_terms = data.get("key_terms", [])
    key_terms = raw_key_terms if isinstance(raw_key_terms, list) else []

    return ExtractOutput(
        requirements=requirements,
        constraints=[str(c) for c in constraints],
        key_terms=[str(t) for t in key_terms],
    )


class RequirementExtractionSkill(BaseSkill):
    """Extract structured requirements from parsed document text using LLM."""

    name = "requirement_extraction"
    description = "Extract structured requirements from parsed document text using LLM"
    prerequisites: list[str] = []

    PROMPT_TEMPLATE: str = SYSTEM_PROMPT

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute requirement extraction via single LLM call."""
        start_ms = int(time.time() * 1000)
        try:
            input_data = context.input_data
            parsed_text: str = input_data.get("parsed_text", "")
            doc_type: str = input_data.get("doc_type", "report")

            user_content = f"文档类型: {doc_type}\n\n文档内容:\n{parsed_text}"

            result = await context.llm_client.complete_json(
                messages=[
                    {"role": "system", "content": self.PROMPT_TEMPLATE},
                    {"role": "user", "content": user_content},
                ]
            )

            output = _parse_extract_output(result)

            return SkillResult(
                success=True,
                output={
                    "requirements": [
                        {
                            "id": r.id,
                            "description": r.description,
                            "category": r.category,
                            "priority": r.priority,
                            "source_excerpt": r.source_excerpt,
                        }
                        for r in output.requirements
                    ],
                    "constraints": output.constraints,
                    "key_terms": output.key_terms,
                },
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )
        except Exception as exc:
            # Malformed LLM output or other errors — return empty but successful
            return SkillResult(
                success=True,
                output={
                    "requirements": [],
                    "constraints": [],
                    "key_terms": [],
                },
                error=str(exc),
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from skills.registry import get_skill_registry  # noqa: E402

get_skill_registry().register(RequirementExtractionSkill())
