"""RAG service for knowledge chunk ingestion and pgvector search."""

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Protocol, cast

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.knowledge import KnowledgeChunk


class EmbeddingClient(Protocol):
    """Protocol for embedding-capable clients."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...


def chunk_text(text_value: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into fixed-size chunks with overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = text_value.strip()
    if not normalized:
        return []

    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(normalized), step):
        part = normalized[start : start + chunk_size]
        if part:
            chunks.append(part)
        if start + chunk_size >= len(normalized):
            break
    return chunks


class RAGService:
    """Service encapsulating ingestion and vector retrieval for knowledge chunks."""

    def __init__(self, llm_client: EmbeddingClient | None = None) -> None:
        if llm_client is None:
            from core.llm import get_llm_client

            self.llm_client: EmbeddingClient = get_llm_client()
        else:
            self.llm_client = llm_client

    async def ingest_document(
        self,
        db: AsyncSession,
        document_id: str,
        filename: str,
        chunks: list[str],
    ) -> list[KnowledgeChunk]:
        """Embed and persist chunk rows for one document."""
        normalized_chunks: list[str] = []
        for raw_chunk in chunks:
            normalized_chunks.extend(chunk_text(raw_chunk, chunk_size=500, overlap=50))

        if not normalized_chunks:
            return []

        embeddings = await self.llm_client.embed(normalized_chunks)
        saved: list[KnowledgeChunk] = []
        document_uuid = uuid.UUID(document_id)
        for idx, (chunk_value, embedding) in enumerate(
            zip(normalized_chunks, embeddings, strict=True)
        ):
            row = KnowledgeChunk(
                document_id=document_uuid,
                filename=filename,
                chunk_index=idx,
                content=chunk_value,
                embedding=embedding,
            )
            db.add(row)
            saved.append(row)

        await db.commit()
        return saved

    async def search(
        self,
        db: AsyncSession,
        query: str,
        top_k: int = 5,
    ) -> list[KnowledgeChunk]:
        """Run cosine similarity search using pgvector <=> operator."""
        query_embedding = (await self.llm_client.embed([query]))[0]
        embedding_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"

        stmt = (
            select(KnowledgeChunk)
            .from_statement(
                text(
                    """
                    SELECT *
                    FROM knowledge_chunks
                    ORDER BY embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :top_k
                    """
                )
            )
            .params(query_embedding=embedding_literal, top_k=top_k)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_document_chunks(self, db: AsyncSession, document_id: str) -> None:
        """Delete all chunks associated with one document_id."""
        stmt = delete(KnowledgeChunk).where(
            KnowledgeChunk.document_id == uuid.UUID(document_id)
        )
        _ = await db.execute(stmt)
        await db.commit()

    async def list_documents(
        self, db: AsyncSession
    ) -> list[dict[str, str | int | None]]:
        """List distinct documents currently present in the knowledge chunk table."""
        stmt = (
            select(
                KnowledgeChunk.document_id.label("id"),
                KnowledgeChunk.filename.label("filename"),
                func.count(KnowledgeChunk.id).label("chunk_count"),
            )
            .where(KnowledgeChunk.document_id.is_not(None))
            .group_by(KnowledgeChunk.document_id, KnowledgeChunk.filename)
            .order_by(func.max(KnowledgeChunk.created_at).desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            {
                "id": cast(str | None, row.id),
                "filename": cast(str | None, row.filename),
                "chunk_count": int(cast(int, row.chunk_count)),
            }
            for row in rows
        ]

    async def get_stats(self, db: AsyncSession) -> dict[str, int | datetime | None]:
        """Get aggregate counters for the knowledge base."""
        stmt = select(
            func.count(func.distinct(KnowledgeChunk.document_id)).label(
                "total_documents"
            ),
            func.count(KnowledgeChunk.id).label("total_chunks"),
            func.max(KnowledgeChunk.created_at).label("last_updated"),
        )
        result = await db.execute(stmt)
        stats = result.one()
        return {
            "total_documents": int(cast(int | None, stats.total_documents) or 0),
            "total_chunks": int(cast(int | None, stats.total_chunks) or 0),
            "last_updated": cast(datetime | None, stats.last_updated),
        }
