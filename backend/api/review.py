"""FastAPI router for review execution and aggregated results."""
# pyright: reportCallInDefaultInitializer=false

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.review_aggregation import AggregatedReview
from services.review_service import ReviewService

router = APIRouter(prefix="/tasks", tags=["review"])

_service = ReviewService()


def _resolve_llm_client() -> object | None:
    """Resolve LLM client lazily to keep import-time side effects minimal in tests."""
    try:
        from core.llm import get_llm_client

        return get_llm_client()
    except ModuleNotFoundError:
        return None


class RunReviewRequest(BaseModel):
    """Body for starting a review round."""

    document_id: str
    review_round: int = Field(default=1, ge=1)


@router.post("/{task_id}/reviews/run", response_model=AggregatedReview)
async def run_review_round(
    task_id: str,
    body: RunReviewRequest,
    db: AsyncSession = Depends(get_db),
) -> AggregatedReview:
    """Run all 8 reviewers for one task/document review round."""
    return await _service.run_all_reviews(
        task_id=task_id,
        document_id=body.document_id,
        review_round=body.review_round,
        db=db,
        llm_client=_resolve_llm_client(),
    )


@router.get("/{task_id}/reviews/latest", response_model=AggregatedReview)
async def get_latest_review(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> AggregatedReview:
    """Get latest aggregated review for a task."""
    aggregated = await _service.get_latest_review(db, task_id)
    if aggregated is None:
        raise HTTPException(status_code=404, detail="No reviews found")
    return aggregated


@router.get("/{task_id}/reviews/{review_round}", response_model=AggregatedReview)
async def get_review_round(
    task_id: str,
    review_round: int,
    db: AsyncSession = Depends(get_db),
) -> AggregatedReview:
    """Get aggregated review for a specific review round."""
    aggregated = await _service.get_review_round(db, task_id, review_round)
    if aggregated is None:
        raise HTTPException(status_code=404, detail="Review round not found")
    return aggregated
