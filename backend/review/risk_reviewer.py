"""RiskReviewer — checks for risky content: sensitive terms, exaggerated claims, legal/compliance risks."""

from __future__ import annotations

import json
from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData
from skills.registry import get_skill_registry


class RiskReviewer(BaseReviewer):
    """Reviewer that flags risk-sensitive content requiring human review.

    Checks for: sensitive/confidential terms, exaggerated claims,
    unsubstantiated superlatives, absolute statements without qualification,
    potential legal/compliance risks, and data privacy concerns.

    All risk issues default to requires_human=True.
    """

    name: str = "risk"
    reviewer_name: str = "risk"
    description: str = "Review document for risk-sensitive content"
    review_criteria: str = (
        "检查风险：是否包含敏感/机密词汇、是否有夸大表述、"
        "是否有未限定的绝对化表述、是否有法律/合规风险、是否有数据隐私问题"
    )

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Perform risk review via single LLM call (G9)."""
        messages = self._build_prompt(sections, config)
        raw = await llm_client.complete_json(messages=messages)

        if isinstance(raw, str):
            raw = json.loads(raw)

        # Ensure all risk issues have requires_human=True
        issues: list[ReviewIssue] = []
        for issue_data in raw.get("issues", []):
            issue_data["requires_human"] = True
            issue_data["category"] = "risk"
            issues.append(ReviewIssue(**issue_data))

        return ReviewResult(
            reviewer_name=self.reviewer_name,
            status=raw.get("status", "fail"),
            score=int(raw.get("score", 0)),
            summary=raw.get("summary", ""),
            issues=issues,
            metadata=raw.get("metadata", {}),
        )

    def _build_prompt(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
    ) -> list[dict[str, str]]:
        """Build [system, user] messages for risk review. Single prompt (G9)."""
        sections_text = "\n\n".join(
            f"## Section {s.order_index + 1}: {s.title}\n{s.content}" for s in sections
        )

        rules_text = ""
        if config.rules:
            rules_text = "\n\nApplicable rules:\n" + "\n".join(
                f"- {r.get('name', '')}: {r.get('description', '')}"
                for r in config.rules
            )

        system_prompt = (
            "You are a specialized document risk reviewer.\n"
            f"Your review criteria: {self.review_criteria}\n"
            "检查风险：是否包含敏感/机密词汇、是否有夸大表述、"
            "是否有未限定的绝对化表述、是否有法律/合规风险、是否有数据隐私问题\n\n"
            "Return a JSON object with this exact structure:\n"
            '{"status": "pass"|"fail"|"warning", "score": 0-100, "summary": "...", '
            '"issues": [{"severity": "critical"|"major"|"minor"|"info", "category": "risk", '
            '"section_id": null, "location_excerpt": "...", "description": "...", '
            '"suggestion": "...", "requires_human": true}]}\n\n'
            "IMPORTANT: All risk issues MUST have requires_human=true."
        )

        user_prompt = (
            f"Please review the following document sections for risk content:{rules_text}\n\n"
            f"{sections_text}\n\n"
            "Return your review as JSON."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]


# Register at module load
get_skill_registry().register(RiskReviewer())
