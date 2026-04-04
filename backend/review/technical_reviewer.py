"""TechnicalReviewer — checks technical correctness of document content."""

from __future__ import annotations

from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData
from skills.registry import get_skill_registry

# Technical review criteria — used in prompt construction
_TECHNICAL_CRITERIA = (
    "检查技术正确性：论证逻辑是否完整、技术论述是否准确、"
    "方法论是否合理、计算是否正确、技术术语使用是否恰当"
)

_TECHNICAL_CHECKS = (
    "Checks to perform:\n"
    "1. 论证逻辑是否完整 — logical argument completeness\n"
    "2. 技术论述是否准确 — technical claims accuracy\n"
    "3. 方法论是否合理 — methodology soundness\n"
    "4. 计算是否正确 — calculation correctness\n"
    "5. 技术术语使用是否恰当 — technical terminology usage\n"
    "6. 规范引用是否有效 — specification references validity"
)


class TechnicalReviewer(BaseReviewer):
    """Reviewer that checks technical correctness: logical completeness,
    claim accuracy, methodology soundness, calculation correctness,
    terminology usage, and specification reference validity."""

    name: str = "technical"
    reviewer_name: str = "technical"
    description: str = "检查技术正确性：论证逻辑、技术论述、方法论、计算及术语"
    review_criteria: str = _TECHNICAL_CRITERIA

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Perform technical correctness review via single LLM prompt (G9)."""
        criteria = f"{self.review_criteria}\n\n{_TECHNICAL_CHECKS}"
        messages = self._build_prompt(sections, criteria, config.rules or None)

        try:
            data = await llm_client.complete_json(messages=messages)
        except (ValueError, RuntimeError):
            # Graceful fallback on invalid JSON or LLM failure
            return ReviewResult(
                reviewer_name=self.reviewer_name,
                status="fail",
                summary="Technical review failed: LLM returned invalid response",
                score=0,
                issues=[
                    ReviewIssue(
                        severity="critical",
                        category="technical",
                        description="LLM未能返回有效的JSON审核结果",
                        suggestion="请重试技术审核",
                    )
                ],
            )

        return self._build_review_result(data)

    def _build_review_result(self, data: dict[str, Any]) -> ReviewResult:
        """Convert LLM JSON dict into ReviewResult."""
        issues = [ReviewIssue(**issue_data) for issue_data in data.get("issues", [])]
        return ReviewResult(
            reviewer_name=self.reviewer_name,
            status=data.get("status", "fail"),
            score=int(data.get("score", 0)),
            summary=data.get("summary", ""),
            issues=issues,
            metadata=data.get("metadata", {}),
        )


# Register at module load
get_skill_registry().register(TechnicalReviewer())
