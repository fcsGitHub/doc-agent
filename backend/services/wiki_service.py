"""Wiki service — CRUD for raw sources and wiki articles."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.wiki import WikiArticle, WikiRawSource


class WikiService:
    """CRUD operations for wiki sources and articles."""

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
