"""BaseReviewer — extends BaseSkill with reviewer-specific prompt/parse logic."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData


if TYPE_CHECKING:
    from skills.base import BaseSkill, SkillContext, SkillResult
else:
    try:
        from skills.base import BaseSkill, SkillContext, SkillResult
    except ImportError:
        class BaseSkill(ABC):
            """Fallback BaseSkill."""

        SkillContext = Any
        SkillResult = Any


class BaseReviewer(BaseSkill, ABC):
    """Base class for all 8 document reviewers. Extends BaseSkill."""

    reviewer_name: str = ""
    review_criteria: str = ""

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute review via SkillContext. Extracts sections and config from input_data."""
        sections_data = cast(
            list[dict[str, Any]], context.input_data.get("sections", [])
        )
        config_data = cast(dict[str, Any], context.input_data.get("config", {}))

        sections = [SectionData(**s) for s in sections_data]
        config = ReviewConfig(**config_data) if config_data else ReviewConfig()

        result = await self.review(
            sections=sections,
            config=config,
            llm_client=context.llm_client,
        )

        return SkillResult(
            success=True,
            output=result.model_dump(),
            tokens_used=0,  # LLM client tracks tokens internally
        )

    @abstractmethod
    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Perform the review. Must be implemented by each concrete reviewer."""
        ...

    def _build_prompt(
        self,
        sections: list[SectionData],
        criteria: str,
        rules: list[dict[str, Any]] | None = None,
        extra_criteria: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Build LLM messages for review. Single prompt → structured output (G9)."""
        sections_text = "\n\n".join(
            f"## Section {s.order_index + 1}: {s.title}\n{s.content}" for s in sections
        )
        rules_text = ""
        if rules:
            rules_text = "\n\nApplicable rules:\n" + "\n".join(
                f"- {r.get('name', '')}: {r.get('description', '')}" for r in rules
            )

        extra_text = ""
        if extra_criteria:
            extra_text = "\n\nAdditional review criteria specified by user:\n" + "\n".join(
                f"- {c}" for c in extra_criteria
            )

        system_prompt = (
            f"You are a specialized document reviewer. Your review criteria: {criteria}"
            f"{extra_text}\n"
            "Return a JSON object with this exact structure:\n"
            '{"status": "pass"|"fail"|"warning", "score": 0-100, "summary": "...", '
            '"issues": [{"severity": "critical"|"major"|"minor"|"info", "category": "...", '
            '"section_id": null, "location_excerpt": "...", "description": "...", '
            '"suggestion": "...", "requires_human": false}]}'
        )

        user_prompt = (
            f"Please review the following document sections:{rules_text}\n\n"
            f"{sections_text}\n\n"
            "Return your review as JSON."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _parse_response(self, llm_output: str) -> ReviewResult:
        """Parse LLM JSON output into ReviewResult. Single pass — no multi-turn (G9)."""
        try:
            data = json.loads(llm_output)
        except json.JSONDecodeError:
            # Graceful degradation — return fail with note
            return ReviewResult(
                reviewer_name=self.reviewer_name,
                status="fail",
                summary=f"Reviewer output parsing failed: {llm_output[:100]}",
                score=0,
                issues=[
                    ReviewIssue(
                        severity="critical",
                        category="system",
                        description="Reviewer failed to produce valid JSON output",
                        suggestion="Retry review",
                    )
                ],
            )

        issues = [ReviewIssue(**i) for i in data.get("issues", [])]
        return ReviewResult(
            reviewer_name=self.reviewer_name,
            status=data.get("status", "fail"),
            score=int(data.get("score", 0)),
            summary=data.get("summary", ""),
            issues=issues,
            metadata=data.get("metadata", {}),
        )
