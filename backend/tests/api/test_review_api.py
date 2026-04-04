"""API tests for review run + retrieval endpoints."""
# pyright: reportUnusedFunction=false

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from main import app
from models.review_aggregation import AggregatedReview
from review.schemas import ReviewResult


async def _override_get_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    yield db


@pytest.fixture(autouse=True)
def _override_db():
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _agg() -> AggregatedReview:
    return AggregatedReview.from_results(
        task_id=str(uuid.uuid4()),
        document_id=str(uuid.uuid4()),
        review_round=1,
        results=[
            ReviewResult(
                reviewer_name="structure",
                status="pass",
                score=95,
                summary="ok",
                issues=[],
            )
        ],
    )


class TestRunReviewAPI:
    @pytest.mark.asyncio
    async def test_post_run_review_200(self):
        aggregated = _agg()

        with (
            patch("api.review._service") as mock_service,
            patch("api.review._resolve_llm_client", return_value=AsyncMock()),
        ):
            mock_service.run_all_reviews = AsyncMock(return_value=aggregated)
            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{uuid.uuid4()}/reviews/run",
                    json={"document_id": str(uuid.uuid4()), "review_round": 1},
                )

        assert resp.status_code == 200
        assert resp.json()["overall_status"] == aggregated.overall_status


class TestGetReviewRoundAPI:
    @pytest.mark.asyncio
    async def test_get_review_round_200(self):
        aggregated = _agg()

        with patch("api.review._service") as mock_service:
            mock_service.get_review_round = AsyncMock(return_value=aggregated)
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}/reviews/1")

        assert resp.status_code == 200
        assert resp.json()["review_round"] == 1

    @pytest.mark.asyncio
    async def test_get_review_round_404(self):
        with patch("api.review._service") as mock_service:
            mock_service.get_review_round = AsyncMock(return_value=None)
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}/reviews/2")

        assert resp.status_code == 404


class TestGetLatestReviewAPI:
    @pytest.mark.asyncio
    async def test_get_latest_review_200(self):
        aggregated = _agg()

        with patch("api.review._service") as mock_service:
            mock_service.get_latest_review = AsyncMock(return_value=aggregated)
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}/reviews/latest")

        assert resp.status_code == 200
        assert resp.json()["overall_score"] == aggregated.overall_score

    @pytest.mark.asyncio
    async def test_get_latest_review_404(self):
        with patch("api.review._service") as mock_service:
            mock_service.get_latest_review = AsyncMock(return_value=None)
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}/reviews/latest")

        assert resp.status_code == 404
