"""StructureReviewer — checks document structural completeness."""

from __future__ import annotations

from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData
from skills.registry import get_skill_registry


class StructureReviewer(BaseReviewer):
    """Reviews document structure: hierarchy, required sections, ordering, heading levels, balance."""

    name: str = "structure"
    reviewer_name: str = "structure"
    description: str = "Check document structural completeness"
    review_criteria: str = (
        "检查文档结构：章节层级是否正确、必需章节是否齐全、"
        "章节顺序是否合理、标题层级是否一致、各章节篇幅是否均衡"
    )

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Perform structure review via single LLM prompt (G9)."""
        messages = self._build_prompt(sections, self.review_criteria, config.rules)

        try:
            llm_output: dict[str, Any] = await llm_client.complete_json(
                messages=messages,
            )
        except (ValueError, RuntimeError):
            # LLM returned invalid JSON or failed — graceful fallback
            return ReviewResult(
                reviewer_name=self.reviewer_name,
                status="fail",
                summary="Structure review failed: LLM returned invalid response",
                score=0,
                issues=[
                    ReviewIssue(
                        severity="critical",
                        category="system",
                        description="Structure reviewer failed to get valid LLM response",
                        suggestion="Retry review",
                    )
                ],
            )

        # LLMClient.complete_json returns a parsed dict already
        issues = [
            ReviewIssue(**issue_data) for issue_data in llm_output.get("issues", [])
        ]
        return ReviewResult(
            reviewer_name=self.reviewer_name,
            status=llm_output.get("status", "fail"),
            score=int(llm_output.get("score", 0)),
            summary=llm_output.get("summary", ""),
            issues=issues,
            metadata=llm_output.get("metadata", {}),
        )


# Register at module load
get_skill_registry().register(StructureReviewer())
