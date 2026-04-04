"""Initial schema with all 19 tables

Revision ID: 0001
Revises:
Create Date: 2026-03-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------- Enum types ----------
task_status_enum = postgresql.ENUM(
    "created",
    "parsing",
    "extracting",
    "planning",
    "awaiting_approval",
    "generating",
    "reviewing",
    "revising",
    "approved",
    "exporting",
    "completed",
    "failed",
    name="taskstatus",
    create_type=False,
)

section_status_enum = postgresql.ENUM(
    "draft",
    "generating",
    "generated",
    "revising",
    "approved",
    name="sectionstatus",
    create_type=False,
)

review_severity_enum = postgresql.ENUM(
    "critical",
    "major",
    "minor",
    name="reviewseverity",
    create_type=False,
)

review_status_enum = postgresql.ENUM(
    "pass",
    "fail",
    "pending",
    name="reviewstatus",
    create_type=False,
)


def upgrade() -> None:
    # ---------- Create enum types ----------
    task_status_enum.create(op.get_bind(), checkfirst=True)
    section_status_enum.create(op.get_bind(), checkfirst=True)
    review_severity_enum.create(op.get_bind(), checkfirst=True)
    review_status_enum.create(op.get_bind(), checkfirst=True)

    # ---------- Enable pgvector extension ----------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ---------- 1. tasks ----------
    op.create_table(
        "tasks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("doc_type", sa.String(100), nullable=False, server_default="report"),
        sa.Column("status", task_status_enum, nullable=False, server_default="created"),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("progress_pct", sa.Integer, server_default="0"),
        sa.Column("progress_message", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 2. task_configs ----------
    op.create_table(
        "task_configs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_id", UUID(as_uuid=True), nullable=True),
        sa.Column("outline_approved", sa.Boolean, server_default="false"),
        sa.Column("final_approved", sa.Boolean, server_default="false"),
        sa.Column("revision_round", sa.Integer, server_default="0"),
        sa.Column("max_revision_rounds", sa.Integer, server_default="3"),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 3. source_documents ----------
    op.create_table(
        "source_documents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 4. parsed_documents ----------
    op.create_table(
        "parsed_documents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "source_document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("structure", JSONB, server_default="[]"),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 5. sections ----------
    op.create_table(
        "sections",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sections.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("level", sa.Integer, nullable=False, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("target_word_count", sa.Integer, server_default="500"),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "status", section_status_enum, nullable=False, server_default="draft"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 6. section_versions ----------
    op.create_table(
        "section_versions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "section_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("word_count", sa.Integer, server_default="0"),
        sa.Column("change_source", sa.String(100), server_default="generation"),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 7. review_results ----------
    op.create_table(
        "review_results",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("reviewer_name", sa.String(100), nullable=False),
        sa.Column(
            "status", review_status_enum, nullable=False, server_default="pending"
        ),
        sa.Column("score", sa.Integer, server_default="0"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 8. review_issues ----------
    op.create_table(
        "review_issues",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "review_result_id",
            UUID(as_uuid=True),
            sa.ForeignKey("review_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "severity", review_severity_enum, nullable=False, server_default="minor"
        ),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("location_excerpt", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("suggestion", sa.Text, nullable=True),
        sa.Column("requires_human", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 9. evidence_references ----------
    op.create_table(
        "evidence_references",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "section_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("excerpt", sa.Text, nullable=True),
        sa.Column("relevance_score", sa.Float, server_default="0.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 10. skill_executions ----------
    op.create_table(
        "skill_executions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("input_data", JSONB, server_default="{}"),
        sa.Column("output_data", JSONB, server_default="{}"),
        sa.Column("tokens_used", sa.Integer, server_default="0"),
        sa.Column("execution_time_ms", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 11. templates ----------
    op.create_table(
        "templates",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("doc_type", sa.String(100), nullable=False),
        sa.Column("outline_structure", JSONB, server_default="[]"),
        sa.Column("rules", JSONB, server_default="[]"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 12. rules ----------
    op.create_table(
        "rules",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 13. terminology_entries ----------
    op.create_table(
        "terminology_entries",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("term", sa.String(200), nullable=False),
        sa.Column("definition", sa.Text, nullable=True),
        sa.Column("context", sa.String(100), nullable=True),
        sa.Column("is_preferred", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 14. knowledge_chunks (with pgvector) ----------
    op.create_table(
        "knowledge_chunks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("source_document_id", UUID(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("chunk_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )
    # Add vector column via raw SQL (pgvector type not natively in SA)
    op.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding vector(1536)")
    # IVFFlat index for vector similarity search
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding ON knowledge_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # ---------- 15. user_comments ----------
    op.create_table(
        "user_comments",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sections.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 16. export_artifacts ----------
    op.create_table(
        "export_artifacts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(20), nullable=False, server_default="docx"),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 17. audit_events ----------
    op.create_table(
        "audit_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(200), nullable=False),
        sa.Column("details", JSONB, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 18. review_rounds ----------
    op.create_table(
        "review_rounds",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "overall_status", sa.String(50), nullable=False, server_default="pending"
        ),
        sa.Column("overall_score", sa.Integer, server_default="0"),
        sa.Column("total_issues", sa.Integer, server_default="0"),
        sa.Column("critical_count", sa.Integer, server_default="0"),
        sa.Column("major_count", sa.Integer, server_default="0"),
        sa.Column("minor_count", sa.Integer, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- 19. approvals ----------
    op.create_table(
        "approvals",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("approval_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
    )

    # ---------- Indexes ----------
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])
    op.create_index("ix_sections_task_id", "sections", ["task_id"])
    op.create_index("ix_sections_order", "sections", ["task_id", "order_index"])
    op.create_index(
        "ix_section_versions_section_id", "section_versions", ["section_id"]
    )
    op.create_index("ix_review_results_task_id", "review_results", ["task_id"])
    op.create_index(
        "ix_review_issues_review_result_id", "review_issues", ["review_result_id"]
    )
    op.create_index("ix_skill_executions_task_id", "skill_executions", ["task_id"])
    op.create_index("ix_audit_events_task_id", "audit_events", ["task_id"])
    op.create_index(
        "ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"]
    )
    op.create_index(
        "ix_knowledge_chunks_source", "knowledge_chunks", ["source_document_id"]
    )
    op.create_index("ix_source_documents_task_id", "source_documents", ["task_id"])
    op.create_index("ix_parsed_documents_task_id", "parsed_documents", ["task_id"])
    op.create_index("ix_review_rounds_task_id", "review_rounds", ["task_id"])
    op.create_index("ix_approvals_task_id", "approvals", ["task_id"])


def downgrade() -> None:
    # ---------- Drop indexes ----------
    op.drop_index("ix_approvals_task_id")
    op.drop_index("ix_review_rounds_task_id")
    op.drop_index("ix_parsed_documents_task_id")
    op.drop_index("ix_source_documents_task_id")
    op.drop_index("ix_knowledge_chunks_source")
    op.drop_index("ix_audit_events_entity")
    op.drop_index("ix_audit_events_task_id")
    op.drop_index("ix_skill_executions_task_id")
    op.drop_index("ix_review_issues_review_result_id")
    op.drop_index("ix_review_results_task_id")
    op.drop_index("ix_section_versions_section_id")
    op.drop_index("ix_sections_order")
    op.drop_index("ix_sections_task_id")
    op.drop_index("ix_tasks_created_at")
    op.drop_index("ix_tasks_status")

    # Drop vector index
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding")

    # ---------- Drop tables (reverse order of creation) ----------
    op.drop_table("approvals")
    op.drop_table("review_rounds")
    op.drop_table("audit_events")
    op.drop_table("export_artifacts")
    op.drop_table("user_comments")
    op.drop_table("knowledge_chunks")
    op.drop_table("terminology_entries")
    op.drop_table("rules")
    op.drop_table("templates")
    op.drop_table("skill_executions")
    op.drop_table("evidence_references")
    op.drop_table("review_issues")
    op.drop_table("review_results")
    op.drop_table("section_versions")
    op.drop_table("sections")
    op.drop_table("parsed_documents")
    op.drop_table("source_documents")
    op.drop_table("task_configs")
    op.drop_table("tasks")

    # ---------- Drop enums ----------
    review_status_enum.drop(op.get_bind(), checkfirst=True)
    review_severity_enum.drop(op.get_bind(), checkfirst=True)
    section_status_enum.drop(op.get_bind(), checkfirst=True)
    task_status_enum.drop(op.get_bind(), checkfirst=True)

    # ---------- Drop extension ----------
    op.execute("DROP EXTENSION IF EXISTS vector")
