"""Tests for WikiRawSource and WikiArticle ORM models."""

from models.wiki import WikiArticle, WikiRawSource


def test_wiki_raw_source_table():
    assert WikiRawSource.__tablename__ == "wiki_raw_sources"
    cols = {c.name for c in WikiRawSource.__table__.columns}
    assert {"id", "filename", "content", "compiled", "uploaded_at"} <= cols


def test_wiki_article_table():
    assert WikiArticle.__tablename__ == "wiki_articles"
    cols = {c.name for c in WikiArticle.__table__.columns}
    assert {"id", "title", "category", "content", "summary",
            "backlinks", "source_doc_ids", "health_score", "created_at", "updated_at"} <= cols


def test_wiki_raw_source_instantiation():
    source = WikiRawSource(filename="test.md", content="# Hello", compiled=False)
    assert source.filename == "test.md"
    assert source.compiled is False


def test_wiki_article_instantiation():
    article = WikiArticle(
        title="ISO 9001",
        category="standards",
        content="## ISO 9001\nQuality management.",
        summary="Quality standard",
        backlinks=[],
        source_doc_ids=[],
    )
    assert article.title == "ISO 9001"
    assert article.category == "standards"
