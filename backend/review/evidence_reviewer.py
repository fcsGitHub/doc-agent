"""EvidenceReviewer — checks claims are backed by evidence."""

from __future__ import annotations

from typing import Any

from review.base import BaseReviewer
from review.schemas import ReviewConfig, ReviewIssue, ReviewResult, SectionData
from skills.registry import get_skill_registry


class EvidenceReviewer(BaseReviewer):
    """Reviews evidence quality: unsupported claims, missing citations, vague references, claim-evidence alignment."""

    name: str = "evidence"
    reviewer_name: str = "evidence"
    description: str = "Check claims are backed by evidence"
    review_criteria: str = (
        "检查证据支撑：结论是否有数据/证据支持、引用是否明确、"
        "是否存在空泛表述、论据与论点是否对应"
    )

    async def review(
        self,
        sections: list[SectionData],
        config: ReviewConfig,
        llm_client: Any = None,
    ) -> ReviewResult:
        """Perform evidence review via single LLM prompt (G9)."""
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
                summary="Evidence review failed: LLM returned invalid response",
                score=0,
                issues=[
                    ReviewIssue(
                        severity="critical",
                        category="system",
                        description="Evidence reviewer failed to get valid LLM response",
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
get_skill_registry().register(EvidenceReviewer())
