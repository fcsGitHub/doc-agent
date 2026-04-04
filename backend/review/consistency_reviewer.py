"""ConsistencyReviewer — checks cross-section consistency across the entire document."""

from __future__ import annotations

import json
from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewResult, SectionData
from skills.registry import get_skill_registry


class ConsistencyReviewer(BaseReviewer):
    """Reviews ALL sections together to catch cross-section consistency issues.

    Checks: term usage consistency, number consistency, date/timeline consistency,
    unit consistency, name/abbreviation consistency, cross-reference accuracy.
    """

    name: str = "consistency"
    reviewer_name: str = "consistency"
    description: str = "Cross-section consistency reviewer"
    review_criteria: str = (
        "检查一致性：术语使用是否前后一致、数据/数字是否吻合、"
        "日期/时间线是否一致、单位是否统一、名称/缩写是否一致、"
        "交叉引用是否准确"
    )

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Review all sections in a single prompt for cross-section consistency."""
        messages = self._build_consistency_prompt(sections, config)
        raw = await llm_client.complete_json(messages=messages)

        if isinstance(raw, str):
            return self._parse_response(raw)

        # If llm_client already returned a dict, wrap it
        if isinstance(raw, dict):
            return self._parse_response(json.dumps(raw))

        return self._parse_response(str(raw))

    def _build_consistency_prompt(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
    ) -> list[dict[str, str]]:
        """Build a single prompt with ALL sections for cross-section consistency check."""
        sections_text = "\n\n".join(
            f"## Section {s.order_index + 1} (id={s.section_id}): {s.title}\n{s.content}"
            for s in sections
        )

        rules_text = ""
        if config.rules:
            rules_text = "\n\nApplicable rules:\n" + "\n".join(
                f"- {r.get('name', '')}: {r.get('description', '')}"
                for r in config.rules
            )

        system_prompt = (
            "You are a specialized document consistency reviewer.\n"
            f"Your review criteria: {self.review_criteria}\n\n"
            "You MUST review ALL sections TOGETHER to find cross-section inconsistencies.\n"
            "For each issue found, reference the specific section(s) involved.\n"
            "If an inconsistency spans two sections, mention both section IDs in the description.\n\n"
            "Return a JSON object with this exact structure:\n"
            '{"status": "pass"|"fail"|"warning", "score": 0-100, "summary": "...", '
            '"issues": [{"severity": "critical"|"major"|"minor"|"info", '
            '"category": "consistency", '
            '"section_id": "...", "location_excerpt": "...", "description": "...", '
            '"suggestion": "...", "requires_human": false}]}\n\n'
            "If no issues are found, return status=pass with an empty issues array."
        )

        user_prompt = (
            f"Please review the following document sections for cross-section consistency:{rules_text}\n\n"
            f"{sections_text}\n\n"
            "Return your consistency review as JSON."
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]


# Register at module load
get_skill_registry().register(ConsistencyReviewer())
