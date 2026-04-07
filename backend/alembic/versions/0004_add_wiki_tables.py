"""Add wiki_raw_sources and wiki_articles tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-07
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
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("compiled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "wiki_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("category", sa.String(200), nullable=False, server_default="general"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("summary", sa.String(1000), nullable=False, server_default=""),
        sa.Column("backlinks", postgresql.JSONB, server_default="[]"),
        sa.Column("source_doc_ids", postgresql.JSONB, server_default="[]"),
        sa.Column("health_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_wiki_articles_category", "wiki_articles", ["category"])


def downgrade() -> None:
    op.drop_index("ix_wiki_articles_category", table_name="wiki_articles")
    op.drop_table("wiki_articles")
    op.drop_table("wiki_raw_sources")
