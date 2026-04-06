# LLM Wiki Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Plan 1 (LLM Config) must be completed first.

**Goal:** Implement Karpathy-style LLM wiki alongside existing RAG. Users upload raw source documents, the LLM "compiles" them into structured Markdown wiki articles organized by category. Queries go directly to wiki articles (no vector search). Existing `/knowledge` RAG is preserved.

**Architecture:** `WikiCompilerSkill` in `skills/wiki_compiler.py` handles compile/query/lint/index operations. Wiki articles are stored as plain text in `wiki_articles` table. `compile` reads uncompiled `wiki_raw_sources`, calls LLM to produce article JSON, upserts articles, updates backlinks. `query` loads category index records then reads full articles. Coexists with existing RAG.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Next.js 14, TanStack Query, react-markdown

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/models/wiki.py` | WikiRawSource + WikiArticle ORM models |
| Create | `backend/alembic/versions/0004_add_wiki_tables.py` | DB migration |
| Create | `backend/schemas/wiki.py` | Pydantic request/response schemas |
| Create | `backend/services/wiki_service.py` | CRUD for sources and articles |
| Create | `backend/skills/wiki_compiler.py` | compile/query/lint/index operations |
| Create | `backend/api/wiki.py` | HTTP endpoints + compile SSE |
| Modify | `backend/api/router.py` | Register wiki router |
| Create | `backend/tests/models/test_wiki.py` | Model tests |
| Create | `backend/tests/services/test_wiki_service.py` | Service tests |
| Create | `backend/tests/skills/test_wiki_compiler.py` | Skill tests |
| Create | `backend/tests/api/test_wiki.py` | API tests |
| Modify | `frontend/components/layout/sidebar.tsx` | Add Wiki nav link |
| Create | `frontend/app/wiki/page.tsx` | Wiki root page |
| Create | `frontend/components/wiki/article-tree.tsx` | Category tree (left panel) |
| Create | `frontend/components/wiki/article-viewer.tsx` | Markdown article reader |
| Create | `frontend/components/wiki/article-editor.tsx` | Inline Markdown editor |
| Create | `frontend/components/wiki/lint-report.tsx` | Health check results |
| Create | `frontend/lib/api/wiki.ts` | API client |
| Create | `frontend/lib/hooks/use-wiki.ts` | TanStack Query hooks |

---

### Task 1: ORM Models + Migration

**Files:**
- Create: `backend/models/wiki.py`
- Create: `backend/alembic/versions/0004_add_wiki_tables.py`

- [ ] **Step 1: Write failing model test**

```python
# backend/tests/models/test_wiki.py
import pytest
from models.wiki import WikiRawSource, WikiArticle

def test_wiki_raw_source_table():
    assert WikiRawSource.__tablename__ == "wiki_raw_sources"
    cols = {c.name for c in WikiRawSource.__table__.columns}
    assert {"id", "filename", "content", "compiled", "uploaded_at"} <= cols

def test_wiki_article_table():
    assert WikiArticle.__tablename__ == "wiki_articles"
    cols = {c.name for c in WikiArticle.__table__.columns}
    assert {"id", "title", "category", "content", "summary",
            "backlinks", "source_doc_ids", "health_score", "created_at", "updated_at"} <= cols
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/models/test_wiki.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/models/wiki.py`**

```python
"""WikiRawSource and WikiArticle ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDMixin


class WikiRawSource(Base, UUIDMixin):
    __tablename__ = "wiki_raw_sources"

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    compiled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WikiArticle(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wiki_articles"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(200), nullable=False, server_default="general")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False, server_default="")
    backlinks: Mapped[list] = mapped_column(JSONB, server_default="[]")
    source_doc_ids: Mapped[list] = mapped_column(JSONB, server_default="[]")
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
```

- [ ] **Step 3: Run model test**

Run: `cd backend && LITELLM_MOCK=true pytest tests/models/test_wiki.py -v`
Expected: PASS

- [ ] **Step 4: Create migration `backend/alembic/versions/0004_add_wiki_tables.py`**

```python
"""Add wiki_raw_sources and wiki_articles tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-06
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wiki_raw_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("compiled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "wiki_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(200), nullable=False, server_default="general"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False, server_default=""),
        sa.Column("backlinks", postgresql.JSONB, server_default="[]"),
        sa.Column("source_doc_ids", postgresql.JSONB, server_default="[]"),
        sa.Column("health_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_wiki_articles_category", "wiki_articles", ["category"])


def downgrade() -> None:
    op.drop_index("ix_wiki_articles_category", table_name="wiki_articles")
    op.drop_table("wiki_articles")
    op.drop_table("wiki_raw_sources")
```

- [ ] **Step 5: Commit**

```bash
git add backend/models/wiki.py backend/alembic/versions/0004_add_wiki_tables.py backend/tests/models/test_wiki.py
git commit -m "feat: add WikiRawSource and WikiArticle ORM models and migration"
```

---

### Task 2: Wiki Service

**Files:**
- Create: `backend/schemas/wiki.py`
- Create: `backend/services/wiki_service.py`
- Create: `backend/tests/services/test_wiki_service.py`

- [ ] **Step 1: Write failing service tests**

```python
# backend/tests/services/test_wiki_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.wiki_service import WikiService
from models.wiki import WikiRawSource, WikiArticle
import uuid

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
    mock_result.scalar_one_or_none.return_value = None  # no existing article
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
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/services/test_wiki_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/schemas/wiki.py`**

```python
"""Pydantic schemas for Wiki endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WikiSourceResponse(BaseModel):
    id: str
    filename: str
    compiled: bool
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class WikiArticleResponse(BaseModel):
    id: str
    title: str
    category: str
    content: str
    summary: str
    backlinks: list[str]
    source_doc_ids: list[str]
    health_score: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WikiArticleUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    content: str | None = None
    summary: str | None = None


class WikiQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    category: str | None = None


class WikiQueryResponse(BaseModel):
    answer: str
    source_article_ids: list[str]


class WikiLintReport(BaseModel):
    total_articles: int
    issues: list[dict[str, Any]]
    updated_scores: dict[str, float]  # article_id -> new health_score
```

- [ ] **Step 3: Create `backend/services/wiki_service.py`**

```python
"""Wiki service — CRUD for raw sources and wiki articles."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.wiki import WikiArticle, WikiRawSource


class WikiService:
    """CRUD operations for wiki sources and articles."""

    # ------------------------------------------------------------------
    # Raw sources
    # ------------------------------------------------------------------
    async def create_source(
        self, db: AsyncSession, filename: str, content: str
    ) -> WikiRawSource:
        source = WikiRawSource(filename=filename, content=content, compiled=False)
        db.add(source)
        await db.commit()
        await db.refresh(source)
        return source

    async def list_sources(self, db: AsyncSession) -> Sequence[WikiRawSource]:
        result = await db.execute(
            select(WikiRawSource).order_by(WikiRawSource.uploaded_at.desc())
        )
        return result.scalars().all()

    async def get_uncompiled_sources(self, db: AsyncSession) -> Sequence[WikiRawSource]:
        result = await db.execute(
            select(WikiRawSource).where(WikiRawSource.compiled.is_(False))
        )
        return result.scalars().all()

    async def mark_source_compiled(self, db: AsyncSession, source_id: str) -> None:
        result = await db.execute(
            select(WikiRawSource).where(WikiRawSource.id == uuid.UUID(source_id))
        )
        source = result.scalar_one_or_none()
        if source:
            source.compiled = True
            await db.commit()

    # ------------------------------------------------------------------
    # Articles
    # ------------------------------------------------------------------
    async def list_articles(
        self, db: AsyncSession, category: str | None = None
    ) -> Sequence[WikiArticle]:
        stmt = select(WikiArticle).order_by(WikiArticle.category, WikiArticle.title)
        if category:
            stmt = stmt.where(WikiArticle.category == category)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_article(self, db: AsyncSession, article_id: str) -> WikiArticle | None:
        result = await db.execute(
            select(WikiArticle).where(WikiArticle.id == uuid.UUID(article_id))
        )
        return result.scalar_one_or_none()

    async def upsert_article(
        self,
        db: AsyncSession,
        title: str,
        category: str,
        content: str,
        summary: str,
        source_doc_ids: list[str],
        backlinks: list[str] | None = None,
    ) -> WikiArticle:
        """Create article or update if one with the same title+category exists."""
        result = await db.execute(
            select(WikiArticle).where(
                WikiArticle.title == title, WikiArticle.category == category
            )
        )
        article = result.scalar_one_or_none()
        if article is None:
            article = WikiArticle(
                title=title,
                category=category,
                content=content,
                summary=summary,
                source_doc_ids=source_doc_ids,
                backlinks=backlinks or [],
            )
            db.add(article)
        else:
            article.content = content
            article.summary = summary
            existing_sources = list(article.source_doc_ids or [])
            for sid in source_doc_ids:
                if sid not in existing_sources:
                    existing_sources.append(sid)
            article.source_doc_ids = existing_sources
            if backlinks is not None:
                article.backlinks = backlinks
        await db.commit()
        await db.refresh(article)
        return article

    async def update_article(
        self,
        db: AsyncSession,
        article_id: str,
        title: str | None = None,
        category: str | None = None,
        content: str | None = None,
        summary: str | None = None,
    ) -> WikiArticle | None:
        article = await self.get_article(db, article_id)
        if article is None:
            return None
        if title is not None:
            article.title = title
        if category is not None:
            article.category = category
        if content is not None:
            article.content = content
        if summary is not None:
            article.summary = summary
        await db.commit()
        await db.refresh(article)
        return article

    async def delete_article(self, db: AsyncSession, article_id: str) -> bool:
        article = await self.get_article(db, article_id)
        if article is None:
            return False
        await db.delete(article)
        await db.commit()
        return True

    async def update_health_score(
        self, db: AsyncSession, article_id: str, score: float
    ) -> None:
        article = await self.get_article(db, article_id)
        if article:
            article.health_score = score
            await db.commit()

    async def list_categories(self, db: AsyncSession) -> list[str]:
        """Return distinct category names sorted alphabetically."""
        result = await db.execute(
            select(WikiArticle.category).distinct().order_by(WikiArticle.category)
        )
        return [row[0] for row in result.all()]
```

- [ ] **Step 4: Run service tests**

Run: `cd backend && LITELLM_MOCK=true pytest tests/services/test_wiki_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/wiki.py backend/services/wiki_service.py backend/tests/services/test_wiki_service.py
git commit -m "feat: add Wiki schemas and service"
```

---

### Task 3: Wiki Compiler Skill

**Files:**
- Create: `backend/skills/wiki_compiler.py`
- Create: `backend/tests/skills/test_wiki_compiler.py`

- [ ] **Step 1: Write failing skill tests**

```python
# backend/tests/skills/test_wiki_compiler.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from skills.wiki_compiler import WikiCompilerSkill
from skills.base import SkillContext, SkillResult

@pytest.fixture
def mock_llm():
    client = MagicMock()
    client.complete_json = AsyncMock(return_value={
        "articles": [
            {
                "title": "ISO 9001 Overview",
                "category": "standards",
                "content": "## ISO 9001\nQuality management system standard.",
                "summary": "ISO 9001 overview",
                "backlinks": [],
            }
        ]
    })
    return client

@pytest.mark.asyncio
async def test_compile_returns_articles(mock_llm):
    skill = WikiCompilerSkill()
    context = SkillContext(
        task_id="test",
        llm_client=mock_llm,
        input_data={
            "operation": "compile",
            "sources": [{"id": "src-1", "filename": "iso.md", "content": "ISO 9001 content"}],
        },
    )
    result = await skill.execute(context)
    assert result.success is True
    assert len(result.output["articles"]) == 1
    assert result.output["articles"][0]["title"] == "ISO 9001 Overview"

@pytest.mark.asyncio
async def test_query_returns_answer(mock_llm):
    mock_llm.complete_json = AsyncMock(return_value={
        "answer": "ISO 9001 is a quality management standard.",
        "source_article_ids": ["article-1"],
    })
    skill = WikiCompilerSkill()
    context = SkillContext(
        task_id="test",
        llm_client=mock_llm,
        input_data={
            "operation": "query",
            "question": "What is ISO 9001?",
            "articles": [{"id": "article-1", "title": "ISO 9001", "content": "Quality standard."}],
        },
    )
    result = await skill.execute(context)
    assert result.success is True
    assert "answer" in result.output

@pytest.mark.asyncio
async def test_unknown_operation_fails():
    skill = WikiCompilerSkill()
    context = SkillContext(
        task_id="test",
        input_data={"operation": "unknown"},
    )
    result = await skill.execute(context)
    assert result.success is False
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/skills/test_wiki_compiler.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/skills/wiki_compiler.py`**

```python
"""WikiCompilerSkill — compile raw sources into wiki articles, query, and lint."""

from __future__ import annotations

import time
from typing import Any

from skills.base import BaseSkill, SkillContext, SkillResult

_COMPILE_SYSTEM = """\
You are a knowledge compiler. Given raw source documents, extract key concepts and
generate structured wiki articles in Markdown. Each article should cover one concept
or topic clearly and concisely.

Return JSON with structure:
{
  "articles": [
    {
      "title": "Concept Name",
      "category": "standards|terms|cases|general",
      "content": "## Title\\nMarkdown content...",
      "summary": "One-sentence summary under 200 chars",
      "backlinks": ["Other Article Title", ...]
    }
  ]
}

Guidelines:
- One article per distinct concept (merge related minor points)
- category must be one of: standards, terms, cases, general
- backlinks should reference other article titles found in the same compilation
- content should be self-contained Markdown (use ## for sections within the article)
"""

_QUERY_SYSTEM = """\
You are a knowledge base assistant. Answer the user's question using ONLY the
provided wiki articles. Cite which articles you used.

Return JSON:
{
  "answer": "Detailed answer in Markdown format",
  "source_article_ids": ["<article id>", ...]
}

If the answer cannot be found in the provided articles, say so clearly.
"""

_LINT_SYSTEM = """\
You are a wiki quality reviewer. Analyze the provided wiki articles and identify:
1. Contradictions between articles
2. Orphaned articles (no backlinks, isolated topics)
3. Missing or incomplete articles referenced by backlinks
4. Stale or low-quality content

Return JSON:
{
  "issues": [
    {
      "type": "contradiction|orphan|missing_reference|low_quality",
      "article_id": "<id or null>",
      "article_title": "<title>",
      "description": "Issue description",
      "suggestion": "How to fix"
    }
  ],
  "scores": {
    "<article_id>": <float 0.0-1.0>
  }
}
"""


class WikiCompilerSkill(BaseSkill):
    """Performs wiki compile, query, lint, and index operations."""

    name = "wiki_compiler"
    description = "Compile raw documents into wiki articles; query and lint the wiki"
    prerequisites: list[str] = []

    async def execute(self, context: SkillContext) -> SkillResult:
        start_ms = int(time.time() * 1000)
        operation = context.input_data.get("operation")

        dispatch = {
            "compile": self._compile,
            "query": self._query,
            "lint": self._lint,
        }

        handler = dispatch.get(operation)  # type: ignore[arg-type]
        if handler is None:
            return SkillResult(
                success=False,
                error=f"Unknown wiki operation: {operation!r}. Must be one of: {list(dispatch)}",
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

        try:
            output = await handler(context)
            return SkillResult(
                success=True,
                output=output,
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                error=str(exc),
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

    async def _compile(self, context: SkillContext) -> dict[str, Any]:
        """Compile a list of raw source dicts into wiki article dicts."""
        llm = context.llm_client
        if llm is None:
            raise ValueError("llm_client required for compile operation")

        sources: list[dict[str, Any]] = context.input_data.get("sources", [])
        if not sources:
            return {"articles": []}

        combined_text = "\n\n---\n\n".join(
            f"Source: {s.get('filename', 'unknown')}\n{s.get('content', '')}"
            for s in sources
        )

        messages = [
            {"role": "system", "content": _COMPILE_SYSTEM},
            {"role": "user", "content": f"Compile the following documents into wiki articles:\n\n{combined_text}"},
        ]
        result = await llm.complete_json(messages=messages)
        # Attach source ids to each article
        source_ids = [str(s.get("id", "")) for s in sources]
        for article in result.get("articles", []):
            article["source_doc_ids"] = source_ids
        return result

    async def _query(self, context: SkillContext) -> dict[str, Any]:
        """Answer a question using provided wiki article dicts."""
        llm = context.llm_client
        if llm is None:
            raise ValueError("llm_client required for query operation")

        question: str = context.input_data.get("question", "")
        articles: list[dict[str, Any]] = context.input_data.get("articles", [])

        articles_text = "\n\n---\n\n".join(
            f"[{a.get('id', '?')}] ## {a.get('title', '')}\n{a.get('content', '')}"
            for a in articles
        )

        messages = [
            {"role": "system", "content": _QUERY_SYSTEM},
            {"role": "user", "content": f"Wiki articles:\n{articles_text}\n\nQuestion: {question}"},
        ]
        return await llm.complete_json(messages=messages)

    async def _lint(self, context: SkillContext) -> dict[str, Any]:
        """Run health check over provided wiki article dicts."""
        llm = context.llm_client
        if llm is None:
            raise ValueError("llm_client required for lint operation")

        articles: list[dict[str, Any]] = context.input_data.get("articles", [])
        if not articles:
            return {"issues": [], "scores": {}}

        articles_text = "\n\n---\n\n".join(
            f"[{a.get('id', '?')}] {a.get('title', '')}\nCategory: {a.get('category', '')}\n"
            f"Summary: {a.get('summary', '')}\nBacklinks: {a.get('backlinks', [])}"
            for a in articles
        )

        messages = [
            {"role": "system", "content": _LINT_SYSTEM},
            {"role": "user", "content": f"Review these wiki articles:\n{articles_text}"},
        ]
        return await llm.complete_json(messages=messages)


from skills.registry import get_skill_registry  # noqa: E402
get_skill_registry().register(WikiCompilerSkill())
```

- [ ] **Step 3: Run skill tests**

Run: `cd backend && LITELLM_MOCK=true pytest tests/skills/test_wiki_compiler.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/skills/wiki_compiler.py backend/tests/skills/test_wiki_compiler.py
git commit -m "feat: add WikiCompilerSkill with compile/query/lint operations"
```

---

### Task 4: Wiki API Endpoints

**Files:**
- Create: `backend/api/wiki.py`
- Modify: `backend/api/router.py`
- Create: `backend/tests/api/test_wiki.py`

- [ ] **Step 1: Write failing API tests**

```python
# backend/tests/api/test_wiki.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
import uuid, datetime
from models.wiki import WikiArticle

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
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/api/test_wiki.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/api/wiki.py`**

```python
"""FastAPI router for LLM Wiki — source upload, compile, article management, query, lint."""

from __future__ import annotations

import asyncio
import json
import os
from io import BytesIO
from typing import AsyncGenerator

from docx import Document
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
        doc = Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    if ext == ".pdf":
        import pdfplumber
        pages = []
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    pages.append(t)
        return "\n".join(pages)
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
# Compile (async with SSE progress)
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
    # Load articles: filter by category if specified, else all
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
```

- [ ] **Step 3: Modify `backend/api/router.py`**

```python
# Add to imports:
from api.wiki import router as wiki_router

# Add to include_router calls:
router.include_router(wiki_router)
```

- [ ] **Step 4: Run API tests**

Run: `cd backend && LITELLM_MOCK=true pytest tests/api/test_wiki.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/wiki.py backend/api/router.py backend/tests/api/test_wiki.py
git commit -m "feat: add Wiki API endpoints — sources, compile, articles, query, lint"
```

---

### Task 5: Frontend — API Client + Hooks

**Files:**
- Create: `frontend/lib/api/wiki.ts`
- Create: `frontend/lib/hooks/use-wiki.ts`

- [ ] **Step 1: Create `frontend/lib/api/wiki.ts`**

```typescript
import { apiFetch, API_BASE } from "@/lib/api";

export interface WikiSource {
  id: string;
  filename: string;
  compiled: boolean;
  uploaded_at: string;
}

export interface WikiArticle {
  id: string;
  title: string;
  category: string;
  content: string;
  summary: string;
  backlinks: string[];
  source_doc_ids: string[];
  health_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface WikiArticleUpdate {
  title?: string;
  category?: string;
  content?: string;
  summary?: string;
}

export interface WikiQueryResponse {
  answer: string;
  source_article_ids: string[];
}

export interface WikiLintReport {
  total_articles: number;
  issues: { type: string; article_id: string | null; article_title: string; description: string; suggestion: string }[];
  updated_scores: Record<string, number>;
}

export const wikiApi = {
  listSources: () => apiFetch<WikiSource[]>("/api/v1/wiki/sources"),

  uploadSource: async (file: File): Promise<WikiSource> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/v1/wiki/sources`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },

  listArticles: (category?: string) => {
    const qs = category ? `?category=${encodeURIComponent(category)}` : "";
    return apiFetch<WikiArticle[]>(`/api/v1/wiki/articles${qs}`);
  },

  getArticle: (id: string) => apiFetch<WikiArticle>(`/api/v1/wiki/articles/${id}`),

  updateArticle: (id: string, data: WikiArticleUpdate) =>
    apiFetch<WikiArticle>(`/api/v1/wiki/articles/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteArticle: (id: string) =>
    fetch(`${API_BASE}/api/v1/wiki/articles/${id}`, { method: "DELETE" }),

  compile: async (onEvent: (event: Record<string, unknown>) => void): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/v1/wiki/compile`, { method: "POST" });
    if (!res.ok) throw new Error(`Compile failed: ${res.status}`);
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try { onEvent(JSON.parse(line.slice(6))); } catch { /* ignore */ }
        }
      }
    }
  },

  query: (question: string, category?: string) =>
    apiFetch<WikiQueryResponse>("/api/v1/wiki/query", {
      method: "POST",
      body: JSON.stringify({ question, category: category ?? null }),
    }),

  lint: () => apiFetch<WikiLintReport>("/api/v1/wiki/lint", { method: "POST" }),
};
```

- [ ] **Step 2: Create `frontend/lib/hooks/use-wiki.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { wikiApi, WikiArticleUpdate } from "@/lib/api/wiki";
import { useState } from "react";

export const WIKI_SOURCES_KEY = ["wiki-sources"] as const;
export const WIKI_ARTICLES_KEY = (category?: string) => ["wiki-articles", category] as const;

export function useWikiSources() {
  return useQuery({ queryKey: WIKI_SOURCES_KEY, queryFn: wikiApi.listSources });
}

export function useWikiArticles(category?: string) {
  return useQuery({
    queryKey: WIKI_ARTICLES_KEY(category),
    queryFn: () => wikiApi.listArticles(category),
  });
}

export function useWikiArticle(id: string | null) {
  return useQuery({
    queryKey: ["wiki-article", id],
    queryFn: () => wikiApi.getArticle(id!),
    enabled: !!id,
  });
}

export function useUploadWikiSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => wikiApi.uploadSource(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_SOURCES_KEY }),
  });
}

export function useUpdateWikiArticle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WikiArticleUpdate }) =>
      wikiApi.updateArticle(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() }),
  });
}

export function useDeleteWikiArticle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => wikiApi.deleteArticle(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() }),
  });
}

export function useWikiCompile() {
  const qc = useQueryClient();
  const [progress, setProgress] = useState<Record<string, unknown> | null>(null);
  const [compiling, setCompiling] = useState(false);

  const compile = async () => {
    setCompiling(true);
    setProgress(null);
    try {
      await wikiApi.compile((event) => setProgress(event));
      qc.invalidateQueries({ queryKey: WIKI_SOURCES_KEY });
      qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() });
    } finally {
      setCompiling(false);
    }
  };

  return { compile, compiling, progress };
}

export function useWikiQuery() {
  return useMutation({
    mutationFn: ({ question, category }: { question: string; category?: string }) =>
      wikiApi.query(question, category),
  });
}

export function useWikiLint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: wikiApi.lint,
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() }),
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/wiki.ts frontend/lib/hooks/use-wiki.ts
git commit -m "feat: add Wiki API client and React Query hooks"
```

---

### Task 6: Frontend — Wiki Page UI

**Files:**
- Create: `frontend/components/wiki/article-tree.tsx`
- Create: `frontend/components/wiki/article-viewer.tsx`
- Create: `frontend/components/wiki/article-editor.tsx`
- Create: `frontend/components/wiki/lint-report.tsx`
- Create: `frontend/app/wiki/page.tsx`
- Modify: `frontend/components/layout/sidebar.tsx`

Note: Install `react-markdown` if not present: `cd frontend && npm install react-markdown`

- [ ] **Step 1: Create `frontend/components/wiki/article-tree.tsx`**

```tsx
"use client";

import { useWikiArticles } from "@/lib/hooks/use-wiki";
import { WikiArticle } from "@/lib/api/wiki";

interface Props {
  selectedId: string | null;
  onSelect: (article: WikiArticle) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  standards: "行业规范",
  terms: "术语",
  cases: "历史案例",
  general: "通用",
};

export function ArticleTree({ selectedId, onSelect }: Props) {
  const { data: articles, isLoading } = useWikiArticles();

  if (isLoading) return <div className="p-4 text-sm text-gray-400">加载中...</div>;
  if (!articles?.length) return <div className="p-4 text-sm text-gray-400">暂无文章</div>;

  const grouped = articles.reduce<Record<string, WikiArticle[]>>((acc, a) => {
    const cat = a.category || "general";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(a);
    return acc;
  }, {});

  return (
    <nav className="space-y-4 p-3">
      {Object.entries(grouped).map(([cat, items]) => (
        <div key={cat}>
          <p className="text-xs font-semibold text-gray-500 uppercase px-2 mb-1">
            {CATEGORY_LABELS[cat] ?? cat}
          </p>
          <ul className="space-y-0.5">
            {items.map((a) => (
              <li key={a.id}>
                <button
                  onClick={() => onSelect(a)}
                  className={`w-full text-left text-sm px-2 py-1.5 rounded transition-colors truncate ${
                    selectedId === a.id
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                  title={a.title}
                >
                  {a.health_score !== null && a.health_score < 0.5 && (
                    <span className="mr-1 text-yellow-500">⚠</span>
                  )}
                  {a.title}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Create `frontend/components/wiki/article-viewer.tsx`**

```tsx
"use client";

import ReactMarkdown from "react-markdown";
import { WikiArticle } from "@/lib/api/wiki";
import { useDeleteWikiArticle } from "@/lib/hooks/use-wiki";

interface Props {
  article: WikiArticle;
  onEdit: () => void;
}

export function ArticleViewer({ article, onEdit }: Props) {
  const remove = useDeleteWikiArticle();

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-start justify-between p-4 border-b">
        <div>
          <h1 className="text-xl font-bold text-gray-800">{article.title}</h1>
          <p className="text-xs text-gray-400 mt-1">
            分类：{article.category}
            {article.health_score !== null && (
              <span className={`ml-3 ${article.health_score < 0.5 ? "text-yellow-600" : "text-green-600"}`}>
                健康分：{(article.health_score * 100).toFixed(0)}
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="text-sm border border-gray-300 px-3 py-1.5 rounded hover:bg-gray-50"
          >
            编辑
          </button>
          <button
            onClick={() => remove.mutate(article.id)}
            disabled={remove.isPending}
            className="text-sm border border-red-300 text-red-600 px-3 py-1.5 rounded hover:bg-red-50 disabled:opacity-50"
          >
            删除
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-6 prose prose-sm max-w-none">
        <ReactMarkdown>{article.content}</ReactMarkdown>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/components/wiki/article-editor.tsx`**

```tsx
"use client";

import { useState } from "react";
import { WikiArticle } from "@/lib/api/wiki";
import { useUpdateWikiArticle } from "@/lib/hooks/use-wiki";

interface Props {
  article: WikiArticle;
  onDone: () => void;
}

export function ArticleEditor({ article, onDone }: Props) {
  const [title, setTitle] = useState(article.title);
  const [category, setCategory] = useState(article.category);
  const [content, setContent] = useState(article.content);
  const [summary, setSummary] = useState(article.summary);
  const update = useUpdateWikiArticle();

  const handleSave = () => {
    update.mutate(
      { id: article.id, data: { title, category, content, summary } },
      { onSuccess: onDone }
    );
  };

  return (
    <div className="flex flex-col h-full p-4 space-y-3">
      <div className="flex gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="文章标题"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded border border-gray-300 px-2 py-2 text-sm focus:outline-none"
        >
          <option value="standards">行业规范</option>
          <option value="terms">术语</option>
          <option value="cases">历史案例</option>
          <option value="general">通用</option>
        </select>
      </div>
      <input
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        className="rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none"
        placeholder="摘要（一句话描述）"
      />
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none resize-none"
        placeholder="Markdown 内容..."
      />
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={update.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {update.isPending ? "保存中..." : "保存"}
        </button>
        <button
          onClick={onDone}
          className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50"
        >
          取消
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/components/wiki/lint-report.tsx`**

```tsx
"use client";

import { useWikiLint } from "@/lib/hooks/use-wiki";
import { WikiLintReport as LintData } from "@/lib/api/wiki";

interface Props {
  report: LintData | null;
  onRun: () => void;
  isRunning: boolean;
}

const ISSUE_TYPE_LABEL: Record<string, string> = {
  contradiction: "矛盾",
  orphan: "孤立文章",
  missing_reference: "引用缺失",
  low_quality: "质量偏低",
};

export function LintReport({ report, onRun, isRunning }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onRun}
          disabled={isRunning}
          className="bg-yellow-500 text-white px-4 py-2 rounded text-sm hover:bg-yellow-600 disabled:opacity-50"
        >
          {isRunning ? "检查中..." : "运行健康检查"}
        </button>
        {report && (
          <span className="text-sm text-gray-500">
            共 {report.total_articles} 篇，发现 {report.issues.length} 个问题
          </span>
        )}
      </div>

      {report && report.issues.length > 0 && (
        <div className="space-y-2">
          {report.issues.map((issue, i) => (
            <div key={i} className="rounded border border-yellow-200 bg-yellow-50 p-3 text-sm">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-yellow-800">
                  {ISSUE_TYPE_LABEL[issue.type] ?? issue.type}
                </span>
                {issue.article_title && (
                  <span className="text-gray-600">— {issue.article_title}</span>
                )}
              </div>
              <p className="text-gray-700">{issue.description}</p>
              <p className="text-gray-500 mt-1">建议：{issue.suggestion}</p>
            </div>
          ))}
        </div>
      )}

      {report && report.issues.length === 0 && (
        <p className="text-green-600 text-sm">✓ 知识库状态良好，未发现问题。</p>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Create `frontend/app/wiki/page.tsx`**

```tsx
"use client";

import { useState, useRef } from "react";
import { ArticleTree } from "@/components/wiki/article-tree";
import { ArticleViewer } from "@/components/wiki/article-viewer";
import { ArticleEditor } from "@/components/wiki/article-editor";
import { LintReport } from "@/components/wiki/lint-report";
import {
  useWikiSources,
  useUploadWikiSource,
  useWikiCompile,
  useWikiQuery,
  useWikiLint,
} from "@/lib/hooks/use-wiki";
import { WikiArticle } from "@/lib/api/wiki";

type View = "articles" | "sources" | "query" | "lint";

export default function WikiPage() {
  const [view, setView] = useState<View>("articles");
  const [selectedArticle, setSelectedArticle] = useState<WikiArticle | null>(null);
  const [editing, setEditing] = useState(false);
  const [question, setQuestion] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: sources } = useWikiSources();
  const uploadSource = useUploadWikiSource();
  const { compile, compiling, progress } = useWikiCompile();
  const queryWiki = useWikiQuery();
  const lintWiki = useWikiLint();

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadSource.mutate(file);
  };

  return (
    <div className="flex h-[calc(100vh-120px)] bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Left panel — article tree */}
      <div className="w-64 border-r border-gray-200 overflow-y-auto shrink-0">
        <div className="flex border-b border-gray-200 text-xs">
          {(["articles", "sources", "query", "lint"] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`flex-1 py-2 ${view === v ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-500 hover:bg-gray-50"}`}
            >
              {{ articles: "文章", sources: "源文件", query: "问答", lint: "检查" }[v]}
            </button>
          ))}
        </div>

        {view === "articles" && (
          <ArticleTree selectedId={selectedArticle?.id ?? null} onSelect={(a) => { setSelectedArticle(a); setEditing(false); }} />
        )}

        {view === "sources" && (
          <div className="p-3 space-y-2">
            <input ref={fileRef} type="file" accept=".md,.txt,.docx,.pdf" className="hidden" onChange={handleFileUpload} />
            <button onClick={() => fileRef.current?.click()} className="w-full text-sm bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
              上传源文件
            </button>
            <button
              onClick={compile}
              disabled={compiling}
              className="w-full text-sm border border-blue-600 text-blue-600 py-2 rounded hover:bg-blue-50 disabled:opacity-50"
            >
              {compiling ? "编译中..." : "一键编译"}
            </button>
            {progress && (
              <p className="text-xs text-gray-500 break-words">
                {JSON.stringify(progress)}
              </p>
            )}
            <ul className="space-y-1 mt-2">
              {sources?.map((s) => (
                <li key={s.id} className="text-xs flex items-center gap-1 text-gray-600">
                  <span>{s.compiled ? "✓" : "○"}</span>
                  <span className="truncate">{s.filename}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {view === "query" && (
          <div className="p-3 space-y-2">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="输入问题..."
              rows={4}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={() => queryWiki.mutate({ question })}
              disabled={queryWiki.isPending || !question.trim()}
              className="w-full text-sm bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {queryWiki.isPending ? "查询中..." : "提问"}
            </button>
          </div>
        )}

        {view === "lint" && <div className="p-3 text-xs text-gray-400">点击右侧运行检查</div>}
      </div>

      {/* Right panel */}
      <div className="flex-1 overflow-y-auto">
        {view === "query" && queryWiki.data && (
          <div className="p-6 prose prose-sm max-w-none">
            <h2 className="text-lg font-semibold mb-3">回答</h2>
            <div className="whitespace-pre-wrap text-gray-800">{queryWiki.data.answer}</div>
            {queryWiki.data.source_article_ids.length > 0 && (
              <p className="text-xs text-gray-400 mt-4">
                来源文章 ID：{queryWiki.data.source_article_ids.join(", ")}
              </p>
            )}
          </div>
        )}

        {view === "lint" && (
          <div className="p-6">
            <LintReport
              report={lintWiki.data ?? null}
              onRun={() => lintWiki.mutate()}
              isRunning={lintWiki.isPending}
            />
          </div>
        )}

        {view === "articles" && selectedArticle && !editing && (
          <ArticleViewer article={selectedArticle} onEdit={() => setEditing(true)} />
        )}

        {view === "articles" && selectedArticle && editing && (
          <ArticleEditor article={selectedArticle} onDone={() => setEditing(false)} />
        )}

        {view === "articles" && !selectedArticle && (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            从左侧选择文章查看
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Add Wiki nav link to sidebar**

In `frontend/components/layout/sidebar.tsx`, add `{ label: "Wiki", href: "/wiki" }` to `NAV_ITEMS`:

```typescript
const NAV_ITEMS = [
  { label: "任务列表", href: "/" },
  { label: "工作台", href: "/tasks" },
  { label: "知识库", href: "/knowledge" },
  { label: "Wiki", href: "/wiki" },
  { label: "设置", href: "/settings" },
];
```

(If Plan 1 already added the "设置" entry, only add the "Wiki" entry.)

- [ ] **Step 7: Install react-markdown if missing**

```bash
cd frontend && npm list react-markdown 2>/dev/null | grep react-markdown || npm install react-markdown
```

- [ ] **Step 8: Run frontend build check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```
Expected: Build succeeds.

- [ ] **Step 9: Commit**

```bash
git add frontend/components/wiki/ frontend/app/wiki/ frontend/lib/api/wiki.ts frontend/lib/hooks/use-wiki.ts frontend/components/layout/sidebar.tsx
git commit -m "feat: add Wiki page, article tree, viewer, editor, and lint report"
```

---

### Task 7: Full Test Suite Check

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && LITELLM_MOCK=true pytest tests/ -v --tb=short -q 2>&1 | tail -30
```
Expected: All tests PASS

- [ ] **Step 2: Apply all pending migrations**

```bash
docker compose exec backend alembic upgrade head
```
Expected: `Running upgrade 0003 -> 0004, Add wiki_raw_sources and wiki_articles tables`

- [ ] **Step 3: Commit any fixes**

```bash
git add -A && git commit -m "fix: resolve wiki feature test failures"
```
