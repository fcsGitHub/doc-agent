"""StyleReviewer — checks writing style and tone consistency."""

from __future__ import annotations

from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData


class StyleReviewer(BaseReviewer):
    """Reviewer that checks writing style, tone, and formality consistency."""

    name: str = "style"
    reviewer_name: str = "style"
    description: str = "Checks writing style: formality, perspective, tone, sentence variety, jargon, paragraph length"

    def _build_prompt(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
    ) -> list[dict[str, str]]:
        """Build [system, user] messages for style review. Single prompt (G9)."""
        sections_text = "\n\n".join(
            f"## Section {s.order_index + 1}: {s.title}\n{s.content}" for s in sections
        )

        criteria = (
            "检查文风：正式程度是否适当、人称视角是否一致、"
            "语气是否统一、句式是否多变、行话是否过多、段落长度是否合理"
        )

        style_guide_text = ""
        if config.style_guide:
            style_guide_text = f"\n\nStyle guide to follow:\n{config.style_guide}"

        system_prompt = (
            f"You are a specialized document reviewer. Your review criteria: {criteria}"
            f"{style_guide_text}\n"
            "Return a JSON object with this exact structure:\n"
            '{"status": "pass"|"fail"|"warning", "score": 0-100, "summary": "...", '
            '"issues": [{"severity": "critical"|"major"|"minor"|"info", "category": "style", '
            '"section_id": null, "location_excerpt": "...", "description": "...", '
            '"suggestion": "...", "requires_human": false}]}'
        )

        user_prompt = (
            f"Please review the following document sections for style consistency:\n\n"
            f"{sections_text}\n\n"
            "Return your review as JSON."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Perform style review via single LLM call (G9)."""
        if not sections:
            return ReviewResult(
                reviewer_name=self.reviewer_name,
                status="pass",
                summary="No sections to review.",
                score=100,
                issues=[],
            )

        messages = self._build_prompt(sections, config)
        self.llm_client = llm_client

        try:
            result = await self.llm_client.complete_json(messages=messages)
        except Exception as exc:
            return ReviewResult(
                reviewer_name=self.reviewer_name,
                status="fail",
                summary=f"Style review LLM call failed: {exc}",
                score=0,
                issues=[
                    ReviewIssue(
                        severity="critical",
                        category="style",
                        description=f"LLM call failed: {exc}",
                        suggestion="Retry the review",
                    )
                ],
            )

        return self._parse_response_dict(result)

    def _parse_response_dict(self, data: dict[str, Any]) -> ReviewResult:
        """Parse LLM dict output into ReviewResult."""
        issues = [ReviewIssue(**i) for i in data.get("issues", [])]
        return ReviewResult(
            reviewer_name=self.reviewer_name,
            status=data.get("status", "fail"),
            score=int(data.get("score", 0)),
            summary=data.get("summary", ""),
            issues=issues,
            metadata=data.get("metadata", {}),
        )


# Register in skill registry at module load
from skills.registry import get_skill_registry  # noqa: E402

get_skill_registry().register(StyleReviewer())
