# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Docker (primary development)
```bash
cp .env.example .env        # first time: fill in LLM_API_KEY
docker compose up -d        # start all services
docker compose up --build   # rebuild after code changes
docker compose logs -f backend
docker compose down -v      # stop and wipe data
```

### Backend (local development)
```bash
cd backend
pip install -e ".[dev]"
uvicorn main:app --reload                         # dev server on :8000
pytest                                            # all tests
pytest tests/test_health.py                       # single test file
pytest -k "test_name"                             # single test by name
alembic upgrade head                              # run migrations
alembic revision --autogenerate -m "description" # new migration
```

### Frontend (local development)
```bash
cd frontend
npm install
npm run dev     # dev server on :3000
npm test        # vitest unit tests
npm run build   # production build
```

### E2E tests
```bash
cd e2e
npm install
LITELLM_MOCK=true npx playwright test   # requires both services running
```

## Architecture

This is a **document generation and multi-role review platform** powered by LLM. The workflow is: upload source docs → parse → extract requirements → generate outline (human approval gate) → write sections → automated multi-reviewer review (up to 3 revision rounds) → final human approval → export DOCX.

```
frontend (Next.js 14 :3000)
    └─► backend (FastAPI :8000)
            ├── orchestrator/   # LangGraph workflow engine
            ├── skills/         # reusable LLM skill primitives
            ├── review/         # 8 parallel automated reviewers
            └── PostgreSQL + pgvector :5432
```

### Backend layers

**`orchestrator/`** — LangGraph `StateGraph` controlling the end-to-end pipeline. `graph.py` wires nodes together; `state.py` defines `DocumentState` (TypedDict). The state stores only IDs and control flags — all content stays in the DB. Two `interrupt()` points pause for human approval: outline and final.

**`skills/`** — All LLM operations are implemented as `BaseSkill` subclasses (parse, extract_requirements, outline, write_section, rewrite, retrieval, comparison). Skills are registered in a module-level `SkillRegistry` singleton (`skills/registry.py`). Each skill receives a `SkillContext` and returns a `SkillResult`. Retry logic with exponential backoff lives in `BaseSkill.execute_with_retry()`.

**`review/`** — 8 specialized reviewer classes all extend `BaseReviewer` (which extends `BaseSkill`): compliance, consistency, coverage, evidence, risk, structure, style, technical. Each reviewer calls the LLM once per invocation, returns structured JSON parsed into `ReviewResult`.

**`core/llm.py`** — `LLMClient` wraps litellm with retry logic. `LITELLM_MOCK=true` env var enables offline/test mode. Three model roles: `llm_default_model` (generation), `llm_review_model` (review), `llm_embed_model` (embeddings/RAG).

**`api/`** — FastAPI routers under `/api/v1/`. All aggregated in `api/router.py`. Key routes: tasks, documents, review, final_approval, sse (progress streaming), knowledge, template, version, export, audit, comparison.

**`models/`** — SQLAlchemy async ORM. Task lifecycle: `created → parsing → extracting → planning → awaiting_approval → generating → reviewing → revising → approved → exporting → completed | failed`. Progress updates are streamed via SSE.

**`services/`** — Service layer between API and ORM. One service per domain (task, document, review, approval, version, export, rag, template, etc.).

### Frontend structure

Next.js 14 App Router. Key routes mirror task lifecycle: `/` (task list), `/tasks/[id]` (workbench), `/tasks/[id]/reviews`, `/tasks/[id]/quality`, `/tasks/[id]/versions`, `/tasks/[id]/export`, `/knowledge`.

State management via TanStack Query (`@tanstack/react-query`). API calls centralized in `lib/api.ts`. Custom hooks in `lib/hooks/`.

### Testing approach

Backend: `pytest` with `pytest-asyncio`. Set `LITELLM_MOCK=true` to avoid real LLM calls. E2E Playwright tests require `LITELLM_MOCK=true` for deterministic behaviour. Frontend: Vitest + Testing Library.

### Key env vars
| Variable | Purpose |
|---|---|
| `LLM_API_KEY` | Required for real LLM calls |
| `LITELLM_MOCK` | `true` = use mock LLM (tests/offline) |
| `LLM_API_BASE` | Override LLM endpoint (e.g., Azure, local) |
| `SEED_DEMO_DATA` | Seed example data on startup |
