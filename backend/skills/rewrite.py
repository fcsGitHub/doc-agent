"""Rewrite & Polish Skill — rewrites a section based on review issues."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportImplicitOverride=false, reportUnannotatedClassAttribute=false

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from skills.base import BaseSkill, SkillContext, SkillResult, load_prompt_parts


_SYSTEM_PROMPT, _USER_TEMPLATE = load_prompt_parts(
    Path(__file__).parent / "prompts" / "rewrite.txt"
)


def _format_issues_text(issues: list[dict[str, Any]]) -> str:
    """Format auto-fixable issues into a numbered list for the LLM prompt."""
    lines: list[str] = []
    for idx, issue in enumerate(issues, 1):
        severity = issue.get("severity", "unknown")
        description = issue.get("description", "")
        suggestion = issue.get("suggestion", "")
        lines.append(f"{idx}. [{severity}] {description}")
        if suggestion:
            lines.append(f"   建议修改：{suggestion}")
    return "\n".join(lines)


class RewriteSkill(BaseSkill):
    """Rewrite a section to address review issues (skipping human-required ones)."""

    name = "rewrite_polish"
    description = "Rewrite section content based on review issues"

    async def execute(self, context: SkillContext) -> SkillResult:
        """Rewrite section content addressing auto-fixable issues."""
        start = time.time()
        try:
            data = context.input_data or {}
            section_content: str = str(data.get("section_content", ""))
            issues: list[dict[str, Any]] = data.get("issues", [])

            auto_fixable = [i for i in issues if not i.get("requires_human", False)]
            human_required = [i for i in issues if i.get("requires_human", False)]

            issues_text = _format_issues_text(auto_fixable)
            user_prompt = _USER_TEMPLATE.format(
                section_content=section_content,
                issues_text=issues_text,
            )

            llm_result = await context.llm_client.complete(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )

            rewritten_content: str = llm_result.content

            return SkillResult(
                success=True,
                output={
                    "rewritten_content": rewritten_content,
                    "addressed_issues": len(auto_fixable),
                    "skipped_human_required": [
                        i["issue_id"] for i in human_required if "issue_id" in i
                    ],
                },
                tokens_used=getattr(llm_result, "tokens_used", 0) or 0,
                execution_time_ms=int((time.time() - start) * 1000),
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                error=str(exc),
                output={},
                execution_time_ms=int((time.time() - start) * 1000),
            )


from skills.registry import get_skill_registry  # noqa: E402

get_skill_registry().register(RewriteSkill())
