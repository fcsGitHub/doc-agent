"""Checkpoint configuration for LangGraph Postgres persistence."""

from __future__ import annotations

from typing import Any

from config import settings

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # pyright: ignore[reportMissingImports]
except ImportError:  # pragma: no cover - optional dependency in local env
    AsyncPostgresSaver = None  # type: ignore[assignment]


def get_checkpoint_database_url(database_url: str | None = None) -> str:
    """Return Postgres URL compatible with langgraph-checkpoint-postgres."""

    url = database_url or settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def build_async_postgres_saver(database_url: str | None = None) -> Any:
    """Create AsyncPostgresSaver using project DATABASE_URL settings."""

    if AsyncPostgresSaver is None:
        raise RuntimeError(
            "langgraph-checkpoint-postgres is not installed; "
            "install it to enable graph checkpointing"
        )
    return AsyncPostgresSaver.from_conn_string(
        get_checkpoint_database_url(database_url)
    )
