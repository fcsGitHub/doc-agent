# LLM Manual Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to create, manage, and activate LLM provider configurations at runtime through a UI, without restarting the server.

**Architecture:** Add a `llm_configs` DB table. Activating a config updates both DB and a module-level cache in `core/llm.py` via `update_active_config()` — no async changes needed. On startup, the app loads the active config from DB.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Pydantic v2, Next.js 14, TanStack Query

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/models/llm_config.py` | SQLAlchemy ORM model |
| Create | `backend/alembic/versions/0002_add_llm_configs.py` | DB migration |
| Modify | `backend/core/llm.py` | Add config cache + `update_active_config()` + startup loader |
| Create | `backend/schemas/llm_config.py` | Pydantic request/response schemas |
| Create | `backend/services/llm_config_service.py` | CRUD + activate logic |
| Create | `backend/api/settings.py` | HTTP endpoints |
| Modify | `backend/api/router.py` | Register settings router |
| Create | `backend/main.py` lifespan | Load active config on startup (if main.py exists) |
| Create | `backend/tests/models/test_llm_config.py` | Model tests |
| Create | `backend/tests/services/test_llm_config_service.py` | Service tests |
| Create | `backend/tests/api/test_settings.py` | API tests |
| Modify | `frontend/components/layout/sidebar.tsx` | Add Settings nav link |
| Create | `frontend/app/settings/page.tsx` | Settings page |
| Create | `frontend/components/settings/llm-config-card.tsx` | Config card (display + activate) |
| Create | `frontend/components/settings/llm-config-form.tsx` | Create/edit form |
| Create | `frontend/lib/api/settings.ts` | API client functions |
| Create | `frontend/lib/hooks/use-llm-config.ts` | TanStack Query hooks |

---

### Task 1: ORM Model + Migration

**Files:**
- Create: `backend/models/llm_config.py`
- Create: `backend/alembic/versions/0002_add_llm_configs.py`
- Modify: `backend/models/__init__.py`

- [ ] **Step 1: Write the failing model import test**

```python
# backend/tests/models/test_llm_config.py
import pytest
from models.llm_config import LLMConfig

def test_llm_config_table_name():
    assert LLMConfig.__tablename__ == "llm_configs"

def test_llm_config_fields():
    cols = {c.name for c in LLMConfig.__table__.columns}
    assert {"id", "name", "api_key", "api_base", "default_model",
            "review_model", "embed_model", "is_active", "created_at", "updated_at"} <= cols
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/models/test_llm_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'models.llm_config'`

- [ ] **Step 2: Create `backend/models/llm_config.py`**

```python
"""LLMConfig ORM model — persists LLM provider configurations."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDMixin


class LLMConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "llm_configs"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    api_base: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    default_model: Mapped[str] = mapped_column(String(200), nullable=False)
    review_model: Mapped[str] = mapped_column(String(200), nullable=False)
    embed_model: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
```

- [ ] **Step 3: Run test to verify it passes**

Run: `cd backend && LITELLM_MOCK=true pytest tests/models/test_llm_config.py -v`
Expected: PASS

- [ ] **Step 4: Create migration `backend/alembic/versions/0002_add_llm_configs.py`**

```python
"""Add llm_configs table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-06
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
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
```

Note: `sa.dialects.postgresql.UUID` needs `from sqlalchemy.dialects import postgresql` — fix import:

```python
from sqlalchemy.dialects import postgresql

# in upgrade():
sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
```

- [ ] **Step 5: Commit**

```bash
git add backend/models/llm_config.py backend/alembic/versions/0002_add_llm_configs.py backend/tests/models/test_llm_config.py
git commit -m "feat: add LLMConfig ORM model and migration"
```

---

### Task 2: Update `core/llm.py` — Config Cache

**Files:**
- Modify: `backend/core/llm.py`

The goal: keep `get_llm_client()` sync. Add `update_active_config(config: dict)` which resets the singleton with new settings. Add `load_active_config_from_db(db)` async for startup.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/core/test_llm.py (append to existing file)
from core.llm import update_active_config, get_llm_client

def test_update_active_config_resets_singleton():
    """After update_active_config, get_llm_client returns client with new model."""
    update_active_config({
        "api_key": "test-key",
        "api_base": "http://localhost:11434",
        "default_model": "ollama/llama3",
        "review_model": "ollama/llama3",
        "embed_model": "ollama/nomic-embed-text",
    })
    client = get_llm_client()
    assert client.default_model == "ollama/llama3"
    assert client.api_base == "http://localhost:11434"
    # Reset to avoid polluting other tests
    update_active_config({})
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/core/test_llm.py::test_update_active_config_resets_singleton -v`
Expected: FAIL with `ImportError: cannot import name 'update_active_config'`

- [ ] **Step 2: Modify `backend/core/llm.py` — add config cache**

Append after the existing `_default_client` declaration at line 131:

```python
# Module-level config override (set by LLMConfigService.activate())
_active_config: dict = {}


def update_active_config(config: dict) -> None:
    """Update the active LLM config cache and reset the singleton client.

    Called by LLMConfigService when a config is activated in the DB.
    config keys: api_key, api_base, default_model, review_model, embed_model.
    Pass empty dict {} to clear the override and fall back to env vars.
    """
    global _active_config, _default_client
    _active_config = config
    _default_client = None  # force rebuild on next get_llm_client() call


def get_llm_client() -> LLMClient:
    """Get or create module-level LLMClient instance.

    Uses _active_config if set (from DB), otherwise falls back to settings (env vars).
    """
    global _default_client
    if _default_client is None:
        if _active_config:
            _default_client = LLMClient(
                api_key=_active_config.get("api_key") or settings.llm_api_key,
                api_base=_active_config.get("api_base") or settings.llm_api_base,
                default_model=_active_config.get("default_model") or settings.llm_default_model,
                review_model=_active_config.get("review_model") or settings.llm_review_model,
            )
        else:
            _default_client = LLMClient()
    return _default_client


async def load_active_config_from_db(db: "AsyncSession") -> None:  # type: ignore[name-defined]
    """Load the active LLM config from DB on app startup.

    Called once during application lifespan startup.
    Safe to call even if no active config exists — falls back to env vars.
    """
    from sqlalchemy import select
    from models.llm_config import LLMConfig

    result = await db.execute(
        select(LLMConfig).where(LLMConfig.is_active.is_(True)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        update_active_config({
            "api_key": row.api_key,
            "api_base": row.api_base,
            "default_model": row.default_model,
            "review_model": row.review_model,
            "embed_model": row.embed_model,
        })
```

Also **remove** the old `get_llm_client` function (lines 134-139) since we're replacing it.

- [ ] **Step 3: Run test to verify it passes**

Run: `cd backend && LITELLM_MOCK=true pytest tests/core/test_llm.py -v`
Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add backend/core/llm.py backend/tests/core/test_llm.py
git commit -m "feat: add update_active_config and load_active_config_from_db to LLMClient"
```

---

### Task 3: Schemas + Service

**Files:**
- Create: `backend/schemas/llm_config.py`
- Create: `backend/services/llm_config_service.py`
- Create: `backend/tests/services/test_llm_config_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
# backend/tests/services/test_llm_config_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.llm_config_service import LLMConfigService
from models.llm_config import LLMConfig
import uuid

@pytest.fixture
def service():
    return LLMConfigService()

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    return db

@pytest.mark.asyncio
async def test_create_config(service, mock_db):
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())
    result = await service.create(
        mock_db,
        name="Test",
        api_key="sk-test",
        api_base="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        review_model="gpt-4o",
        embed_model="text-embedding-3-small",
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert isinstance(result, LLMConfig)
    assert result.name == "Test"

@pytest.mark.asyncio
async def test_activate_sets_is_active(service, mock_db):
    config_id = uuid.uuid4()
    mock_config = LLMConfig(
        id=config_id, name="Test", api_key="k", api_base="b",
        default_model="m", review_model="m", embed_model="e", is_active=False
    )
    # Mock get returning the config
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_config
    mock_db.execute.return_value = mock_result

    result = await service.activate(mock_db, str(config_id))
    assert result.is_active is True
    mock_db.commit.assert_called()
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/services/test_llm_config_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/schemas/llm_config.py`**

```python
"""Pydantic schemas for LLM configuration endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LLMConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    api_key: str = Field(default="")
    api_base: str = Field(default="https://api.openai.com/v1")
    default_model: str = Field(default="gpt-4o-mini")
    review_model: str = Field(default="gpt-4o")
    embed_model: str = Field(default="text-embedding-3-small")


class LLMConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: str | None = None
    api_base: str | None = None
    default_model: str | None = None
    review_model: str | None = None
    embed_model: str | None = None


class LLMConfigResponse(BaseModel):
    id: str
    name: str
    api_key_masked: str  # shows only last 4 chars
    api_base: str
    default_model: str
    review_model: str
    embed_model: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create `backend/services/llm_config_service.py`**

```python
"""Service for managing LLM provider configurations."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.llm import update_active_config
from models.llm_config import LLMConfig


class LLMConfigService:
    """CRUD and activation logic for LLMConfig records."""

    async def list_all(self, db: AsyncSession) -> Sequence[LLMConfig]:
        result = await db.execute(select(LLMConfig).order_by(LLMConfig.created_at.desc()))
        return result.scalars().all()

    async def get(self, db: AsyncSession, config_id: str) -> LLMConfig | None:
        result = await db.execute(
            select(LLMConfig).where(LLMConfig.id == uuid.UUID(config_id))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        name: str,
        api_key: str = "",
        api_base: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
        review_model: str = "gpt-4o",
        embed_model: str = "text-embedding-3-small",
    ) -> LLMConfig:
        config = LLMConfig(
            name=name,
            api_key=api_key,
            api_base=api_base,
            default_model=default_model,
            review_model=review_model,
            embed_model=embed_model,
            is_active=False,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        return config

    async def update(
        self,
        db: AsyncSession,
        config_id: str,
        **fields: str | None,
    ) -> LLMConfig | None:
        config = await self.get(db, config_id)
        if config is None:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(config, key, value)
        await db.commit()
        await db.refresh(config)
        if config.is_active:
            # Propagate changes to the in-memory client immediately
            update_active_config({
                "api_key": config.api_key,
                "api_base": config.api_base,
                "default_model": config.default_model,
                "review_model": config.review_model,
                "embed_model": config.embed_model,
            })
        return config

    async def delete(self, db: AsyncSession, config_id: str) -> bool:
        config = await self.get(db, config_id)
        if config is None:
            return False
        await db.delete(config)
        await db.commit()
        return True

    async def activate(self, db: AsyncSession, config_id: str) -> LLMConfig | None:
        """Set this config as active; deactivate all others."""
        config = await self.get(db, config_id)
        if config is None:
            return None
        # Deactivate all
        await db.execute(update(LLMConfig).values(is_active=False))
        # Activate target
        config.is_active = True
        await db.commit()
        await db.refresh(config)
        # Update in-memory LLM client immediately
        update_active_config({
            "api_key": config.api_key,
            "api_base": config.api_base,
            "default_model": config.default_model,
            "review_model": config.review_model,
            "embed_model": config.embed_model,
        })
        return config
```

- [ ] **Step 4: Run service tests to verify they pass**

Run: `cd backend && LITELLM_MOCK=true pytest tests/services/test_llm_config_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/llm_config.py backend/services/llm_config_service.py backend/tests/services/test_llm_config_service.py
git commit -m "feat: add LLMConfig schemas and service"
```

---

### Task 4: API Endpoints

**Files:**
- Create: `backend/api/settings.py`
- Modify: `backend/api/router.py`
- Create: `backend/tests/api/test_settings.py`

- [ ] **Step 1: Write the failing API tests**

```python
# backend/tests/api/test_settings.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

@pytest.fixture
def mock_service():
    from services.llm_config_service import LLMConfigService
    svc = MagicMock(spec=LLMConfigService)
    svc.list_all = AsyncMock(return_value=[])
    return svc

@pytest.mark.asyncio
async def test_list_configs_empty(mock_service):
    with patch("api.settings._service", mock_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/settings/llm")
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_create_config(mock_service):
    from models.llm_config import LLMConfig
    new_config = LLMConfig(
        id=uuid.uuid4(), name="Test", api_key="sk-test",
        api_base="https://api.openai.com/v1",
        default_model="gpt-4o-mini", review_model="gpt-4o",
        embed_model="text-embedding-3-small", is_active=False,
    )
    import datetime
    new_config.created_at = datetime.datetime.now()
    new_config.updated_at = datetime.datetime.now()
    mock_service.create = AsyncMock(return_value=new_config)
    with patch("api.settings._service", mock_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/settings/llm", json={
                "name": "Test",
                "api_key": "sk-test",
                "api_base": "https://api.openai.com/v1",
                "default_model": "gpt-4o-mini",
                "review_model": "gpt-4o",
                "embed_model": "text-embedding-3-small",
            })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test"
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/api/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.settings'`

- [ ] **Step 2: Create `backend/api/settings.py`**

```python
"""FastAPI router for LLM configuration management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.llm_config import LLMConfigCreate, LLMConfigResponse, LLMConfigUpdate
from services.llm_config_service import LLMConfigService

router = APIRouter(prefix="/settings", tags=["settings"])
_service = LLMConfigService()


def _to_response(config: object) -> LLMConfigResponse:
    api_key = str(getattr(config, "api_key", "") or "")
    masked = f"...{api_key[-4:]}" if len(api_key) >= 4 else "****"
    return LLMConfigResponse(
        id=str(getattr(config, "id")),
        name=str(getattr(config, "name")),
        api_key_masked=masked,
        api_base=str(getattr(config, "api_base")),
        default_model=str(getattr(config, "default_model")),
        review_model=str(getattr(config, "review_model")),
        embed_model=str(getattr(config, "embed_model")),
        is_active=bool(getattr(config, "is_active")),
        created_at=getattr(config, "created_at"),
        updated_at=getattr(config, "updated_at"),
    )


@router.get("/llm", response_model=list[LLMConfigResponse])
async def list_configs(db: AsyncSession = Depends(get_db)) -> list[LLMConfigResponse]:
    configs = await _service.list_all(db)
    return [_to_response(c) for c in configs]


@router.post("/llm", status_code=201, response_model=LLMConfigResponse)
async def create_config(
    body: LLMConfigCreate, db: AsyncSession = Depends(get_db)
) -> LLMConfigResponse:
    config = await _service.create(
        db,
        name=body.name,
        api_key=body.api_key,
        api_base=body.api_base,
        default_model=body.default_model,
        review_model=body.review_model,
        embed_model=body.embed_model,
    )
    return _to_response(config)


@router.put("/llm/{config_id}", response_model=LLMConfigResponse)
async def update_config(
    config_id: str, body: LLMConfigUpdate, db: AsyncSession = Depends(get_db)
) -> LLMConfigResponse:
    config = await _service.update(
        db, config_id,
        name=body.name, api_key=body.api_key, api_base=body.api_base,
        default_model=body.default_model, review_model=body.review_model,
        embed_model=body.embed_model,
    )
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    return _to_response(config)


@router.delete("/llm/{config_id}", status_code=204)
async def delete_config(config_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    deleted = await _service.delete(db, config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    return Response(status_code=204)


@router.post("/llm/{config_id}/activate", response_model=LLMConfigResponse)
async def activate_config(
    config_id: str, db: AsyncSession = Depends(get_db)
) -> LLMConfigResponse:
    config = await _service.activate(db, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    return _to_response(config)
```

- [ ] **Step 3: Modify `backend/api/router.py` — register settings router**

Add after the last import line and after the last `include_router` call:

```python
# In imports section add:
from api.settings import router as settings_router

# In router.include_router calls add:
router.include_router(settings_router)
```

- [ ] **Step 4: Run API tests**

Run: `cd backend && LITELLM_MOCK=true pytest tests/api/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/settings.py backend/api/router.py backend/tests/api/test_settings.py
git commit -m "feat: add LLM config API endpoints"
```

---

### Task 5: Startup Config Loader

**Files:**
- Modify: `backend/main.py` (find or check if it exists with `ls backend/main.py`)

- [ ] **Step 1: Check main.py structure**

Run: `head -40 backend/main.py`

- [ ] **Step 2: Add LLM config loader to existing lifespan in `backend/main.py`**

`main.py` already has a `lifespan` function. Add the loader call inside the existing `async with async_session_maker() as db:` block, right after the template seeding block (before the `yield`):

```python
# Add import at top of main.py:
from core.llm import load_active_config_from_db

# Inside the lifespan function, add after the template seeding try/except block:
    try:
        from core.database import async_session_maker
        async with async_session_maker() as db:
            await load_active_config_from_db(db)
    except Exception as exc:
        print(f"[llm-config] Failed to load active config: {exc}")
```

The full updated lifespan body should look like:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: seed built-in templates and load LLM config on startup."""
    try:
        from core.database import async_session_maker
        from services.template_service import TemplateService

        async with async_session_maker() as db:
            svc = TemplateService()
            count = await svc.seed_builtin_templates(db)
            if count > 0:
                print(f"[seed] Inserted {count} built-in template(s).")
            else:
                print("[seed] Built-in templates already exist, skipping.")
    except Exception as exc:
        print(f"[seed] Template seeding skipped: {exc}")

    try:
        from core.database import async_session_maker
        from core.llm import load_active_config_from_db

        async with async_session_maker() as db:
            await load_active_config_from_db(db)
            print("[llm-config] Active LLM config loaded from DB.")
    except Exception as exc:
        print(f"[llm-config] Failed to load active config (using env vars): {exc}")

    yield
```

- [ ] **Step 3: Run existing tests to ensure nothing is broken**

Run: `cd backend && LITELLM_MOCK=true pytest tests/ -v --tb=short -q`
Expected: all existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: load active LLM config from DB on startup"
```

---

### Task 6: Frontend — API Client + Hooks

**Files:**
- Create: `frontend/lib/api/settings.ts`
- Create: `frontend/lib/hooks/use-llm-config.ts`

- [ ] **Step 1: Create `frontend/lib/api/settings.ts`**

```typescript
import { apiFetch, API_BASE } from "@/lib/api";

export interface LLMConfig {
  id: string;
  name: string;
  api_key_masked: string;
  api_base: string;
  default_model: string;
  review_model: string;
  embed_model: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMConfigCreate {
  name: string;
  api_key?: string;
  api_base?: string;
  default_model?: string;
  review_model?: string;
  embed_model?: string;
}

export interface LLMConfigUpdate {
  name?: string;
  api_key?: string;
  api_base?: string;
  default_model?: string;
  review_model?: string;
  embed_model?: string;
}

export const settingsApi = {
  listConfigs: () => apiFetch<LLMConfig[]>("/api/v1/settings/llm"),

  createConfig: (data: LLMConfigCreate) =>
    apiFetch<LLMConfig>("/api/v1/settings/llm", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateConfig: (id: string, data: LLMConfigUpdate) =>
    apiFetch<LLMConfig>(`/api/v1/settings/llm/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteConfig: (id: string) =>
    fetch(`${API_BASE}/api/v1/settings/llm/${id}`, { method: "DELETE" }),

  activateConfig: (id: string) =>
    apiFetch<LLMConfig>(`/api/v1/settings/llm/${id}/activate`, {
      method: "POST",
    }),
};
```

- [ ] **Step 2: Create `frontend/lib/hooks/use-llm-config.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { settingsApi, LLMConfigCreate, LLMConfigUpdate } from "@/lib/api/settings";

export const LLM_CONFIG_KEY = ["llm-configs"] as const;

export function useLLMConfigs() {
  return useQuery({
    queryKey: LLM_CONFIG_KEY,
    queryFn: settingsApi.listConfigs,
  });
}

export function useCreateLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LLMConfigCreate) => settingsApi.createConfig(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}

export function useUpdateLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LLMConfigUpdate }) =>
      settingsApi.updateConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}

export function useDeleteLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => settingsApi.deleteConfig(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}

export function useActivateLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => settingsApi.activateConfig(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/settings.ts frontend/lib/hooks/use-llm-config.ts
git commit -m "feat: add LLM config API client and React Query hooks"
```

---

### Task 7: Frontend — Settings Page UI

**Files:**
- Create: `frontend/components/settings/llm-config-form.tsx`
- Create: `frontend/components/settings/llm-config-card.tsx`
- Create: `frontend/app/settings/page.tsx`
- Modify: `frontend/components/layout/sidebar.tsx`

- [ ] **Step 1: Create `frontend/components/settings/llm-config-form.tsx`**

```tsx
"use client";

import { useState } from "react";
import { LLMConfigCreate } from "@/lib/api/settings";

interface Props {
  onSubmit: (data: LLMConfigCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
  initialValues?: Partial<LLMConfigCreate>;
}

export function LLMConfigForm({ onSubmit, onCancel, isLoading, initialValues }: Props) {
  const [form, setForm] = useState<LLMConfigCreate>({
    name: initialValues?.name ?? "",
    api_key: initialValues?.api_key ?? "",
    api_base: initialValues?.api_base ?? "https://api.openai.com/v1",
    default_model: initialValues?.default_model ?? "gpt-4o-mini",
    review_model: initialValues?.review_model ?? "gpt-4o",
    embed_model: initialValues?.embed_model ?? "text-embedding-3-small",
  });

  const fields: { key: keyof LLMConfigCreate; label: string; type?: string }[] = [
    { key: "name", label: "配置名称" },
    { key: "api_key", label: "API Key", type: "password" },
    { key: "api_base", label: "API Base URL" },
    { key: "default_model", label: "生成模型" },
    { key: "review_model", label: "审阅模型" },
    { key: "embed_model", label: "嵌入模型" },
  ];

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit(form); }}
      className="space-y-4"
    >
      {fields.map(({ key, label, type }) => (
        <div key={key}>
          <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
          <input
            type={type ?? "text"}
            value={form[key] ?? ""}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required={key === "name"}
          />
        </div>
      ))}
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? "保存中..." : "保存"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="border border-gray-300 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50"
        >
          取消
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Create `frontend/components/settings/llm-config-card.tsx`**

```tsx
"use client";

import { useState } from "react";
import { LLMConfig } from "@/lib/api/settings";
import { useActivateLLMConfig, useDeleteLLMConfig } from "@/lib/hooks/use-llm-config";

interface Props {
  config: LLMConfig;
}

export function LLMConfigCard({ config }: Props) {
  const [showKey, setShowKey] = useState(false);
  const activate = useActivateLLMConfig();
  const remove = useDeleteLLMConfig();

  return (
    <div className={`rounded-lg border p-4 ${config.is_active ? "border-blue-500 bg-blue-50" : "border-gray-200 bg-white"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-800">{config.name}</h3>
          {config.is_active && (
            <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">当前使用</span>
          )}
        </div>
        <div className="flex gap-2">
          {!config.is_active && (
            <button
              onClick={() => activate.mutate(config.id)}
              disabled={activate.isPending}
              className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              激活
            </button>
          )}
          <button
            onClick={() => remove.mutate(config.id)}
            disabled={remove.isPending}
            className="text-sm border border-red-300 text-red-600 px-3 py-1 rounded hover:bg-red-50 disabled:opacity-50"
          >
            删除
          </button>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <dt className="text-gray-500">API Base</dt>
        <dd className="text-gray-800 truncate">{config.api_base}</dd>
        <dt className="text-gray-500">生成模型</dt>
        <dd className="text-gray-800">{config.default_model}</dd>
        <dt className="text-gray-500">审阅模型</dt>
        <dd className="text-gray-800">{config.review_model}</dd>
        <dt className="text-gray-500">嵌入模型</dt>
        <dd className="text-gray-800">{config.embed_model}</dd>
        <dt className="text-gray-500">API Key</dt>
        <dd className="text-gray-800">
          {showKey ? config.api_key_masked : "••••••••"}
          <button
            onClick={() => setShowKey((v) => !v)}
            className="ml-2 text-xs text-blue-600 hover:underline"
          >
            {showKey ? "隐藏" : "显示"}
          </button>
        </dd>
      </dl>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/app/settings/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useLLMConfigs, useCreateLLMConfig } from "@/lib/hooks/use-llm-config";
import { LLMConfigCard } from "@/components/settings/llm-config-card";
import { LLMConfigForm } from "@/components/settings/llm-config-form";

export default function SettingsPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: configs, isLoading } = useLLMConfigs();
  const createConfig = useCreateLLMConfig();

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">LLM 配置</h1>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700"
        >
          + 新增配置
        </button>
      </div>

      {showForm && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="font-semibold text-gray-700 mb-3">新增 LLM 配置</h2>
          <LLMConfigForm
            onSubmit={(data) => {
              createConfig.mutate(data, { onSuccess: () => setShowForm(false) });
            }}
            onCancel={() => setShowForm(false)}
            isLoading={createConfig.isPending}
          />
        </div>
      )}

      {isLoading && <p className="text-gray-500 text-sm">加载中...</p>}

      {configs && configs.length === 0 && !showForm && (
        <p className="text-gray-500 text-sm">暂无配置，点击「新增配置」添加。</p>
      )}

      <div className="space-y-3">
        {configs?.map((c) => <LLMConfigCard key={c.id} config={c} />)}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Add Settings nav link to sidebar**

In `frontend/components/layout/sidebar.tsx`, add `{ label: "设置", href: "/settings" }` to the `NAV_ITEMS` array:

```typescript
const NAV_ITEMS = [
  { label: "任务列表", href: "/" },
  { label: "工作台", href: "/tasks" },
  { label: "知识库", href: "/knowledge" },
  { label: "设置", href: "/settings" },
];
```

- [ ] **Step 5: Run frontend build check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```
Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/settings/ frontend/app/settings/ frontend/lib/api/settings.ts frontend/lib/hooks/use-llm-config.ts frontend/components/layout/sidebar.tsx
git commit -m "feat: add LLM config settings page and components"
```

---

### Task 8: Run Full Backend Test Suite

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && LITELLM_MOCK=true pytest tests/ -v --tb=short -q 2>&1 | tail -30
```
Expected: All tests pass.

- [ ] **Step 2: Apply migration against local DB (if running Docker)**

```bash
docker compose exec backend alembic upgrade head
```
Expected: `Running upgrade 0001 -> 0002, Add llm_configs table`

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: resolve any test failures from LLM config feature"
```
