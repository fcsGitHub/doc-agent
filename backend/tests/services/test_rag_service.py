"""Unit tests for RAGService and chunk_text."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.rag_service import (  # pyright: ignore[reportMissingImports]
    RAGService,
    chunk_text,
)


def _mock_db() -> AsyncMock:
    """Create a fully mocked AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


class TestRAGService:
    @pytest.mark.asyncio
    async def test_ingest_stores_chunks(self):
        """ingest_document stores one KnowledgeChunk row per chunk."""
        db = _mock_db()
        llm_client = AsyncMock()
        llm_client.embed = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
        service = RAGService(llm_client=llm_client)

        chunks = ["chunk-1", "chunk-2"]
        result = await service.ingest_document(
            db,
            document_id="doc-123",
            filename="kb.md",
            chunks=chunks,
        )

        llm_client.embed.assert_awaited_once_with(chunks)
        assert db.add.call_count == 2
        db.commit.assert_awaited_once()
        assert len(result) == 2
        assert result[0].chunk_index == 0
        assert result[1].chunk_index == 1

    @pytest.mark.asyncio
    async def test_search_returns_ordered_results(self):
        """search delegates retrieval to pgvector ORDER BY <=> query."""
        db = _mock_db()
        llm_client = AsyncMock()
        llm_client.embed = AsyncMock(return_value=[[0.11, 0.22, 0.33]])
        service = RAGService(llm_client=llm_client)

        first = MagicMock()
        second = MagicMock()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [first, second]
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        result = await service.search(db, query="test query", top_k=2)

        llm_client.embed.assert_awaited_once_with(["test query"])
        db.execute.assert_awaited_once()
        stmt = db.execute.await_args.args[0]
        assert "<=>" in str(stmt)
        assert result == [first, second]

    @pytest.mark.asyncio
    async def test_delete_removes_chunks(self):
        """delete_document_chunks executes delete and commits."""
        db = _mock_db()
        llm_client = AsyncMock()
        service = RAGService(llm_client=llm_client)

        await service.delete_document_chunks(db, "doc-delete")

        db.execute.assert_awaited_once()
        stmt = db.execute.await_args.args[0]
        assert "DELETE FROM knowledge_chunks" in str(stmt)
        db.commit.assert_awaited_once()


class TestChunkText:
    def test_chunk_text_splits_correctly(self):
        """chunk_text applies fixed-size chunking with overlap."""
        payload = "a" * 1200
        chunks = chunk_text(payload, chunk_size=500, overlap=50)

        assert len(chunks) == 3
        assert all(len(chunk) <= 500 for chunk in chunks)
        assert chunks[0][-50:] == chunks[1][:50]
        assert chunks[1][-50:] == chunks[2][:50]
