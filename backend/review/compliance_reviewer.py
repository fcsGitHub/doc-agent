"""ComplianceReviewer — checks format rules and hard constraints."""

from __future__ import annotations

import json
from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData
from skills.registry import get_skill_registry


class ComplianceReviewer(BaseReviewer):
    """Checks format rules, mandatory fields, naming, numbering, labeling, terminology."""

    name: str = "compliance"
    reviewer_name: str = "compliance"
    description: str = "Check format rule compliance: numbering, labeling, terminology, mandatory fields"
    review_criteria: str = (
        "检查合规性：格式规则是否遵守、必填字段是否齐全、"
        "编号格式是否正确、表格图片是否标注、术语是否与规则库一致"
    )

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Run compliance review via single LLM call (G9)."""
        messages = self._build_compliance_prompt(sections, config)

        try:
            llm_output = await llm_client.complete_json(messages=messages)
        except Exception as exc:
            # Graceful fallback on LLM failure
            return ReviewResult(
                reviewer_name=self.reviewer_name,
                status="fail",
                summary=f"Compliance review LLM call failed: {exc}",
                score=0,
                issues=[
                    ReviewIssue(
                        severity="critical",
                        category="compliance",
                        description=f"LLM call failed: {exc}",
                        suggestion="Retry compliance review",
                    )
                ],
            )

        # complete_json returns dict; _parse_response expects str
        if isinstance(llm_output, dict):
            return self._parse_response(json.dumps(llm_output))
        return self._parse_response(str(llm_output))

    def _build_compliance_prompt(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
    ) -> list[dict[str, str]]:
        """Build compliance-specific prompt. Returns [system, user] messages (G9)."""
        rules = config.rules if config.rules else None

        # Use base _build_prompt with compliance criteria
        base_messages = self._build_prompt(sections, self.review_criteria, rules)

        # Enhance system prompt with compliance-specific instructions
        system_content = base_messages[0]["content"]
        compliance_addendum = (
            "\n\nFocus ONLY on objective rule violations. Do NOT assess subjective quality.\n"
            "Check categories:\n"
            "1. Format rule violations\n"
            "2. Mandatory field presence\n"
            "3. Naming conventions\n"
            "4. Numbering format correctness (e.g. Table 1, Figure 1)\n"
            "5. Table and figure labeling\n"
            "6. Terminology consistency with rules\n"
            'Every issue must have category="compliance".'
        )

        if not rules:
            compliance_addendum += (
                "\n\nNo specific rules provided. Apply generic document compliance checks "
                "for numbering, labeling, and formatting."
            )

        base_messages[0]["content"] = system_content + compliance_addendum
        return base_messages


# Register at module load
get_skill_registry().register(ComplianceReviewer())
