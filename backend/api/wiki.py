"""FastAPI router for LLM Wiki — source upload, compile, article management, query, lint."""

from __future__ import annotations

import json
import os
from io import BytesIO
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.llm import get_llm_client
from schemas.wiki import (
    WikiArticleResponse,
    WikiArticleUpdate,
    WikiLintReport,
    WikiQueryRequest,
    WikiQueryResponse,
    WikiSourceResponse,
)
from services.wiki_service import WikiService
from skills.base import SkillContext
from skills.wiki_compiler import WikiCompilerSkill

router = APIRouter(prefix="/wiki", tags=["wiki"])
_service = WikiService()
_skill = WikiCompilerSkill()
_allowed_exts = {".md", ".txt", ".docx", ".pdf"}


def _extract_text(content: bytes, ext: str) -> str:
    if ext in {".md", ".txt"}:
        return content.decode("utf-8", errors="ignore")
    if ext == ".docx":
        try:
            from docx import Document
            doc = Document(BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs if p.text)
        except ImportError:
            raise HTTPException(status_code=400, detail="python-docx not installed, cannot read .docx files")
    if ext == ".pdf":
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(BytesIO(content)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    if t:
                        pages.append(t)
            return "\n".join(pages)
        except ImportError:
            raise HTTPException(status_code=400, detail="pdfplumber not installed, cannot read .pdf files")
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")


def _source_to_resp(s: object) -> WikiSourceResponse:
    return WikiSourceResponse(
        id=str(getattr(s, "id")),
        filename=str(getattr(s, "filename")),
        compiled=bool(getattr(s, "compiled")),
        uploaded_at=getattr(s, "uploaded_at"),
    )


def _article_to_resp(a: object) -> WikiArticleResponse:
    return WikiArticleResponse(
        id=str(getattr(a, "id")),
        title=str(getattr(a, "title")),
        category=str(getattr(a, "category")),
        content=str(getattr(a, "content")),
        summary=str(getattr(a, "summary")),
        backlinks=list(getattr(a, "backlinks") or []),
        source_doc_ids=list(getattr(a, "source_doc_ids") or []),
        health_score=getattr(a, "health_score"),
        created_at=getattr(a, "created_at"),
        updated_at=getattr(a, "updated_at"),
    )


# ------------------------------------------------------------------
# Sources
# ------------------------------------------------------------------
@router.post("/sources", status_code=201, response_model=WikiSourceResponse)
async def upload_source(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> WikiSourceResponse:
    filename = file.filename or "unnamed"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    payload = await file.read()
    text = _extract_text(payload, ext)
    source = await _service.create_source(db, filename=filename, content=text)
    return _source_to_resp(source)


@router.get("/sources", response_model=list[WikiSourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[WikiSourceResponse]:
    sources = await _service.list_sources(db)
    return [_source_to_resp(s) for s in sources]


# ------------------------------------------------------------------
# Compile
# ------------------------------------------------------------------
@router.post("/compile")
async def compile_wiki(db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Compile all uncompiled sources into wiki articles. Streams progress via SSE."""

    async def stream() -> AsyncGenerator[str, None]:
        sources = await _service.get_uncompiled_sources(db)
        if not sources:
            yield f"data: {json.dumps({'status': 'done', 'message': '没有待编译的源文件', 'articles_created': 0})}\n\n"
            return

        yield f"data: {json.dumps({'status': 'start', 'total_sources': len(sources)})}\n\n"

        llm = get_llm_client()
        total_articles = 0

        for i, source in enumerate(sources):
            yield f"data: {json.dumps({'status': 'compiling', 'source': source.filename, 'progress': i + 1, 'total': len(sources)})}\n\n"
            context = SkillContext(
                task_id="wiki",
                llm_client=llm,
                db_session=db,
                input_data={
                    "operation": "compile",
                    "sources": [{"id": str(source.id), "filename": source.filename, "content": source.content}],
                },
            )
            result = await _skill.execute(context)
            if result.success:
                for art in result.output.get("articles", []):
                    await _service.upsert_article(
                        db,
                        title=art["title"],
                        category=art.get("category", "general"),
                        content=art["content"],
                        summary=art.get("summary", ""),
                        source_doc_ids=art.get("source_doc_ids", [str(source.id)]),
                        backlinks=art.get("backlinks", []),
                    )
                    total_articles += 1
                await _service.mark_source_compiled(db, str(source.id))
            else:
                yield f"data: {json.dumps({'status': 'error', 'source': source.filename, 'error': result.error})}\n\n"

        yield f"data: {json.dumps({'status': 'done', 'articles_created': total_articles})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


# ------------------------------------------------------------------
# Articles
# ------------------------------------------------------------------
@router.get("/articles", response_model=list[WikiArticleResponse])
async def list_articles(
    category: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[WikiArticleResponse]:
    articles = await _service.list_articles(db, category=category)
    return [_article_to_resp(a) for a in articles]


@router.get("/articles/{article_id}", response_model=WikiArticleResponse)
async def get_article(
    article_id: str, db: AsyncSession = Depends(get_db)
) -> WikiArticleResponse:
    article = await _service.get_article(db, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_to_resp(article)


@router.put("/articles/{article_id}", response_model=WikiArticleResponse)
async def update_article(
    article_id: str, body: WikiArticleUpdate, db: AsyncSession = Depends(get_db)
) -> WikiArticleResponse:
    article = await _service.update_article(
        db, article_id,
        title=body.title, category=body.category,
        content=body.content, summary=body.summary,
    )
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_to_resp(article)


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(
    article_id: str, db: AsyncSession = Depends(get_db)
) -> Response:
    deleted = await _service.delete_article(db, article_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return Response(status_code=204)


# ------------------------------------------------------------------
# Query
# ------------------------------------------------------------------
@router.post("/query", response_model=WikiQueryResponse)
async def query_wiki(
    body: WikiQueryRequest, db: AsyncSession = Depends(get_db)
) -> WikiQueryResponse:
    articles = await _service.list_articles(db, category=body.category)
    if not articles:
        return WikiQueryResponse(answer="知识库暂无文章，请先上传资料并编译。", source_article_ids=[])

    llm = get_llm_client()
    context = SkillContext(
        task_id="wiki",
        llm_client=llm,
        db_session=db,
        input_data={
            "operation": "query",
            "question": body.question,
            "articles": [
                {"id": str(a.id), "title": a.title, "content": a.content}
                for a in articles
            ],
        },
    )
    result = await _skill.execute(context)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return WikiQueryResponse(
        answer=result.output.get("answer", ""),
        source_article_ids=result.output.get("source_article_ids", []),
    )


# ------------------------------------------------------------------
# Lint
# ------------------------------------------------------------------
@router.post("/lint", response_model=WikiLintReport)
async def lint_wiki(db: AsyncSession = Depends(get_db)) -> WikiLintReport:
    articles = await _service.list_articles(db)
    if not articles:
        return WikiLintReport(total_articles=0, issues=[], updated_scores={})

    llm = get_llm_client()
    context = SkillContext(
        task_id="wiki",
        llm_client=llm,
        db_session=db,
        input_data={
            "operation": "lint",
            "articles": [
                {"id": str(a.id), "title": a.title, "category": a.category,
                 "summary": a.summary, "backlinks": a.backlinks}
                for a in articles
            ],
        },
    )
    result = await _skill.execute(context)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    scores: dict[str, float] = result.output.get("scores", {})
    for article_id, score in scores.items():
        await _service.update_health_score(db, article_id, float(score))

    return WikiLintReport(
        total_articles=len(articles),
        issues=result.output.get("issues", []),
        updated_scores=scores,
    )
