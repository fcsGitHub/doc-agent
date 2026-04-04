"""Comparison Skill — compare section content against requirements or reference documents."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportImplicitOverride=false, reportUnannotatedClassAttribute=false

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from skills.base import BaseSkill, SkillContext, SkillResult


# Load prompt template at import time
_PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "comparison.txt"
_PROMPT_RAW = _PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

# Split into system and user parts (template uses SYSTEM: / USER: markers)
_parts = _PROMPT_RAW.split("USER:")
_SYSTEM_PROMPT = _parts[0].replace("SYSTEM:", "").strip()
_USER_TEMPLATE = _parts[1].strip() if len(_parts) > 1 else ""


class ComparisonSkill(BaseSkill):
    """Compare section content against requirements or reference documents via LLM."""

    name = "comparison"
    description = "Compare section content against requirements or reference documents"

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute comparison analysis.

        Input (from context.input_data):
            section_content (str): The section content to compare.
            reference_content (str): The reference/requirements content.
            comparison_type (str): "requirements_match" or "reference_alignment".

        Returns:
            SkillResult with output containing:
                coverage_score (int): 0-100 coverage/alignment score.
                missing_items (list[str]): Uncovered requirements or misaligned points.
                alignment_notes (str): Overall alignment summary.
                suggestions (list[str]): Improvement suggestions.
        """
        start = time.time()
        try:
            data = context.input_data or {}
            section_content: str = str(data.get("section_content", ""))
            reference_content: str = str(data.get("reference_content", ""))
            comparison_type: str = str(
                data.get("comparison_type", "requirements_match")
            )

            # Build prompt from template
            user_prompt = _USER_TEMPLATE.format(
                section_content=section_content,
                reference_content=reference_content,
                comparison_type=comparison_type,
            )

            # Call LLM with JSON output mode
            result: dict[str, Any] = await context.llm_client.complete_json(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )

            # Normalise output fields with safe defaults
            output: dict[str, Any] = {
                "coverage_score": int(result.get("coverage_score", 0)),
                "missing_items": list(result.get("missing_items", [])),
                "alignment_notes": str(result.get("alignment_notes", "")),
                "suggestions": list(result.get("suggestions", [])),
            }

            return SkillResult(
                success=True,
                output=output,
                execution_time_ms=int((time.time() - start) * 1000),
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                error=str(exc),
                output={},
                execution_time_ms=int((time.time() - start) * 1000),
            )


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from skills.registry import get_skill_registry  # noqa: E402

get_skill_registry().register(ComparisonSkill())
