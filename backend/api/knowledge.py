"""Knowledge base API endpoints (ingest, search, list, delete, stats)."""
# pyright: reportCallInDefaultInitializer=false

from __future__ import annotations

import os
import uuid
from io import BytesIO

import pdfplumber  # pyright: ignore[reportMissingImports]
from docx import Document
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.knowledge import (  # pyright: ignore[reportMissingImports]
    KnowledgeChunkResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeStatsResponse,
)
from services.rag_service import RAGService, chunk_text  # pyright: ignore[reportMissingImports]

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_service = RAGService()
_allowed_extensions = {".docx", ".pdf", ".md", ".txt"}


def _extract_text(content: bytes, ext: str) -> str:
    """Extract plain text from supported knowledge base file types."""
    if ext in {".md", ".txt"}:
        return content.decode("utf-8", errors="ignore")

    if ext == ".docx":
        doc = Document(BytesIO(content))
        return "\n".join(
            paragraph.text for paragraph in doc.paragraphs if paragraph.text
        )

    if ext == ".pdf":
        pages: list[str] = []
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text:
                    pages.append(page_text)
        return "\n".join(pages)

    raise HTTPException(
        status_code=400,
        detail=f"不支持的文件类型: {ext}，仅支持 .docx, .pdf, .md, .txt",
    )


def _to_chunk_response(item: object) -> KnowledgeChunkResponse:
    return KnowledgeChunkResponse(
        id=str(getattr(item, "id")),
        document_id=getattr(item, "document_id"),
        filename=getattr(item, "filename"),
        chunk_index=int(getattr(item, "chunk_index")),
        content=getattr(item, "content"),
    )


@router.post("/ingest")
async def ingest_knowledge(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Ingest one knowledge file into knowledge_chunks with embeddings."""
    filename = file.filename or "unnamed"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，仅支持 .docx, .pdf, .md, .txt",
        )

    payload = await file.read()
    raw_text = _extract_text(payload, ext)
    chunks = chunk_text(raw_text, chunk_size=500, overlap=50)
    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容为空，无法入库")

    document_id = str(uuid.uuid4())
    saved = await _service.ingest_document(db, document_id, filename, chunks)
    return {
        "document_id": document_id,
        "filename": filename,
        "chunk_count": len(saved),
    }


@router.post("/search", response_model=list[KnowledgeChunkResponse])
async def search_knowledge(
    body: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeChunkResponse]:
    """Run semantic retrieval over knowledge chunks."""
    chunks = await _service.search(db, query=body.query, top_k=body.top_k)
    return [_to_chunk_response(chunk) for chunk in chunks]


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocumentResponse]:
    """List all ingested documents with chunk counts."""
    docs = await _service.list_documents(db)
    return [
        KnowledgeDocumentResponse(
            id=str(doc["id"]),
            filename=(
                doc["filename"]
                if doc["filename"] is None or isinstance(doc["filename"], str)
                else str(doc["filename"])
            ),
            chunk_count=int(doc["chunk_count"]),
        )
        for doc in docs
    ]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str, db: AsyncSession = Depends(get_db)
) -> Response:
    """Delete all chunks associated with one document_id."""
    await _service.delete_document_chunks(db, document_id)
    return Response(status_code=204)


@router.get("/stats", response_model=KnowledgeStatsResponse)
async def knowledge_stats(db: AsyncSession = Depends(get_db)) -> KnowledgeStatsResponse:
    """Return knowledge base aggregate statistics."""
    stats = await _service.get_stats(db)
    return KnowledgeStatsResponse(
        total_documents=int(stats["total_documents"]),
        total_chunks=int(stats["total_chunks"]),
        last_updated=(
            stats["last_updated"]
            if hasattr(stats["last_updated"], "isoformat")
            else None
        ),
    )
