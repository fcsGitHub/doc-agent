"""Tests for Wiki API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_wiki_service():
    from services.wiki_service import WikiService
    svc = MagicMock(spec=WikiService)
    svc.list_sources = AsyncMock(return_value=[])
    svc.list_articles = AsyncMock(return_value=[])
    svc.list_categories = AsyncMock(return_value=[])
    return svc


@pytest.mark.asyncio
async def test_list_wiki_sources_empty(mock_wiki_service):
    with patch("api.wiki._service", mock_wiki_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/wiki/sources")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_wiki_articles_empty(mock_wiki_service):
    with patch("api.wiki._service", mock_wiki_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/wiki/articles")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_query_wiki_empty_returns_default(mock_wiki_service):
    with patch("api.wiki._service", mock_wiki_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/wiki/query", json={"question": "What is ISO 9001?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["source_article_ids"] == []


@pytest.mark.asyncio
async def test_lint_wiki_empty_returns_no_issues(mock_wiki_service):
    with patch("api.wiki._service", mock_wiki_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/wiki/lint")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_articles"] == 0
    assert data["issues"] == []
