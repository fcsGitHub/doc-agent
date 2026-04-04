"""Test that the migration file is valid and contains expected tables and enums."""

import ast
import pytest
from pathlib import Path


MIGRATION_DIR = Path(__file__).parent.parent / "alembic" / "versions"


def _get_migration_files() -> list[Path]:
    """Return migration files, excluding __init__.py."""
    return [f for f in MIGRATION_DIR.glob("*.py") if not f.name.startswith("__")]


def _read_first_migration() -> str:
    """Read content of the first (initial) migration file."""
    files = _get_migration_files()
    assert files, "No migration files found in alembic/versions/"
    return files[0].read_text(encoding="utf-8")


# ---------- File existence ----------


def test_migration_file_exists():
    """Verify the initial migration file exists."""
    actual_migrations = _get_migration_files()
    assert len(actual_migrations) >= 1, "At least one migration file must exist"


def test_migration_file_is_valid_python():
    """Verify migration file is syntactically valid Python."""
    content = _read_first_migration()
    try:
        ast.parse(content)
    except SyntaxError as e:
        pytest.fail(f"Migration file has syntax error: {e}")


# ---------- Required tables ----------


def test_migration_contains_required_tables():
    """Verify migration file references all required tables."""
    content = _read_first_migration()

    required_tables = [
        "tasks",
        "task_configs",
        "source_documents",
        "parsed_documents",
        "sections",
        "section_versions",
        "review_results",
        "review_issues",
        "evidence_references",
        "skill_executions",
        "templates",
        "rules",
        "terminology_entries",
        "knowledge_chunks",
        "user_comments",
        "export_artifacts",
        "audit_events",
        "review_rounds",
        "approvals",
    ]

    for table in required_tables:
        assert table in content, f"Table '{table}' not found in migration"


def test_migration_has_19_create_table_calls():
    """Verify exactly 19 tables are created."""
    content = _read_first_migration()
    create_count = content.count("op.create_table(")
    assert create_count == 19, f"Expected 19 create_table calls, got {create_count}"


# ---------- pgvector ----------


def test_migration_contains_vector_extension():
    """Verify pgvector extension is enabled."""
    content = _read_first_migration()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in content, (
        "pgvector extension creation not found in migration"
    )


def test_migration_has_vector_column():
    """Verify vector(1536) column exists for embeddings."""
    content = _read_first_migration()
    assert "vector(1536)" in content, "vector(1536) column not found in migration"


def test_migration_has_ivfflat_index():
    """Verify IVFFlat index for vector similarity search."""
    content = _read_first_migration()
    assert "ivfflat" in content, "IVFFlat index not found in migration"
    assert "vector_cosine_ops" in content, "vector_cosine_ops not found in migration"


# ---------- Enum values ----------


def test_task_status_enum_values():
    """Verify task status enum has all required values."""
    content = _read_first_migration()

    required_statuses = [
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
    ]
    for status in required_statuses:
        assert f'"{status}"' in content, (
            f"Task status '{status}' not found in migration"
        )


def test_section_status_enum_values():
    """Verify section status enum has all required values."""
    content = _read_first_migration()

    required_statuses = ["draft", "generating", "generated", "revising", "approved"]
    for status in required_statuses:
        assert f'"{status}"' in content, (
            f"Section status '{status}' not found in migration"
        )


def test_review_severity_enum_values():
    """Verify review severity enum has all required values."""
    content = _read_first_migration()

    required_severities = ["critical", "major", "minor"]
    for severity in required_severities:
        assert f'"{severity}"' in content, (
            f"Review severity '{severity}' not found in migration"
        )


def test_review_status_enum_values():
    """Verify review status enum has all required values."""
    content = _read_first_migration()

    required_statuses = ["pass", "fail", "pending"]
    for status in required_statuses:
        assert f'"{status}"' in content, (
            f"Review status '{status}' not found in migration"
        )


# ---------- Key constraints ----------


def test_migration_has_uuid_primary_keys():
    """Verify UUID primary keys are used."""
    content = _read_first_migration()
    assert "gen_random_uuid()" in content, "gen_random_uuid() not found"
    assert "UUID(as_uuid=True)" in content, "UUID type not found"


def test_migration_has_cascade_deletes():
    """Verify CASCADE delete constraints exist."""
    content = _read_first_migration()
    assert 'ondelete="CASCADE"' in content, "CASCADE delete not found"


def test_migration_has_timezone_timestamps():
    """Verify timestamps use timezone=True."""
    content = _read_first_migration()
    assert "DateTime(timezone=True)" in content, "Timezone-aware timestamps not found"


def test_migration_has_jsonb_columns():
    """Verify JSONB columns are used for flexible data."""
    content = _read_first_migration()
    assert "JSONB" in content, "JSONB column type not found"


# ---------- Downgrade ----------


def test_migration_has_downgrade():
    """Verify downgrade function drops all tables."""
    content = _read_first_migration()

    required_drops = [
        'op.drop_table("tasks")',
        'op.drop_table("sections")',
        'op.drop_table("knowledge_chunks")',
        'op.drop_table("audit_events")',
        'op.drop_table("approvals")',
        'op.drop_table("review_rounds")',
    ]
    for drop in required_drops:
        assert drop in content, f"Downgrade missing: {drop}"


def test_migration_downgrade_drops_enums():
    """Verify downgrade drops enum types."""
    content = _read_first_migration()
    assert "task_status_enum.drop" in content, (
        "Downgrade does not drop task_status_enum"
    )
    assert "section_status_enum.drop" in content, (
        "Downgrade does not drop section_status_enum"
    )
    assert "review_severity_enum.drop" in content, (
        "Downgrade does not drop review_severity_enum"
    )
    assert "review_status_enum.drop" in content, (
        "Downgrade does not drop review_status_enum"
    )


def test_migration_downgrade_drops_extension():
    """Verify downgrade drops pgvector extension."""
    content = _read_first_migration()
    assert "DROP EXTENSION IF EXISTS vector" in content, (
        "Downgrade does not drop vector extension"
    )
