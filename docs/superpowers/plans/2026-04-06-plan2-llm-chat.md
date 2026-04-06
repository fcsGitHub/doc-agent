# LLM Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** Plan 1 (LLM Config) must be completed first.

**Goal:** Add a two-level conversational interface: task-level sidebar chat for document-wide instructions, and section-level AI edit modal for targeted rewrites. Chat can modify documents and inject review standards.

**Architecture:** `ChatSkill` in `skills/chat.py` receives conversation history + task context (sections, reviews) and resolves two intents: document-edit (calls `RewriteSkill`) and standard-specification (updates `chat_session.review_criteria`). SSE streaming reuses existing `api/sse.py` infrastructure. `BaseReviewer._build_prompt` is extended to accept optional extra criteria.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, SSE, Next.js 14, TanStack Query

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `backend/models/chat.py` | ChatSession + ChatMessage ORM models |
| Create | `backend/alembic/versions/0003_add_chat_tables.py` | DB migration |
| Create | `backend/schemas/chat.py` | Pydantic request/response schemas |
| Create | `backend/services/chat_service.py` | Session/message CRUD + context assembly |
| Create | `backend/skills/chat.py` | Chat skill — intent resolution + LLM call |
| Create | `backend/api/chat.py` | HTTP + SSE endpoints |
| Modify | `backend/api/router.py` | Register chat router |
| Modify | `backend/review/base.py` | Accept `extra_criteria` in `_build_prompt` |
| Create | `backend/tests/models/test_chat.py` | Model tests |
| Create | `backend/tests/services/test_chat_service.py` | Service tests |
| Create | `backend/tests/skills/test_chat.py` | Skill tests |
| Create | `backend/tests/api/test_chat.py` | API tests |
| Create | `frontend/components/chat/chat-sidebar.tsx` | Collapsible task-level chat panel |
| Create | `frontend/components/chat/chat-message.tsx` | Single message bubble |
| Create | `frontend/components/chat/section-edit-modal.tsx` | Section-scoped AI edit dialog |
| Create | `frontend/lib/api/chat.ts` | API client + SSE reader |
| Create | `frontend/lib/hooks/use-chat.ts` | TanStack Query hooks |
| Modify | `frontend/app/tasks/[id]/page.tsx` | Integrate sidebar + section button |

---

### Task 1: ORM Models + Migration

**Files:**
- Create: `backend/models/chat.py`
- Create: `backend/alembic/versions/0003_add_chat_tables.py`

- [ ] **Step 1: Write failing model test**

```python
# backend/tests/models/test_chat.py
import pytest
from models.chat import ChatSession, ChatMessage

def test_chat_session_table():
    assert ChatSession.__tablename__ == "chat_sessions"
    cols = {c.name for c in ChatSession.__table__.columns}
    assert {"id", "task_id", "scope", "section_id", "review_criteria", "created_at"} <= cols

def test_chat_message_table():
    assert ChatMessage.__tablename__ == "chat_messages"
    cols = {c.name for c in ChatMessage.__table__.columns}
    assert {"id", "session_id", "role", "content", "action", "created_at"} <= cols
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/models/test_chat.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/models/chat.py`**

```python
"""ChatSession and ChatMessage ORM models."""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, UUIDMixin

ChatScopeEnum = Enum("task", "section", name="chatscopeenum", create_constraint=False)
ChatRoleEnum = Enum("user", "assistant", name="chatroleenum", create_constraint=False)


class ChatSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_sessions"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(ChatScopeEnum, nullable=False, server_default="task")
    section_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    review_criteria: Mapped[list] = mapped_column(JSONB, server_default="[]")


class ChatMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(ChatRoleEnum, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 3: Run model test**

Run: `cd backend && LITELLM_MOCK=true pytest tests/models/test_chat.py -v`
Expected: PASS

- [ ] **Step 4: Create migration `backend/alembic/versions/0003_add_chat_tables.py`**

```python
"""Add chat_sessions and chat_messages tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-06
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE chatscopeenum AS ENUM ('task', 'section')")
    op.execute("CREATE TYPE chatroleenum AS ENUM ('user', 'assistant')")

    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.Text, nullable=False, server_default="task"),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_criteria", postgresql.JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("action", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.execute("DROP TYPE chatroleenum")
    op.execute("DROP TYPE chatscopeenum")
```

- [ ] **Step 5: Commit**

```bash
git add backend/models/chat.py backend/alembic/versions/0003_add_chat_tables.py backend/tests/models/test_chat.py
git commit -m "feat: add ChatSession and ChatMessage ORM models and migration"
```

---

### Task 2: Extend BaseReviewer to Accept Extra Criteria

**Files:**
- Modify: `backend/review/base.py`

This allows chat-specified standards to be injected into reviewer prompts.

- [ ] **Step 1: Write failing test**

```python
# backend/tests/review/test_base.py — add to existing test file
from review.base import BaseReviewer
from review.schemas import SectionData, ReviewConfig, ReviewResult

class DummyReviewer(BaseReviewer):
    reviewer_name = "dummy"
    review_criteria = "base criteria"
    async def review(self, sections, config, llm_client=None):
        return ReviewResult(reviewer_name="dummy", status="pass", score=100, summary="ok", issues=[])

def test_build_prompt_with_extra_criteria():
    reviewer = DummyReviewer()
    sections = [SectionData(id="1", title="Intro", content="Hello", order_index=0)]
    messages = reviewer._build_prompt(sections, "base criteria", extra_criteria=["Follow ISO 9001"])
    system = messages[0]["content"]
    assert "ISO 9001" in system
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/review/test_base.py::test_build_prompt_with_extra_criteria -v`
Expected: FAIL with `TypeError: _build_prompt() got an unexpected keyword argument 'extra_criteria'`

- [ ] **Step 2: Modify `backend/review/base.py` — add `extra_criteria` parameter**

Change the `_build_prompt` signature and system prompt assembly:

```python
def _build_prompt(
    self,
    sections: list[SectionData],
    criteria: str,
    rules: list[dict[str, Any]] | None = None,
    extra_criteria: list[str] | None = None,  # <-- new param
) -> list[dict[str, str]]:
    """Build LLM messages for review. Single prompt → structured output (G9)."""
    sections_text = "\n\n".join(
        f"## Section {s.order_index + 1}: {s.title}\n{s.content}" for s in sections
    )
    rules_text = ""
    if rules:
        rules_text = "\n\nApplicable rules:\n" + "\n".join(
            f"- {r.get('name', '')}: {r.get('description', '')}" for r in rules
        )

    extra_text = ""
    if extra_criteria:
        extra_text = "\n\nAdditional review criteria specified by user:\n" + "\n".join(
            f"- {c}" for c in extra_criteria
        )

    system_prompt = (
        f"You are a specialized document reviewer. Your review criteria: {criteria}"
        f"{extra_text}\n"
        "Return a JSON object with this exact structure:\n"
        '{"status": "pass"|"fail"|"warning", "score": 0-100, "summary": "...", '
        '"issues": [{"severity": "critical"|"major"|"minor"|"info", "category": "...", '
        '"section_id": null, "location_excerpt": "...", "description": "...", '
        '"suggestion": "...", "requires_human": false}]}'
    )

    user_prompt = (
        f"Please review the following document sections:{rules_text}\n\n"
        f"{sections_text}\n\n"
        "Return your review as JSON."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
```

- [ ] **Step 3: Run test**

Run: `cd backend && LITELLM_MOCK=true pytest tests/review/test_base.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/review/base.py backend/tests/review/test_base.py
git commit -m "feat: extend BaseReviewer._build_prompt with extra_criteria support"
```

---

### Task 3: Chat Service

**Files:**
- Create: `backend/schemas/chat.py`
- Create: `backend/services/chat_service.py`
- Create: `backend/tests/services/test_chat_service.py`

- [ ] **Step 1: Write failing service tests**

```python
# backend/tests/services/test_chat_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.chat_service import ChatService
import uuid

@pytest.fixture
def service():
    return ChatService()

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db

@pytest.mark.asyncio
async def test_create_session(service, mock_db):
    task_id = str(uuid.uuid4())
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())
    session = await service.create_session(mock_db, task_id=task_id, scope="task")
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert session.task_id == uuid.UUID(task_id)
    assert session.scope == "task"

@pytest.mark.asyncio
async def test_add_message(service, mock_db):
    session_id = str(uuid.uuid4())
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())
    msg = await service.add_message(
        mock_db, session_id=session_id, role="user", content="Hello"
    )
    mock_db.add.assert_called_once()
    assert msg.content == "Hello"
    assert msg.role == "user"
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/services/test_chat_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/schemas/chat.py`**

```python
"""Pydantic schemas for Chat endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    scope: str = Field(default="task", pattern="^(task|section)$")
    section_id: str | None = None


class ChatSessionResponse(BaseModel):
    id: str
    task_id: str
    scope: str
    section_id: str | None
    review_criteria: list[dict[str, str]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    action: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create `backend/services/chat_service.py`**

```python
"""Chat service — session and message management."""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat import ChatMessage, ChatSession


class ChatService:
    """CRUD operations for chat sessions and messages."""

    async def create_session(
        self,
        db: AsyncSession,
        task_id: str,
        scope: str = "task",
        section_id: str | None = None,
    ) -> ChatSession:
        session = ChatSession(
            task_id=uuid.UUID(task_id),
            scope=scope,
            section_id=uuid.UUID(section_id) if section_id else None,
            review_criteria=[],
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_session(self, db: AsyncSession, session_id: str) -> ChatSession | None:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == uuid.UUID(session_id))
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, db: AsyncSession, task_id: str) -> Sequence[ChatSession]:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.task_id == uuid.UUID(task_id))
            .order_by(ChatSession.created_at.desc())
        )
        return result.scalars().all()

    async def list_messages(self, db: AsyncSession, session_id: str) -> Sequence[ChatMessage]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == uuid.UUID(session_id))
            .order_by(ChatMessage.created_at.asc())
        )
        return result.scalars().all()

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        action: dict[str, Any] | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=uuid.UUID(session_id),
            role=role,
            content=content,
            action=action,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def append_review_criterion(
        self, db: AsyncSession, session_id: str, label: str, description: str
    ) -> ChatSession:
        """Add a review standard to the session's criteria list."""
        session = await self.get_session(db, session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")
        criteria = list(session.review_criteria or [])
        criteria.append({"label": label, "description": description})
        session.review_criteria = criteria
        await db.commit()
        await db.refresh(session)
        return session

    async def get_review_criteria_for_task(
        self, db: AsyncSession, task_id: str
    ) -> list[str]:
        """Return all criteria descriptions from the most recent task session."""
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.task_id == uuid.UUID(task_id), ChatSession.scope == "task")
            .order_by(ChatSession.created_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if session is None or not session.review_criteria:
            return []
        return [c["description"] for c in session.review_criteria if "description" in c]
```

- [ ] **Step 4: Run service tests**

Run: `cd backend && LITELLM_MOCK=true pytest tests/services/test_chat_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/chat.py backend/services/chat_service.py backend/tests/services/test_chat_service.py
git commit -m "feat: add Chat schemas and service"
```

---

### Task 4: Chat Skill

**Files:**
- Create: `backend/skills/chat.py`
- Create: `backend/tests/skills/test_chat.py`

- [ ] **Step 1: Write failing skill test**

```python
# backend/tests/skills/test_chat.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from skills.chat import ChatSkill, INTENT_EDIT, INTENT_STANDARD
from skills.base import SkillContext, SkillResult


@pytest.fixture
def mock_llm():
    client = MagicMock()
    client.complete_json = AsyncMock(return_value={
        "intent": INTENT_STANDARD,
        "reply": "已记录标准：ISO 9001",
        "standard_label": "ISO 9001",
        "standard_description": "Follow ISO 9001 quality management requirements",
        "section_id": None,
        "rewrite_instruction": None,
    })
    return client


@pytest.mark.asyncio
async def test_chat_skill_standard_intent(mock_llm):
    skill = ChatSkill()
    context = SkillContext(
        task_id="test-task",
        llm_client=mock_llm,
        input_data={
            "session_id": "session-1",
            "user_message": "按照 ISO 9001 标准审查",
            "history": [],
            "sections": [],
        },
    )
    result = await skill.execute(context)
    assert result.success is True
    assert result.output["intent"] == INTENT_STANDARD
    assert "reply" in result.output


@pytest.mark.asyncio
async def test_chat_skill_requires_llm_client():
    skill = ChatSkill()
    context = SkillContext(
        task_id="test-task",
        input_data={"session_id": "s", "user_message": "hi", "history": [], "sections": []},
    )
    result = await skill.execute(context)
    assert result.success is False
    assert "llm_client" in result.error
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/skills/test_chat.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/skills/chat.py`**

```python
"""ChatSkill — resolves user chat messages into document actions or standard specs."""

from __future__ import annotations

import time
from typing import Any

from skills.base import BaseSkill, SkillContext, SkillResult

INTENT_EDIT = "edit"
INTENT_STANDARD = "standard"
INTENT_QUERY = "query"

_SYSTEM_PROMPT = """\
You are an AI assistant helping a user manage a document generation task.
You have access to the document sections listed below.

Your job: analyze the user's message and return JSON with:
{
  "intent": "edit" | "standard" | "query",
  "reply": "<friendly reply to show the user>",
  "section_id": "<section id if editing a specific section, else null>",
  "rewrite_instruction": "<instruction for the rewrite skill if intent=edit, else null>",
  "standard_label": "<short label if intent=standard, e.g. 'ISO 9001', else null>",
  "standard_description": "<full description of the standard if intent=standard, else null>"
}

Intent meanings:
- edit: user wants to modify one or more document sections
- standard: user is specifying a review standard or criterion to follow
- query: user is asking a question (answer in 'reply', no document changes)
"""


class ChatSkill(BaseSkill):
    """Resolves chat intent and returns structured action for the API layer to execute."""

    name = "chat"
    description = "Resolve user chat message into document action or standard specification"
    prerequisites: list[str] = []

    async def execute(self, context: SkillContext) -> SkillResult:
        start_ms = int(time.time() * 1000)
        llm = context.llm_client
        if llm is None:
            return SkillResult(
                success=False,
                error="llm_client is required for ChatSkill",
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

        user_message: str = context.input_data.get("user_message", "")
        history: list[dict[str, str]] = context.input_data.get("history", [])
        sections: list[dict[str, Any]] = context.input_data.get("sections", [])

        sections_text = "\n".join(
            f"- [{s.get('id', '?')}] {s.get('title', '')}: {str(s.get('content', ''))[:200]}"
            for s in sections
        )

        messages = [{"role": "system", "content": _SYSTEM_PROMPT + f"\n\nDocument sections:\n{sections_text}"}]
        for h in history[-10:]:  # last 10 messages for context
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            result = await llm.complete_json(messages=messages)
        except Exception as exc:
            return SkillResult(
                success=False,
                error=str(exc),
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

        return SkillResult(
            success=True,
            output=result,
            execution_time_ms=int(time.time() * 1000) - start_ms,
        )


from skills.registry import get_skill_registry  # noqa: E402
get_skill_registry().register(ChatSkill())
```

- [ ] **Step 3: Run skill tests**

Run: `cd backend && LITELLM_MOCK=true pytest tests/skills/test_chat.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/skills/chat.py backend/tests/skills/test_chat.py
git commit -m "feat: add ChatSkill with intent resolution"
```

---

### Task 5: Chat API Endpoints

**Files:**
- Create: `backend/api/chat.py`
- Modify: `backend/api/router.py`
- Create: `backend/tests/api/test_chat.py`

- [ ] **Step 1: Write failing API tests**

```python
# backend/tests/api/test_chat.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
import uuid, datetime
from models.chat import ChatSession, ChatMessage

@pytest.fixture
def mock_chat_service():
    from services.chat_service import ChatService
    svc = MagicMock(spec=ChatService)
    session = ChatSession()
    session.id = uuid.uuid4()
    session.task_id = uuid.uuid4()
    session.scope = "task"
    session.section_id = None
    session.review_criteria = []
    session.created_at = datetime.datetime.now()
    svc.create_session = AsyncMock(return_value=session)
    svc.list_sessions = AsyncMock(return_value=[session])
    svc.list_messages = AsyncMock(return_value=[])
    return svc

@pytest.mark.asyncio
async def test_create_chat_session(mock_chat_service):
    task_id = str(uuid.uuid4())
    with patch("api.chat._service", mock_chat_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(f"/api/v1/tasks/{task_id}/chat/sessions", json={"scope": "task"})
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_list_chat_sessions(mock_chat_service):
    task_id = str(uuid.uuid4())
    with patch("api.chat._service", mock_chat_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/tasks/{task_id}/chat/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

Run: `cd backend && LITELLM_MOCK=true pytest tests/api/test_chat.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 2: Create `backend/api/chat.py`**

```python
"""FastAPI router for chat session management and message handling."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.llm import get_llm_client
from schemas.chat import (
    ChatMessageResponse,
    ChatMessageSend,
    ChatSessionCreate,
    ChatSessionResponse,
)
from services.chat_service import ChatService
from skills.chat import ChatSkill

router = APIRouter(tags=["chat"])
_service = ChatService()
_skill = ChatSkill()


def _session_to_response(s: object) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=str(getattr(s, "id")),
        task_id=str(getattr(s, "task_id")),
        scope=str(getattr(s, "scope")),
        section_id=str(getattr(s, "section_id")) if getattr(s, "section_id") else None,
        review_criteria=list(getattr(s, "review_criteria") or []),
        created_at=getattr(s, "created_at"),
    )


def _msg_to_response(m: object) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=str(getattr(m, "id")),
        session_id=str(getattr(m, "session_id")),
        role=str(getattr(m, "role")),
        content=str(getattr(m, "content")),
        action=getattr(m, "action"),
        created_at=getattr(m, "created_at"),
    )


@router.post("/tasks/{task_id}/chat/sessions", status_code=201, response_model=ChatSessionResponse)
async def create_session(
    task_id: str,
    body: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    session = await _service.create_session(
        db, task_id=task_id, scope=body.scope, section_id=body.section_id
    )
    return _session_to_response(session)


@router.get("/tasks/{task_id}/chat/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    task_id: str, db: AsyncSession = Depends(get_db)
) -> list[ChatSessionResponse]:
    sessions = await _service.list_sessions(db, task_id)
    return [_session_to_response(s) for s in sessions]


@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> list[ChatMessageResponse]:
    msgs = await _service.list_messages(db, session_id)
    return [_msg_to_response(m) for m in msgs]


@router.post("/chat/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: ChatMessageSend,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Send a chat message and stream the assistant reply via SSE."""
    session = await _service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Persist user message
    await _service.add_message(db, session_id=session_id, role="user", content=body.content)

    # Load message history and sections for context
    history_msgs = await _service.list_messages(db, session_id)
    history = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]  # exclude just-added user msg

    # Load sections for task context
    from sqlalchemy import select
    from models.section import Section
    sections_result = await db.execute(
        select(Section).where(Section.task_id == session.task_id).order_by(Section.order_index)
    )
    sections = [
        {"id": str(s.id), "title": s.title, "content": s.content or ""}
        for s in sections_result.scalars().all()
    ]

    llm_client = get_llm_client()

    async def event_stream() -> AsyncGenerator[str, None]:
        from skills.base import SkillContext
        context = SkillContext(
            task_id=str(session.task_id),
            input_data={
                "session_id": session_id,
                "user_message": body.content,
                "history": history,
                "sections": sections,
            },
            llm_client=llm_client,
            db_session=db,
        )
        result = await _skill.execute(context)

        if not result.success:
            yield f"data: {json.dumps({'error': result.error})}\n\n"
            return

        intent = result.output.get("intent")
        reply = result.output.get("reply", "")

        # Handle standard specification
        if intent == "standard":
            label = result.output.get("standard_label", "")
            description = result.output.get("standard_description", "")
            if label and description:
                await _service.append_review_criterion(db, session_id, label, description)

        # Handle edit intent
        action: dict[str, Any] | None = None
        if intent == "edit":
            section_id = result.output.get("section_id")
            rewrite_instruction = result.output.get("rewrite_instruction")
            if section_id and rewrite_instruction:
                action = {
                    "type": "edit",
                    "section_id": section_id,
                    "instruction": rewrite_instruction,
                    "status": "pending_confirmation",
                }

        # Persist assistant message
        await _service.add_message(
            db, session_id=session_id, role="assistant", content=reply, action=action
        )

        yield f"data: {json.dumps({'reply': reply, 'intent': intent, 'action': action})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 3: Modify `backend/api/router.py` — register chat router**

```python
# Add to imports:
from api.chat import router as chat_router

# Add to include_router calls:
router.include_router(chat_router)
```

- [ ] **Step 4: Run API tests**

Run: `cd backend && LITELLM_MOCK=true pytest tests/api/test_chat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api/chat.py backend/api/router.py backend/tests/api/test_chat.py
git commit -m "feat: add Chat API endpoints with SSE streaming"
```

---

### Task 6: Frontend — Chat API Client + Hooks

**Files:**
- Create: `frontend/lib/api/chat.ts`
- Create: `frontend/lib/hooks/use-chat.ts`

- [ ] **Step 1: Create `frontend/lib/api/chat.ts`**

```typescript
import { apiFetch, API_BASE } from "@/lib/api";

export interface ChatSession {
  id: string;
  task_id: string;
  scope: "task" | "section";
  section_id: string | null;
  review_criteria: { label: string; description: string }[];
  created_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  action: { type: string; section_id: string; instruction: string; status: string } | null;
  created_at: string;
}

export const chatApi = {
  createSession: (taskId: string, scope: "task" | "section" = "task", sectionId?: string) =>
    apiFetch<ChatSession>(`/api/v1/tasks/${taskId}/chat/sessions`, {
      method: "POST",
      body: JSON.stringify({ scope, section_id: sectionId ?? null }),
    }),

  listSessions: (taskId: string) =>
    apiFetch<ChatSession[]>(`/api/v1/tasks/${taskId}/chat/sessions`),

  listMessages: (sessionId: string) =>
    apiFetch<ChatMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`),

  /** Returns an EventSource-compatible fetch. Caller handles SSE parsing. */
  sendMessage: async (
    sessionId: string,
    content: string,
    onChunk: (data: { reply: string; intent: string; action: ChatMessage["action"] } | { error: string }) => void,
    onDone: () => void,
  ) => {
    const res = await fetch(`${API_BASE}/api/v1/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (!res.ok) throw new Error(`Chat error ${res.status}`);
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") { onDone(); return; }
          try { onChunk(JSON.parse(payload)); } catch { /* ignore malformed */ }
        }
      }
    }
    onDone();
  },
};
```

- [ ] **Step 2: Create `frontend/lib/hooks/use-chat.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { chatApi, ChatMessage, ChatSession } from "@/lib/api/chat";

export function useChatSessions(taskId: string) {
  return useQuery({
    queryKey: ["chat-sessions", taskId],
    queryFn: () => chatApi.listSessions(taskId),
  });
}

export function useChatMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-messages", sessionId],
    queryFn: () => chatApi.listMessages(sessionId!),
    enabled: !!sessionId,
  });
}

export function useCreateChatSession(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ scope, sectionId }: { scope: "task" | "section"; sectionId?: string }) =>
      chatApi.createSession(taskId, scope, sectionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chat-sessions", taskId] }),
  });
}

export function useSendMessage(sessionId: string, taskId: string) {
  const qc = useQueryClient();
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingReply, setStreamingReply] = useState("");

  const send = useCallback(async (content: string) => {
    setIsStreaming(true);
    setStreamingReply("");
    try {
      await chatApi.sendMessage(
        sessionId,
        content,
        (chunk) => {
          if ("reply" in chunk) setStreamingReply(chunk.reply);
        },
        () => {
          setIsStreaming(false);
          setStreamingReply("");
          qc.invalidateQueries({ queryKey: ["chat-messages", sessionId] });
        },
      );
    } catch {
      setIsStreaming(false);
    }
  }, [sessionId, qc]);

  return { send, isStreaming, streamingReply };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/chat.ts frontend/lib/hooks/use-chat.ts
git commit -m "feat: add Chat API client and React Query hooks"
```

---

### Task 7: Frontend — Chat UI Components

**Files:**
- Create: `frontend/components/chat/chat-message.tsx`
- Create: `frontend/components/chat/chat-sidebar.tsx`
- Create: `frontend/components/chat/section-edit-modal.tsx`
- Modify: `frontend/app/tasks/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/components/chat/chat-message.tsx`**

```tsx
import { ChatMessage } from "@/lib/api/chat";

interface Props { message: ChatMessage }

export function ChatMessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.action && message.action.status === "pending_confirmation" && (
          <div className="mt-2 text-xs bg-yellow-100 text-yellow-800 rounded p-2">
            待确认修改：{message.action.instruction}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/chat/chat-sidebar.tsx`**

```tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { useChatSessions, useChatMessages, useCreateChatSession, useSendMessage } from "@/lib/hooks/use-chat";
import { ChatMessageBubble } from "./chat-message";

interface Props { taskId: string }

export function ChatSidebar({ taskId }: Props) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: sessions } = useChatSessions(taskId);
  const createSession = useCreateChatSession(taskId);
  const activeSession = sessions?.[0] ?? null;
  const { data: messages } = useChatMessages(activeSession?.id ?? null);
  const { send, isStreaming, streamingReply } = useSendMessage(
    activeSession?.id ?? "", taskId
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingReply]);

  const ensureSession = async () => {
    if (!activeSession) {
      await createSession.mutateAsync({ scope: "task" });
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;
    await ensureSession();
    const msg = input;
    setInput("");
    await send(msg);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed right-4 bottom-4 z-40 bg-blue-600 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg hover:bg-blue-700 text-xl"
        title="打开 AI 对话"
      >
        💬
      </button>
    );
  }

  return (
    <div className="fixed right-0 top-0 bottom-0 z-40 w-80 bg-white border-l border-gray-200 flex flex-col shadow-xl">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold text-gray-800 text-sm">AI 助手</h2>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">✕</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {messages?.map((m) => <ChatMessageBubble key={m.id} message={m} />)}
        {isStreaming && streamingReply && (
          <div className="flex justify-start mb-3">
            <div className="max-w-[80%] rounded-lg px-3 py-2 text-sm bg-gray-100 text-gray-800">
              <p className="whitespace-pre-wrap">{streamingReply}</p>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t p-3 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder="输入消息（Enter 发送）"
          rows={2}
          className="flex-1 resize-none rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          disabled={isStreaming}
        />
        <button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          className="bg-blue-600 text-white px-3 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          发送
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/components/chat/section-edit-modal.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useCreateChatSession, useChatSessions } from "@/lib/hooks/use-chat";
import { chatApi } from "@/lib/api/chat";

interface Props {
  taskId: string;
  sectionId: string;
  sectionTitle: string;
  onClose: () => void;
}

export function SectionEditModal({ taskId, sectionId, sectionTitle, onClose }: Props) {
  const [instruction, setInstruction] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const createSession = useCreateChatSession(taskId);
  const { data: sessions } = useChatSessions(taskId);

  const getSectionSession = async () => {
    const existing = sessions?.find(
      (s) => s.scope === "section" && s.section_id === sectionId
    );
    if (existing) return existing;
    return createSession.mutateAsync({ scope: "section", sectionId });
  };

  const handleSubmit = async () => {
    if (!instruction.trim() || submitting) return;
    setSubmitting(true);
    try {
      const session = await getSectionSession();
      await chatApi.sendMessage(
        session.id,
        `针对章节「${sectionTitle}」：${instruction}`,
        (chunk) => { if ("reply" in chunk) setResult(chunk.reply); },
        () => setSubmitting(false),
      );
    } catch {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-[480px] max-w-full p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">AI 修改章节：{sectionTitle}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        {!result ? (
          <>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="描述你希望如何修改这个章节..."
              rows={4}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2 justify-end">
              <button onClick={onClose} className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50">取消</button>
              <button
                onClick={handleSubmit}
                disabled={!instruction.trim() || submitting}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? "处理中..." : "提交"}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="rounded bg-gray-50 border border-gray-200 p-3 text-sm text-gray-800 whitespace-pre-wrap">{result}</div>
            <div className="flex gap-2 justify-end">
              <button onClick={onClose} className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50">关闭</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Modify `frontend/app/tasks/[id]/page.tsx` — add ChatSidebar**

Add the `ChatSidebar` import and render it at the bottom of the JSX return, just before the closing `</div>`:

```tsx
// Add import at top:
import { ChatSidebar } from "@/components/chat/chat-sidebar";

// Add just before closing </div> of the outermost flex container:
<ChatSidebar taskId={taskId} />
```

The `ContentPanel` component in `frontend/components/workbench/content-panel.tsx` should also expose an "AI 修改" button per section — read that file first, then add a prop `onSectionEdit?: (sectionId: string, sectionTitle: string) => void` and call it from each section card.

- [ ] **Step 5: Run frontend build check**

```bash
cd frontend && npm run build 2>&1 | tail -20
```
Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/chat/ frontend/app/tasks/ frontend/lib/api/chat.ts frontend/lib/hooks/use-chat.ts
git commit -m "feat: add Chat sidebar and section AI edit modal to workbench"
```

---

### Task 8: Full Test Suite Check

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && LITELLM_MOCK=true pytest tests/ -v --tb=short -q 2>&1 | tail -30
```
Expected: All tests PASS

- [ ] **Step 2: Apply migration**

```bash
docker compose exec backend alembic upgrade head
```
Expected: `Running upgrade 0002 -> 0003`

- [ ] **Step 3: Commit any fixes**

```bash
git add -A && git commit -m "fix: resolve chat feature test failures"
```
