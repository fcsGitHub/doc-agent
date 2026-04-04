"""CoverageReviewer — checks requirement coverage across document sections."""

from __future__ import annotations

import json
from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData
from skills.registry import get_skill_registry


class CoverageReviewer(BaseReviewer):
    """Reviewer that checks whether all requirements are covered in document sections.

    Verifies:
    - Each extracted requirement is addressed in at least one section
    - Scoring/evaluation criteria are covered
    - No orphan sections exist (sections not linked to any requirement)
    """

    name: str = "coverage"
    reviewer_name: str = "coverage"
    description: str = "Checks requirement coverage in document sections"
    review_criteria: str = (
        "检查覆盖度：每个需求点是否都在文档中有所体现、"
        "评分项/考核标准是否全部覆盖、是否有孤立章节无法追溯到需求"
    )

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Perform coverage review using single LLM prompt (G9)."""
        messages = self._build_prompt(sections, config)

        if llm_client is None:
            return ReviewResult(
                reviewer_name=self.reviewer_name,
                status="fail",
                summary="No LLM client provided",
                score=0,
                issues=[
                    ReviewIssue(
                        severity="critical",
                        category="coverage",
                        description="LLM client is required for coverage review",
                        suggestion="Provide an LLM client via SkillContext",
                    )
                ],
            )

        llm_output = await llm_client.complete_json(messages=messages)

        if isinstance(llm_output, dict):
            llm_text = json.dumps(llm_output)
        else:
            llm_text = str(llm_output)

        return self._parse_response(llm_text)

    def _build_prompt(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
    ) -> list[dict[str, str]]:
        """Build [system, user] messages for coverage review.

        Includes requirements list if available in config input_data.
        Single prompt -- no multi-turn (G9).
        """
        # Extract requirements from config rules or input_data
        requirements = self._extract_requirements(config)

        sections_text = "\n\n".join(
            f"## Section {s.order_index + 1}: {s.title}\n{s.content}" for s in sections
        )

        system_prompt = (
            "You are a specialized document reviewer focused on requirement coverage analysis.\n"
            f"Your review criteria: {self.review_criteria}\n\n"
            "Return a JSON object with this exact structure:\n"
            '{"status": "pass"|"fail"|"warning", "score": 0-100, "summary": "...", '
            '"issues": [{"severity": "critical"|"major"|"minor"|"info", '
            '"category": "coverage", "section_id": null, '
            '"location_excerpt": "...", "description": "...", '
            '"suggestion": "...", "requires_human": false}]}'
        )

        if requirements:
            requirements_text = "\n".join(
                f"- REQ{i + 1}: {req}" for i, req in enumerate(requirements)
            )
            user_prompt = (
                f"Please review the following document for requirement coverage.\n\n"
                f"### Requirements to cover:\n{requirements_text}\n\n"
                f"### Document sections:\n{sections_text}\n\n"
                "For each requirement, check if it is addressed in at least one section. "
                "Also check for orphan sections that don't map to any requirement. "
                "Also verify that scoring/evaluation criteria are fully covered.\n"
                "Return your review as JSON."
            )
        else:
            # No requirements available -- run generic coverage check
            user_prompt = (
                "Please review the following document for general coverage completeness.\n\n"
                f"### Document sections:\n{sections_text}\n\n"
                "Check whether the document covers its topic comprehensively, "
                "whether any sections appear orphaned or disconnected from the main theme, "
                "and whether evaluation criteria (if any) are fully addressed.\n"
                "Return your review as JSON."
            )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _extract_requirements(self, config: ReviewConfig) -> list[str]:
        """Extract requirements list from config.

        Requirements may come from:
        1. config.rules with a 'requirements' key
        2. Directly in the rules list as requirement dicts
        """
        requirements: list[str] = []

        # Check rules for embedded requirements
        for rule in config.rules:
            if rule.get("type") == "requirement" and "text" in rule:
                requirements.append(rule["text"])
            elif "requirements" in rule:
                reqs = rule["requirements"]
                if isinstance(reqs, list):
                    requirements.extend(str(r) for r in reqs)

        return requirements


# Register at module load
_registry = get_skill_registry()
_registry.register(CoverageReviewer())
