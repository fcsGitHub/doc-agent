# LLM Features Design

**Date:** 2026-04-06  
**Status:** Approved  
**Scope:** Three independent feature modules added to doc-agent

---

## Overview

Three new feature modules extending the doc-agent platform:

1. **LLM Manual Configuration** — runtime UI to manage LLM provider settings stored in DB
2. **LLM Chat** — task-level sidebar chat + section-level quick edits, driving document mutations
3. **LLM Wiki** — Karpathy-style knowledge base coexisting with existing RAG

All three follow the existing module pattern: independent `models/`, `services/`, `api/`, `schemas/` per domain. Architecture approach: **independent feature modules (Approach B)**.

---

## Feature 1: LLM Manual Configuration

### Problem
LLM settings (API key, base URL, model names) are loaded from env vars at startup. Changing them requires a restart and file edits.

### Solution
Store named LLM configurations in the database. Mark one as active. `get_llm_client()` reads from DB first, falls back to env vars. Switching configs resets the module-level singleton immediately.

### Data Model — `llm_configs` table

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | — |
| name | str | Display name (e.g. "Azure GPT-4", "Local Ollama") |
| api_key | str | Stored encrypted |
| api_base | str | Provider endpoint |
| default_model | str | Generation model |
| review_model | str | Review model |
| embed_model | str | Embedding model |
| is_active | bool | Only one row true at a time |
| created_at | datetime | — |

### New Files
- `models/llm_config.py` — SQLAlchemy model
- `schemas/llm_config.py` — Pydantic schemas
- `services/llm_config_service.py` — CRUD + activate logic
- `api/settings.py` — HTTP endpoints
- `alembic/versions/` — migration

### API Endpoints
```
GET    /api/v1/settings/llm               # list all configs
POST   /api/v1/settings/llm               # create config
PUT    /api/v1/settings/llm/{id}          # update config
DELETE /api/v1/settings/llm/{id}          # delete config
POST   /api/v1/settings/llm/{id}/activate # activate config (sets is_active=true, others false)
```

### `core/llm.py` Change
`get_llm_client()` becomes async, queries `llm_configs` for `is_active=true` row. Falls back to `settings` (env vars) if table is empty or DB unreachable.

All callers of `get_llm_client()` must be updated to `await get_llm_client()`. Affected: `BaseSkill.__init__`, all 8 reviewer constructors, `RAGService.__init__`, any test fixtures that call `get_llm_client()` directly.

### Frontend
- New page `/settings` with LLM config cards (list + form)
- Supports multiple named configs; one "Activate" button per card
- API key field masked (`type="password"`), revealed on demand
- Navigation bar adds a Settings entry

---

## Feature 2: LLM Chat

### Problem
No conversational interface exists. Users cannot iteratively guide document edits or specify review standards through dialogue.

### Solution
Two-level chat: a collapsible sidebar on the task workbench for full task context, and an inline "Edit with AI" button per section for scoped edits. Chat skill understands task context and can trigger document mutations.

### Data Models — `chat_sessions` and `chat_messages`

**`chat_sessions`**

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | — |
| task_id | UUID FK | Parent task |
| scope | enum | `task` / `section` |
| section_id | UUID? | Set when scope=section |
| review_criteria | JSON? | Accumulated standards from user instructions |
| created_at | datetime | — |

**`chat_messages`**

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | — |
| session_id | UUID FK | Parent session |
| role | enum | `user` / `assistant` |
| content | str | Message text |
| action | JSON? | Document mutation record (section_id, before, after) |
| created_at | datetime | — |

### Chat Skill (`skills/chat.py`)
Extends `BaseSkill`. Receives: conversation history + task context (document sections, review results, active wiki articles).

Two intent types resolved by the LLM:

- **Document edit intent**: user says "rewrite section X to be more concise" → calls `RewriteSkill` → records before/after in `action` field → streams diff back to user for confirmation
- **Standard specification intent**: user says "review against ISO 9001 clause 4.2" → appends standard description to `chat_session.review_criteria` (JSON array of `{label, description}` objects) → when a review run is triggered for this task, `ReviewService` loads `review_criteria` from the task's active chat session and appends each criterion as an additional instruction block in `BaseReviewer.build_system_prompt()`

### New Files
- `models/chat.py`
- `schemas/chat.py`
- `services/chat_service.py`
- `skills/chat.py`
- `api/chat.py`

### API Endpoints
```
POST   /api/v1/tasks/{task_id}/chat/sessions          # create session
GET    /api/v1/tasks/{task_id}/chat/sessions          # list sessions
POST   /api/v1/chat/sessions/{session_id}/messages    # send message (SSE streaming)
GET    /api/v1/chat/sessions/{session_id}/messages    # get history
```

### Frontend
- **Task sidebar**: collapsible Chat panel on `/tasks/[id]`, full conversation history, user can @-mention sections
- **Section quick edit**: "✏️ AI 修改" button on each section card → opens modal with scoped chat → shows diff on completion → user confirms or discards
- Chat responses stream via SSE (reuses existing SSE infrastructure)

---

## Feature 3: LLM Wiki

### Problem
Existing RAG uses pgvector embeddings — knowledge is in opaque vector space, not accumulated, and requires embedding infrastructure. No structured human-readable knowledge base exists.

### Solution
Implement Karpathy's LLM wiki pattern alongside existing RAG:
- Upload raw source documents → LLM "compiles" them into structured Markdown wiki articles
- Articles stored in DB as plain text; organized by category with backlinks
- Query by having LLM read relevant articles directly (no embedding needed)
- Existing RAG (`/knowledge`, pgvector) fully preserved
- Review process can use RAG, wiki, or both

### Data Models

**`wiki_raw_sources`**

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | — |
| filename | str | Original filename |
| content | text | Extracted plain text |
| compiled | bool | Whether compiled into wiki yet |
| uploaded_at | datetime | — |

**`wiki_articles`**

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | — |
| title | str | Article title |
| category | str | e.g. "行业规范", "术语", "历史案例" |
| content | text | Full Markdown body |
| summary | str | ~200 char summary (LLM-generated) |
| backlinks | JSON | List of referenced article IDs |
| source_doc_ids | JSON | Source `wiki_raw_sources` IDs |
| health_score | float? | Score from last lint run (0.0–1.0) |
| created_at | datetime | — |
| updated_at | datetime | — |

### Wiki Skill (`skills/wiki_compiler.py`)
Extends `BaseSkill`. Four operations:

1. **compile**: Read uncompiled raw sources → LLM identifies concepts → create/merge wiki articles → update backlinks and summary → mark sources as compiled
2. **query**: Receive question → load category index files → LLM selects relevant articles → read full content → return answer + source article IDs
3. **lint**: LLM scans all articles → identifies contradictions, orphaned articles, missing data → returns health report → updates `health_score` per article
4. **generate_index**: Maintain one `_index` record per category (title + summary list) used as navigation for query

### New Files
- `models/wiki.py`
- `schemas/wiki.py`
- `services/wiki_service.py`
- `skills/wiki_compiler.py`
- `api/wiki.py`
- `alembic/versions/` — migration for both wiki tables

### API Endpoints
```
POST   /api/v1/wiki/sources              # upload raw source file
GET    /api/v1/wiki/sources              # list raw sources
POST   /api/v1/wiki/compile              # trigger compile (async, SSE progress)
GET    /api/v1/wiki/articles             # list articles (filter by category)
GET    /api/v1/wiki/articles/{id}        # read article
PUT    /api/v1/wiki/articles/{id}        # human edit article
DELETE /api/v1/wiki/articles/{id}        # delete article
POST   /api/v1/wiki/query                # ask a question against the wiki
POST   /api/v1/wiki/lint                 # trigger health check
```

### Coexistence with RAG
- Existing `/api/v1/knowledge` routes and pgvector unchanged
- `review/base_reviewer.py` accepts optional `knowledge_mode: "rag" | "wiki" | "both"` param
- Chat skill can inject wiki query results as context alongside RAG results

### Frontend
- New page `/wiki` with left category tree + right article reader (Markdown rendered)
- "Upload Source" → "Compile" workflow with SSE progress bar
- Article editor: inline Markdown editor with save
- Lint report page: table of articles with health scores and LLM suggestions
- Navigation adds Wiki entry

---

## Migration Plan

Three independent Alembic migrations (can be applied together):
1. `add_llm_configs_table`
2. `add_chat_sessions_and_messages_tables`
3. `add_wiki_raw_sources_and_articles_tables`

## Testing

Each module gets its own test directory following existing patterns:
- `tests/services/test_llm_config_service.py`
- `tests/api/test_settings.py`
- `tests/services/test_chat_service.py`
- `tests/skills/test_chat.py`
- `tests/api/test_chat.py`
- `tests/services/test_wiki_service.py`
- `tests/skills/test_wiki_compiler.py`
- `tests/api/test_wiki.py`

All backend tests use `LITELLM_MOCK=true`.
