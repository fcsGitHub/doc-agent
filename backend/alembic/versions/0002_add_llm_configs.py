"""Add llm_configs table
Revision ID: 0002
Revises: 0001
Create Date: 2026-04-06
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "llm_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("api_key", sa.String(500), nullable=False, server_default=""),
        sa.Column("api_base", sa.String(500), nullable=False, server_default=""),
        sa.Column("default_model", sa.String(200), nullable=False),
        sa.Column("review_model", sa.String(200), nullable=False),
        sa.Column("embed_model", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_llm_configs_is_active", "llm_configs", ["is_active"])

def downgrade() -> None:
    op.drop_index("ix_llm_configs_is_active", table_name="llm_configs")
    op.drop_table("llm_configs")
