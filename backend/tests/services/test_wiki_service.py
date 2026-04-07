"""Tests for WikiService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.wiki_service import WikiService


@pytest.fixture
def service():
    return WikiService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_source(service, mock_db):
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())
    source = await service.create_source(mock_db, filename="test.md", content="# Hello")
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert source.filename == "test.md"
    assert source.compiled is False


@pytest.mark.asyncio
async def test_upsert_article_creates_new(service, mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())

    article = await service.upsert_article(
        mock_db,
        title="ISO 9001 Overview",
        category="standards",
        content="## ISO 9001\nQuality management.",
        summary="ISO 9001 quality standard overview",
        source_doc_ids=["src-1"],
    )
    mock_db.add.assert_called_once()
    assert article.title == "ISO 9001 Overview"


@pytest.mark.asyncio
async def test_upsert_article_updates_existing(service, mock_db):
    from models.wiki import WikiArticle
    existing = WikiArticle(
        title="ISO 9001 Overview",
        category="standards",
        content="Old content",
        summary="Old summary",
        source_doc_ids=["src-0"],
        backlinks=[],
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = mock_result
    mock_db.refresh.side_effect = lambda obj: None

    article = await service.upsert_article(
        mock_db,
        title="ISO 9001 Overview",
        category="standards",
        content="New content",
        summary="New summary",
        source_doc_ids=["src-1"],
    )
    assert article.content == "New content"
    assert "src-0" in article.source_doc_ids
    assert "src-1" in article.source_doc_ids
