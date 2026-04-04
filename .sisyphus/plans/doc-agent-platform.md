# Document Intelligence Production & Review Platform

## TL;DR

> **Quick Summary**: Build an extensible AI agent platform for document production and multi-dimensional review. A single Document Orchestrator (LangGraph) coordinates pluggable Skills for parsing, writing, reviewing, and exporting documents. 8 specialized reviewers provide structured feedback with revision loops and human-in-the-loop checkpoints.
> 
> **Deliverables**:
> - FastAPI backend with 7 service modules, LangGraph orchestrator, 9+ Skills, 8 Reviewers
> - Next.js frontend with 5 pages (task home, workbench, review dashboard, version diff, export)
> - PostgreSQL database with 16+ data models + pgvector for RAG
> - Docker Compose deployment (frontend + backend + PostgreSQL)
> - TDD throughout with pytest + vitest
> 
> **Estimated Effort**: XL (6 phases, 40+ tasks)
> **Parallel Execution**: YES — 6 waves per phase, high parallelism within each
> **Critical Path**: Scaffold → DB Schema → BaseSkill Interface → LangGraph Skeleton → Parse Skill → Generation Pipeline → Review Engine → Frontend → Integration

---

## Context

### Original Request
Build a "Document Intelligence Production & Review Platform" — an extensible AI Agent platform supporting document task understanding, material parsing, knowledge retrieval, outline planning, section generation, multi-dimensional review, revision loops, format export, version management, and human annotation. NOT an agent zoo — one Document Orchestrator with config-driven doc type adaptation via Skills.

### Interview Summary
**Key Discussions**:
- **MVP Scope**: User selected ALL 10 capabilities and ALL 8 reviewers as MVP-required
- **Tech Stack**: Next.js + FastAPI + LangGraph + PostgreSQL + pgvector + Docker Compose
- **LLM**: Configurable multi-backend via litellm (OpenAI/Azure/local)
- **Auth**: Single user, no authentication for MVP
- **UI**: Chinese interface, code in English
- **Testing**: TDD (pytest + vitest)
- **Project**: Monorepo (frontend/ + backend/)

**Explicit Exclusions**:
- No multi-user collaboration, no i18n, no PDF export, no mobile, no microservices, no scheduler, no WebSocket

### Metis Review
**Identified Gaps** (addressed):
- **LLM Cost/Rate Limits**: Added `llm_usage` tracking, `max_revision_loops=3` safety valve, parallel reviewer execution
- **Long-Running Task UX**: Added SSE progress updates, background task execution with status polling
- **Error Recovery**: LangGraph checkpointing + per-skill retry logic (exponential backoff, max 3)
- **Review Aggregation Logic**: Configurable pass/fail policy (any critical = fail, threshold for major)
- **Seed Data**: Include demo template, sample rules, sample terms for testability
- **State Bloat**: LangGraph state = control plane only (IDs, statuses). All content in PostgreSQL
- **Document Size**: Upload limit 50MB, max 200 pages, section-level chunking for LLM
- **Section Granularity**: Sequential generation for MVP, `depends_on` field for future parallelism

---

## Work Objectives

### Core Objective
Build an extensible document production and review platform with a LangGraph-based orchestrator, pluggable skill system, 8 specialized reviewers, version management, and a professional Chinese workbench UI — all deployable via Docker Compose.

### Concrete Deliverables
- `backend/` — FastAPI app with LangGraph orchestrator, 9 Skills, 8 Reviewers, 7 service modules
- `frontend/` — Next.js app with 5 pages: task home, workbench, review dashboard, version diff, export
- `docker-compose.yml` — One-click deployment of frontend + backend + PostgreSQL
- Database — 16+ tables with Alembic migrations, pgvector extension
- Seed data — 1 demo template, sample rules, sample terms
- End-to-end smoke test — Upload → Parse → Generate → Review → Revise → Export

### Definition of Done
- [ ] `docker compose up` starts all services successfully
- [ ] Full end-to-end flow completes: upload DOCX → parse → extract requirements → generate outline → user approves → generate sections → 8 reviewers run → issues shown → auto-revise → re-review → export DOCX
- [ ] All backend tests pass: `pytest backend/tests/ -v`
- [ ] All frontend tests pass: `npm run test` in frontend/
- [ ] Frontend builds without errors: `npm run build` in frontend/

### Must Have
- Single Document Orchestrator (LangGraph StateGraph) — NOT agent-per-doc-type
- Pluggable Skill interface (`BaseSkill` ABC) with registry
- ALL 8 reviewers with structured output (`ReviewResult` / `ReviewIssue`)
- Review issues localized to section + excerpt
- Each revision = new version in database
- Human-in-the-loop: outline approval + final review approval
- Config-driven doc type adaptation (template + rules + style guide)
- SSE progress updates for long-running tasks
- Configurable LLM backend via litellm
- Seed data for testability

### Must NOT Have (Guardrails)
- **G1**: NO document content in LangGraph state — state is control plane only (IDs, statuses, flags). All content in PostgreSQL
- **G2**: NO direct OpenAI imports in skill code — all LLM calls via litellm abstraction
- **G3**: NO template abstraction before one concrete doc type works end-to-end — build "generic report" first
- **G4**: NO synchronous database calls — all SQLAlchemy operations via async engine
- **G5**: NO WebSocket — use SSE for progress updates
- **G6**: NO authentication/authorization logic
- **G7**: NO complex frontend state management — TanStack Query for server state only
- **G8**: NO more than 3 auto-revision loops — force human decision after max
- **G9**: NO multi-turn reasoning inside reviewers — each reviewer = 1 prompt + structured output for MVP
- **G10**: NO hybrid search or reranking in RAG — basic pgvector cosine similarity for MVP
- **G11**: NO custom DOCX styles/headers/footers — basic headings + paragraphs via python-docx
- **G12**: NO charts library in quality dashboard — static summary cards only

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (greenfield — will be set up in Phase 1)
- **Automated tests**: TDD (Test-Driven Development)
- **Framework (backend)**: pytest + pytest-asyncio + httpx.AsyncClient
- **Framework (frontend)**: vitest + @testing-library/react
- **If TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **API/Backend**: Use Bash (curl/httpx) — Send requests, assert status + response fields
- **Frontend/UI**: Use Playwright — Navigate, interact, assert DOM, screenshot
- **Library/Module**: Use Bash (pytest) — Run specific test files, verify output
- **Database**: Use Bash (psql/SQLAlchemy) — Query tables, assert row counts and data

### QA Execution Environment (IMPORTANT)
> **All QA and verification commands execute inside Docker containers (Linux/bash)** via
> `docker compose exec backend bash -c "..."` or `docker compose exec frontend sh -c "..."`.
>
> The development host is **win32/pwsh**, but all application code runs in Linux containers.
> Commands like `curl`, `grep`, `ls`, `wc`, `pytest`, `uvicorn`, and bash pipelines are
> available inside the containers. The executing agent MUST:
> 1. Use `docker compose up -d` to start services before running QA
> 2. Prefix backend commands with `docker compose exec backend bash -c "..."`
> 3. Prefix frontend commands with `docker compose exec frontend sh -c "..."`
> 4. For host-level file checks (e.g., verifying file existence), use PowerShell equivalents:
>    - `ls -d dir/` → `Test-Path dir/`
>    - `grep -c pattern file` → `Select-String -Pattern "pattern" file | Measure-Object`
>    - `wc -l` → `Measure-Object -Line`
> 5. For `curl` on the host, use `Invoke-WebRequest` or install curl via scoop/choco
>
> **Rule**: If a QA scenario says `curl`, `grep`, `ls`, or uses `|` pipes, the executing
> agent decides the execution context: container (bash) for app verification, host (pwsh)
> for file structure checks. The commands in this plan are written in bash syntax as the
> canonical form; translation to the correct execution context is the agent's responsibility.

### Supported File Types (CANONICAL — Two Scopes)

> **Task document uploads** (Tasks 12, 16, 32, 33, 51, F3):
> - Accepted: `.docx`, `.pdf`, `.md`
> - `.txt` is NOT accepted for task documents
>
> **Knowledge base uploads** (Tasks 38, 45):
> - Accepted: `.docx`, `.pdf`, `.md`, `.txt`
> - `.txt` IS accepted for knowledge base reference documents
>
> All tasks MUST enforce the correct scope. Validation errors should say
> "不支持的文件类型" with the list of accepted types for that context.

---

## Execution Strategy

### Parallel Execution Waves

> 6 Phases, each with internal waves. Target 5-8 parallel tasks per wave.
> Each phase produces a runnable, testable vertical slice.

```
PHASE 1: Foundation (Walking Skeleton)
Wave 1.1 (Start Immediately — scaffolding):
├── Task 1: Monorepo scaffold + Docker Compose [quick]
├── Task 2: Backend project scaffold (FastAPI + deps) [quick]
├── Task 3: Frontend project scaffold (Next.js + deps) [quick]
└── Task 4: PostgreSQL schema design + Alembic setup [deep]

Wave 1.2 (After Wave 1.1 — core interfaces):
├── Task 5: LLM abstraction layer (litellm adapter) [unspecified-high]
├── Task 6: BaseSkill interface + Skill registry [deep]
├── Task 7: ReviewResult/ReviewIssue schemas + BaseReviewer [deep]
└── Task 8: Database models + initial migration [unspecified-high]

Wave 1.3 (After Wave 1.2 — orchestration skeleton):
├── Task 9: LangGraph StateGraph skeleton + checkpoint setup [deep]
├── Task 10: Task Service (CRUD API) [unspecified-high]
└── Task 11: SSE progress endpoint [quick]

PHASE 2: Core Pipeline (Document → Sections)
Wave 2.1 (After Phase 1 — skills):
├── Task 12: Document Parse Skill (DOCX + PDF + Markdown) [unspecified-high]
├── Task 13: Requirement Extraction Skill [unspecified-high]
├── Task 14: Outline Planning Skill [unspecified-high]
└── Task 15: Section Writing Skill [deep]

Wave 2.2 (After Wave 2.1 — pipeline integration):
├── Task 16: Document Service (upload, parse, sections CRUD) [unspecified-high]
├── Task 17: LangGraph generation pipeline (parse → extract → outline → write) [deep]
└── Task 18: Human-in-the-loop: outline approval interrupt [unspecified-high]

PHASE 3: Review Engine (8 Reviewers + Revision Loop)
Wave 3.1 (After Phase 2 — first reviewer + revision):
├── Task 19: Structure Reviewer [unspecified-high]
├── Task 20: Compliance Reviewer [unspecified-high]
├── Task 21: Technical Reviewer [unspecified-high]
└── Task 22: Evidence Reviewer [unspecified-high]

Wave 3.2 (Parallel with Wave 3.1 — remaining reviewers):
├── Task 23: Consistency Reviewer [unspecified-high]
├── Task 24: Style Reviewer [unspecified-high]
├── Task 25: Coverage Reviewer [unspecified-high]
└── Task 26: Risk Reviewer [unspecified-high]

Wave 3.3 (After Waves 3.1 + 3.2 — aggregation + revision):
├── Task 27: Review Service (run reviewers, aggregate, pass/fail) [deep]
├── Task 28: Rewrite & Polish Skill [unspecified-high]
├── Task 29: Revision loop in LangGraph (review → revise → re-review, max 3) [deep]
└── Task 30: Human-in-the-loop: final review approval interrupt [unspecified-high]

PHASE 4: Frontend Core
Wave 4.1 (After Phase 2 APIs stable — base UI):
├── Task 31: Frontend layout + navigation + API client setup [visual-engineering]
├── Task 32: Task home page (create, list, status) [visual-engineering]
└── Task 33: Task workbench page — left panel (task info, files, template) [visual-engineering]

Wave 4.2 (After Wave 4.1 — workbench + review):
├── Task 34: Task workbench — center panel (doc tree, section editor) [visual-engineering]
├── Task 35: Task workbench — right panel (review issues, annotations, evidence) [visual-engineering]
└── Task 36: Review dashboard page [visual-engineering]

PHASE 5: Advanced Features
Wave 5.1 (After Phase 3 — version + knowledge + export):
├── Task 37: Version management (snapshot, diff, version list API) [unspecified-high]
├── Task 38: Knowledge Service + RAG pipeline (pgvector) [deep]
├── Task 39: Retrieval Skill (search knowledge base) [unspecified-high]
├── Task 40: Template system (config-driven doc types) [unspecified-high]
└── Task 41: Export Service + Export Skill (Markdown + DOCX) [unspecified-high]

Wave 5.2 (After Wave 5.1 — remaining UI):
├── Task 42: Version diff page [visual-engineering]
├── Task 43: Export page [visual-engineering]
├── Task 44: Human annotation UI (comments per section) [visual-engineering]
└── Task 45: Knowledge base management UI [visual-engineering]

PHASE 6: Polish & Integration
Wave 6.1 (After Phase 5 — seed + audit + comparison):
├── Task 46: Seed data & demo flow [quick]
├── Task 47: Audit/Trace Service + audit log API [unspecified-high]
└── Task 48: Comparison/Diff Skill [quick]

Wave 6.2 (After Wave 6.1 — quality dashboard + final integration):
├── Task 49: Quality dashboard (summary cards, pass rates) [visual-engineering]
├── Task 50: Docker Compose finalization + env configuration [quick]
├── Task 51: End-to-end smoke test script [deep]

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: T1 → T4 → T8 → T9 → T12 → T17 → T19 → T27 → T29 → T31 → T34 → T37 → T41 → T50 → T51 → F1-F4 → user okay
Parallel Speedup: ~60% faster than sequential execution
Max Concurrent: 8 (Waves 3.1 + 3.2 combined)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 2, 3, 4 |
| 2 | 1 | 5, 6, 7, 8 |
| 3 | 1 | 31 |
| 4 | 1 | 8 |
| 5 | 2 | 12, 13, 14, 15 |
| 6 | 2 | 12, 13, 14, 15, 19-26 |
| 7 | 2 | 19-26, 27 |
| 8 | 2, 4 | 9, 10, 16 |
| 9 | 8 | 17, 18 |
| 10 | 8 | 16, 31 |
| 11 | 2 | 17 |
| 12 | 5, 6 | 16, 17 |
| 13 | 5, 6 | 17 |
| 14 | 5, 6 | 17 |
| 15 | 5, 6 | 17 |
| 16 | 8, 12 | 17 |
| 17 | 9, 11, 12, 13, 14, 15, 16 | 18, 19-26 |
| 18 | 17 | 29 |
| 19-26 | 6, 7, 17 | 27 |
| 27 | 19-26 | 29 |
| 28 | 5, 6 | 29 |
| 29 | 27, 28, 18 | 30 |
| 30 | 29 | 51 |
| 31 | 3, 10 | 32, 33 |
| 32 | 31 | 34 |
| 33 | 31 | 34 |
| 34 | 32, 33, 16 | 35 |
| 35 | 34, 27 | 36 |
| 36 | 35, 27 | 46 |
| 37 | 8 | 42 |
| 38 | 8, 5 | 39 |
| 39 | 38, 6 | 45 |
| 40 | 8 | 48 |
| 41 | 8, 15 | 43 |
| 42 | 37, 31 | — |
| 43 | 41, 31 | — |
| 44 | 31, 8 | — |
| 45 | 39, 31 | — |
| 46 | 10, 40, 38 | 51 |
| 47 | 12, 27, 30, 37, 41 | — |
| 48 | 6 | 49 |
| 49 | 27, 36, 48 | — |
| 50 | All | 51 |
| 51 | 50 | F1-F4 |

### Agent Dispatch Summary

- **Phase 1 (Wave 1.1)**: 4 tasks — T1-T3 → `quick`, T4 → `deep`
- **Phase 1 (Wave 1.2)**: 4 tasks — T5 → `unspecified-high`, T6-T7 → `deep`, T8 → `unspecified-high`
- **Phase 1 (Wave 1.3)**: 3 tasks — T9 → `deep`, T10 → `unspecified-high`, T11 → `quick`
- **Phase 2 (Wave 2.1)**: 4 tasks — T12-T14 → `unspecified-high`, T15 → `deep`
- **Phase 2 (Wave 2.2)**: 3 tasks — T16 → `unspecified-high`, T17 → `deep`, T18 → `unspecified-high`
- **Phase 3 (Wave 3.1)**: 4 tasks — T19-T22 → `unspecified-high`
- **Phase 3 (Wave 3.2)**: 4 tasks — T23-T26 → `unspecified-high`
- **Phase 3 (Wave 3.3)**: 4 tasks — T27 → `deep`, T28 → `unspecified-high`, T29 → `deep`, T30 → `unspecified-high`
- **Phase 4 (Wave 4.1)**: 3 tasks — T31-T33 → `visual-engineering`
- **Phase 4 (Wave 4.2)**: 3 tasks — T34-T36 → `visual-engineering`
- **Phase 5 (Wave 5.1)**: 5 tasks — T37 → `unspecified-high`, T38 → `deep`, T39-T41 → `unspecified-high`
- **Phase 5 (Wave 5.2)**: 4 tasks — T42-T45 → `visual-engineering`
- **Phase 6 (Wave 6.1)**: 3 tasks — T46 → `quick`, T47 → `unspecified-high`, T48 → `quick`
- **Phase 6 (Wave 6.2)**: 3 tasks — T49 → `visual-engineering`, T50 → `quick`, T51 → `deep`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> TDD: RED (failing test) → GREEN (minimal impl) → REFACTOR in every task.

### PHASE 1: Foundation (Walking Skeleton)

- [x] 1. Monorepo Scaffold + Docker Compose

  **What to do**:
  - Create root project structure: `frontend/`, `backend/`, `docker-compose.yml`, `.gitignore`, `README.md`
  - Create `docker-compose.yml` with 3 services:
    - `postgres`: PostgreSQL 16 with pgvector extension, port 5432, volume for data persistence
    - `backend`: FastAPI app, port 8000, depends on postgres, env vars for DB connection + LLM config
    - `frontend`: Next.js app, port 3000, depends on backend
  - Create root `.env.example` with all required environment variables (DB URL, LLM API keys, etc.)
  - Create root `.gitignore` covering Python, Node.js, Docker, IDE files
  - Initialize git repository: `git init` + initial commit with scaffold files. This is required because the Commit Strategy and Final Verification (F4) depend on git history.

  **Must NOT do**:
  - Do NOT write application code yet — only project structure and Docker config
  - Do NOT add authentication env vars

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Scaffolding with known patterns, no complex logic
  - **Skills**: [`docker-patterns`, `coding-standards`]
    - `docker-patterns`: Docker Compose service configuration patterns
    - `coding-standards`: Project structure conventions

  **Parallelization**:
  - **Can Run In Parallel**: NO (first task — nothing to parallelize with)
  - **Parallel Group**: Wave 1.1
  - **Blocks**: Tasks 2, 3, 4
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - This is greenfield — no existing patterns. Follow standard monorepo conventions.

  **External References**:
  - Docker Compose v3 spec for multi-service setup
  - PostgreSQL 16 + pgvector Docker image: `pgvector/pgvector:pg16`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Docker Compose starts all services
    Tool: Bash
    Preconditions: Docker installed, .env file created from .env.example
    Steps:
      1. Run `docker compose config` — verify valid YAML, no errors
      2. Run `docker compose up -d postgres` — verify postgres starts
      3. Run `docker compose exec postgres psql -U docagent -c "CREATE EXTENSION IF NOT EXISTS vector;"` — verify pgvector available
      4. Run `docker compose down`
    Expected Result: All commands exit 0, pgvector extension creates successfully
    Failure Indicators: docker compose config shows errors, postgres fails to start, pgvector extension missing
    Evidence: .sisyphus/evidence/task-1-docker-compose-start.txt

  Scenario: Project structure is correct
    Tool: Bash
    Preconditions: Repository root exists
    Steps:
      1. Verify directories exist: `Test-Path frontend, backend` (pwsh) or `ls -d frontend/ backend/` (bash)
      2. Verify files exist: `Test-Path docker-compose.yml, .gitignore, .env.example` (pwsh)
      3. Verify docker-compose.yml has 3 services: `Select-String -Pattern "image|build" docker-compose.yml | Measure-Object` — expect 3+
      4. Verify git repo initialized: `git status` — expect clean working tree with initial commit
    Expected Result: All paths exist, docker-compose has 3 services, git repo initialized with initial commit
    Failure Indicators: Missing directories or files, git not initialized
    Evidence: .sisyphus/evidence/task-1-structure-check.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): scaffold monorepo with Docker Compose`
  - Files: `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`, `frontend/.gitkeep`, `backend/.gitkeep`

- [x] 2. Backend Project Scaffold (FastAPI + Dependencies)

  **What to do**:
  - Initialize Python project in `backend/` with `pyproject.toml` (use `hatch` or `poetry` for dependency management)
  - Install and configure core dependencies:
    - `fastapi`, `uvicorn[standard]`, `pydantic>=2.0`, `pydantic-settings`
    - `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `alembic`
    - `langgraph`, `langgraph-checkpoint-postgres`
    - `litellm`
    - `python-docx`, `pdfplumber`, `python-multipart`
    - `sse-starlette`
    - `pytest`, `pytest-asyncio`, `httpx` (dev dependencies)
  - Create backend directory structure:
    ```
    backend/
    ├── pyproject.toml
    ├── alembic.ini
    ├── alembic/
    │   └── env.py
    ├── main.py              (FastAPI app factory)
    ├── config.py             (pydantic-settings config)
    ├── core/
    │   ├── __init__.py
    │   ├── database.py       (async SQLAlchemy engine + session)
    │   └── llm.py            (placeholder)
    ├── api/
    │   ├── __init__.py
    │   └── router.py         (API router aggregator)
    ├── models/
    │   └── __init__.py
    ├── schemas/
    │   └── __init__.py
    ├── services/
    │   └── __init__.py
    ├── skills/
    │   └── __init__.py
    ├── review/
    │   └── __init__.py
    ├── orchestrator/
    │   └── __init__.py
    ├── knowledge/
    │   └── __init__.py
    ├── tests/
    │   ├── __init__.py
    │   ├── conftest.py       (test fixtures, test DB)
    │   └── test_health.py    (health endpoint test)
    └── Dockerfile
    ```
    > **NOTE**: All backend code lives directly under `backend/` — no extra `app/` nesting.
    > Python package root is `backend/`. Imports: `from models.task import Task`, `from core.llm import LLMClient`.
    > The `main.py` entry point lives at `backend/main.py` (uvicorn target: `main:app`).
  - Implement minimal `main.py`: FastAPI app with health endpoint `/api/v1/health`
  - Implement `config.py`: pydantic-settings loading from env vars (DATABASE_URL, LLM_API_KEY, etc.)
  - Implement `core/database.py`: async SQLAlchemy engine + async session factory
  - Implement `Dockerfile`: multi-stage build, Python 3.12, install deps, run uvicorn
  - TDD: Write `test_health.py` FIRST (RED), then implement health endpoint (GREEN)

  **Must NOT do**:
  - Do NOT implement any business logic
  - Do NOT add auth middleware
  - Do NOT use synchronous SQLAlchemy

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard FastAPI project setup with known patterns
  - **Skills**: [`python-patterns`, `backend-patterns`]
    - `python-patterns`: Python project structure, pyproject.toml conventions
    - `backend-patterns`: FastAPI app factory pattern

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 3, 4
  - **Parallel Group**: Wave 1.1 (after Task 1)
  - **Blocks**: Tasks 5, 6, 7, 8
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - FastAPI official docs: async app factory pattern
  - SQLAlchemy 2.0 async: `create_async_engine` + `async_sessionmaker`
  - pydantic-settings for configuration management

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/test_health.py`
  - [ ] `cd backend && pytest tests/test_health.py -v` → PASS (1 test)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Backend starts and health check works
    Tool: Bash
    Preconditions: Backend dependencies installed, PostgreSQL running
    Steps:
      1. Run `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 &`
      2. Wait 3s
      3. Run `curl -s http://localhost:8000/api/v1/health` — expect JSON with "status": "ok"
      4. Run `curl -s http://localhost:8000/docs` — expect Swagger UI HTML
    Expected Result: Health returns `{"status": "ok"}`, Swagger UI accessible
    Failure Indicators: Connection refused, 500 error, missing health endpoint
    Evidence: .sisyphus/evidence/task-2-health-check.txt

  Scenario: Backend Docker build succeeds
    Tool: Bash
    Preconditions: Dockerfile exists in backend/
    Steps:
      1. Run `docker build -t doc-agent-backend backend/` — expect successful build
      2. Verify image exists: `docker images doc-agent-backend` — expect 1 row
    Expected Result: Docker image builds successfully
    Failure Indicators: Build fails, dependency resolution errors
    Evidence: .sisyphus/evidence/task-2-docker-build.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): scaffold FastAPI backend project`
  - Files: `backend/**`
  - Pre-commit: `cd backend && pytest tests/ -v`

- [x] 3. Frontend Project Scaffold (Next.js + Dependencies)

  **What to do**:
  - Initialize Next.js 14+ project in `frontend/` with TypeScript + Tailwind CSS + App Router
  - Install core dependencies:
    - `@tanstack/react-query` (server state management)
    - `lucide-react` (icons)
    - `clsx`, `tailwind-merge` (class utilities)
    - `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` (dev)
  - Create directory structure:
    ```
    frontend/
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── next.config.ts
    ├── vitest.config.ts
    ├── Dockerfile
    ├── app/
    │   ├── layout.tsx      (root layout with Chinese font, QueryProvider)
    │   ├── page.tsx        (home redirect to /tasks)
    │   └── tasks/
    │       └── page.tsx    (placeholder)
    ├── components/
    │   └── ui/             (shared UI primitives)
    ├── lib/
    │   ├── api.ts          (API client base — fetch wrapper)
    │   └── query-provider.tsx (TanStack Query provider)
    ├── types/
    │   └── index.ts        (shared TypeScript types — placeholder)
    ├── __tests__/
    │   └── home.test.tsx       (basic render test)
    └── public/
    ```
    > **NOTE**: All frontend code lives directly under `frontend/` (NOT `frontend/src/`).
    > Next.js App Router at `frontend/app/`, components at `frontend/components/`, etc.
  - Configure vitest for React component testing with jsdom
  - Configure API client base URL from environment variable `NEXT_PUBLIC_API_URL`
  - Chinese UI: Set HTML lang="zh-CN", use system Chinese font stack
  - TDD: Write `home.test.tsx` FIRST, then implement page

  **Must NOT do**:
  - Do NOT add complex state management (Redux, Zustand)
  - Do NOT add i18n framework
  - Do NOT add authentication
  - Do NOT add UI component library (build minimal primitives)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Frontend scaffolding with UI considerations
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: Next.js App Router patterns, TanStack Query setup
    - `coding-standards`: TypeScript conventions

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 2, 4
  - **Parallel Group**: Wave 1.1 (after Task 1)
  - **Blocks**: Task 31
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - Next.js 14 App Router official docs
  - TanStack Query v5 setup with Next.js
  - Vitest + React Testing Library configuration

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `frontend/__tests__/home.test.tsx`
  - [ ] `cd frontend && npm run test` → PASS (1 test)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Frontend builds and starts
    Tool: Bash
    Preconditions: Node.js 18+ installed, dependencies installed
    Steps:
      1. Run `cd frontend && npm run build` — expect no errors
      2. Run `cd frontend && npm run start &` — wait 5s
      3. Run `curl -s http://localhost:3000` — expect HTML with lang="zh-CN"
    Expected Result: Build succeeds, page serves with Chinese lang attribute
    Failure Indicators: Build fails, TypeScript errors, page not accessible
    Evidence: .sisyphus/evidence/task-3-frontend-build.txt

  Scenario: Frontend Docker build succeeds
    Tool: Bash
    Preconditions: Dockerfile exists in frontend/
    Steps:
      1. Run `docker build -t doc-agent-frontend frontend/` — expect success
    Expected Result: Docker image builds successfully
    Failure Indicators: Build failure
    Evidence: .sisyphus/evidence/task-3-docker-build.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): scaffold Next.js frontend project`
  - Files: `frontend/**`
  - Pre-commit: `cd frontend && npm run test && npm run build`

- [x] 4. PostgreSQL Schema Design + Alembic Setup

  **What to do**:
  - Design the complete database schema for all 16+ data models (this is the foundation — get it right):
    - **Task & Config**: `tasks` (id, name, doc_type, status, config_json, created_at, updated_at), `task_configs` (id, task_id, template_id, rules_json, style_guide, search_scope, output_format)
    - **Documents**: `source_documents` (id, task_id, filename, file_path, file_type, file_size, uploaded_at), `parsed_documents` (id, source_document_id, task_id, structure_json, raw_text, parsed_at)
    - **Sections**: `sections` (id, task_id, parent_id, title, content, order_index, level, status, current_version_id)
    - **Versions**: `section_versions` (id, section_id, version_number, content, change_source, change_summary, parent_version_id, created_at)
    - **Review**: `review_results` (id, task_id, reviewer_name, status, score, summary, metadata_json, created_at), `review_issues` (id, review_result_id, severity, category, section_id, location_excerpt, description, suggestion, requires_human, resolved, resolved_by)
    - **Evidence**: `evidence_references` (id, section_id, source_chunk_id, claim_text, evidence_text, confidence)
    - **Skills**: `skill_executions` (id, task_id, skill_name, input_json, output_json, status, error_message, started_at, completed_at, llm_tokens_used, llm_cost)
    - **Knowledge**: `templates` (id, name, doc_type, description, outline_structure_json, section_prompts_json, metadata_json, is_default, created_at), `rules` (id, name, category, condition, severity, message, doc_type), `terminology_entries` (id, term, definition, domain, synonyms_json), `knowledge_chunks` (id, source_document_id, chunk_index, content, embedding vector(1536), metadata_json, created_at)
    - **User Interaction**: `user_comments` (id, section_id, task_id, content, comment_type, created_at)
    - **Export**: `export_artifacts` (id, task_id, format, file_path, file_size, created_at)
    - **Audit**: `audit_events` (id, task_id, event_type, actor, details_json, created_at)
  - Status enums: TaskStatus (created, parsing, extracting, planning, awaiting_approval, generating, reviewing, revising, approved, exporting, completed, failed), SectionStatus (draft, reviewing, revision_needed, approved), ReviewSeverity (critical, major, minor, info), ReviewStatus (pass, fail, warning)
  - Set up Alembic with async PostgreSQL connection
  - Create initial migration with all tables
  - Ensure pgvector extension is created in migration
  - Add proper indexes: task_id FKs, section ordering, review result lookups
  - Leave `user_id` fields as nullable for future multi-user support

  **Must NOT do**:
  - Do NOT create ORM model classes yet (that's Task 8) — this task designs the SQL schema
  - Do NOT add complex triggers or stored procedures
  - Do NOT add full-text search indexes (pgvector only)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex schema design requiring careful relationship modeling across 16+ tables
  - **Skills**: [`postgres-patterns`, `database-migrations`]
    - `postgres-patterns`: PostgreSQL schema design, indexing, enum types
    - `database-migrations`: Alembic setup, migration best practices

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 2, 3
  - **Parallel Group**: Wave 1.1 (after Task 1)
  - **Blocks**: Task 8
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - Alembic async configuration: `sqlalchemy.ext.asyncio` in env.py
  - pgvector PostgreSQL extension: `CREATE EXTENSION IF NOT EXISTS vector`
  - PostgreSQL enum types via `CREATE TYPE`

  **WHY Each Reference Matters**:
  - The schema design is foundational — 16+ tables with proper relationships, indexes, and enums. Every subsequent task depends on this being correct.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Alembic migration runs successfully
    Tool: Bash
    Preconditions: PostgreSQL running, DATABASE_URL set
    Steps:
      1. Run `cd backend && alembic upgrade head` — expect no errors
      2. Run `docker compose exec postgres psql -U docagent -d docagent -c "\dt"` — expect 16+ tables
      3. Run `docker compose exec postgres psql -U docagent -d docagent -c "\dT+"` — expect enum types (task_status, section_status, etc.)
      4. Run `docker compose exec postgres psql -U docagent -d docagent -c "SELECT * FROM pg_extension WHERE extname = 'vector';"` — expect 1 row
    Expected Result: Migration applies, all tables created, enums exist, pgvector enabled
    Failure Indicators: Migration fails, missing tables, missing enums, pgvector not installed
    Evidence: .sisyphus/evidence/task-4-migration-up.txt

  Scenario: Migration rollback works
    Tool: Bash
    Preconditions: Migration has been applied
    Steps:
      1. Run `cd backend && alembic downgrade -1` — expect no errors
      2. Run `cd backend && alembic upgrade head` — expect no errors (re-apply)
    Expected Result: Downgrade and re-upgrade both succeed
    Failure Indicators: Downgrade fails, data loss
    Evidence: .sisyphus/evidence/task-4-migration-rollback.txt
  ```

  **Commit**: YES
  - Message: `feat(db): PostgreSQL schema design + Alembic migrations`
  - Files: `backend/alembic.ini`, `backend/alembic/**`

- [x] 5. LLM Abstraction Layer (litellm Adapter)

  **What to do**:
  - Implement `backend/core/llm.py` — unified LLM calling interface:
    - `LLMClient` class wrapping litellm with:
      - `complete(messages, model=None, temperature=0.7, max_tokens=4096, response_format=None) -> LLMResponse`
      - `complete_json(messages, schema: dict, model=None) -> dict` — structured output with JSON mode
      - Model selection from config (default model, review model, generation model — can be different)
      - Retry logic: exponential backoff, max 3 retries on rate limit/timeout
      - Token usage tracking: returns `LLMResponse` with `content`, `tokens_used`, `cost`, `model`
    - `LLMResponse` Pydantic model: `content: str`, `tokens_used: int`, `cost: float`, `model: str`
  - Config in `config.py` (at `backend/config.py`): `LLM_DEFAULT_MODEL`, `LLM_REVIEW_MODEL`, `LLM_API_KEY`, `LLM_API_BASE` (optional)
  - TDD: Test with mock litellm (patch `litellm.acompletion`), test retry logic, test JSON parsing

  **Must NOT do**:
  - Do NOT import openai directly anywhere — ALL LLM calls go through this abstraction
  - Do NOT implement streaming yet (add later)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: LLM integration requiring careful error handling and retry patterns
  - **Skills**: [`cost-aware-llm-pipeline`, `python-patterns`]
    - `cost-aware-llm-pipeline`: Model routing, retry logic, cost tracking patterns
    - `python-patterns`: Async Python patterns, Pydantic models

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 6, 7, 8
  - **Parallel Group**: Wave 1.2
  - **Blocks**: Tasks 12, 13, 14, 15
  - **Blocked By**: Task 2

  **References**:

  **External References**:
  - litellm docs: `litellm.acompletion()` for async, model name format (`gpt-4o`, `azure/gpt-4o`, `ollama/llama3`)
  - litellm JSON mode: `response_format={"type": "json_object"}`

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/core/test_llm.py`
  - [ ] `cd backend && pytest tests/core/test_llm.py -v` → PASS (4+ tests: complete, complete_json, retry, token tracking)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: LLM client returns structured response
    Tool: Bash (pytest)
    Preconditions: litellm mocked in tests
    Steps:
      1. Run `cd backend && pytest tests/core/test_llm.py -v -k "test_complete"` — expect PASS
      2. Run `cd backend && pytest tests/core/test_llm.py -v -k "test_complete_json"` — expect PASS
      3. Run `cd backend && pytest tests/core/test_llm.py -v -k "test_retry"` — expect PASS
    Expected Result: All LLM client tests pass with mocked responses
    Failure Indicators: Tests fail, retry logic not triggered, JSON parsing errors
    Evidence: .sisyphus/evidence/task-5-llm-tests.txt

  Scenario: LLM client handles API errors gracefully
    Tool: Bash (pytest)
    Preconditions: litellm mocked to raise exceptions
    Steps:
      1. Run test that mocks RateLimitError → verify 3 retries with backoff
      2. Run test that mocks malformed JSON response → verify graceful error with clear message
    Expected Result: Retry logic works, errors are descriptive
    Failure Indicators: Unhandled exceptions, infinite retry
    Evidence: .sisyphus/evidence/task-5-llm-error-handling.txt
  ```

  **Commit**: YES
  - Message: `feat(skill): LLM abstraction layer via litellm`
  - Files: `backend/core/llm.py`, `backend/tests/core/test_llm.py`
  - Pre-commit: `cd backend && pytest tests/core/ -v`

- [x] 6. BaseSkill Interface + Skill Registry

  **What to do**:
  - Implement `backend/skills/base.py`:
    - `BaseSkill` abstract class:
      ```python
      class BaseSkill(ABC):
          name: str
          description: str
          input_schema: Type[BaseModel]   # Pydantic model for input validation
          output_schema: Type[BaseModel]  # Pydantic model for output validation
          prerequisites: list[str] = []   # Skills that must run before this one
          
          @abstractmethod
          async def execute(self, context: SkillContext) -> SkillResult
          
          async def validate_output(self, result: SkillResult) -> bool
          
          retry_policy: RetryPolicy = RetryPolicy(max_retries=3, backoff_factor=2)
      ```
    - `SkillContext` model: `task_id`, `section_id` (optional), `input_data: dict`, `llm_client: LLMClient`, `db_session: AsyncSession`
    - `SkillResult` model: `success: bool`, `output: dict`, `error: str | None`, `tokens_used: int`, `execution_time_ms: int`
    - `RetryPolicy` model: `max_retries: int`, `backoff_factor: float`, `retryable_exceptions: list[Type[Exception]]`
  - Implement `backend/skills/registry.py`:
    - `SkillRegistry` class:
      - `register(skill_class: Type[BaseSkill])` — decorator or method to register skills
      - `get(name: str) -> BaseSkill` — retrieve skill by name
      - `list_skills() -> list[SkillInfo]` — list all registered skills with metadata
      - Auto-discovery: scan `skills/` directory for BaseSkill subclasses
    - `SkillInfo` model: `name`, `description`, `input_schema`, `output_schema`, `prerequisites`
  - TDD: Test registry CRUD, test skill validation, test retry wrapper

  **Must NOT do**:
  - Do NOT implement any concrete skills yet
  - Do NOT couple skills to specific LLM providers

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core interface design that 17+ components depend on — must be correct
  - **Skills**: [`python-patterns`, `coding-standards`]
    - `python-patterns`: ABC patterns, Pydantic models, async patterns
    - `coding-standards`: Interface design best practices

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 5, 7, 8
  - **Parallel Group**: Wave 1.2
  - **Blocks**: Tasks 12, 13, 14, 15, 19-26, 28, 39, 49
  - **Blocked By**: Task 2

  **References**:

  **External References**:
  - Python ABC pattern: `from abc import ABC, abstractmethod`
  - Pydantic v2 model inheritance for schema validation

  **WHY Each Reference Matters**:
  - This interface is FROZEN after implementation. All 9+ skills and 8 reviewers implement it. Get it right.

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/skills/test_base.py`, `backend/tests/skills/test_registry.py`
  - [ ] `cd backend && pytest tests/skills/ -v` → PASS (6+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Skill registry registers and retrieves skills
    Tool: Bash (pytest)
    Preconditions: Test skill class implementing BaseSkill
    Steps:
      1. Create a `MockSkill(BaseSkill)` in test
      2. Register it: `registry.register(MockSkill)`
      3. Retrieve it: `skill = registry.get("mock_skill")`
      4. Assert `skill.name == "mock_skill"`
      5. List skills: `skills = registry.list_skills()` — assert length 1
    Expected Result: Registration, retrieval, and listing all work
    Failure Indicators: KeyError on get, wrong skill returned
    Evidence: .sisyphus/evidence/task-6-registry-crud.txt

  Scenario: Skill execute with retry on failure
    Tool: Bash (pytest)
    Preconditions: MockSkill that fails twice then succeeds
    Steps:
      1. Execute skill with retry wrapper
      2. Assert skill was called 3 times (2 failures + 1 success)
      3. Assert final result is success
    Expected Result: Retry mechanism works correctly
    Failure Indicators: Only called once, no retry on transient error
    Evidence: .sisyphus/evidence/task-6-skill-retry.txt
  ```

  **Commit**: YES
  - Message: `feat(skill): BaseSkill interface + skill registry`
  - Files: `backend/skills/base.py`, `backend/skills/registry.py`, `backend/tests/skills/`
  - Pre-commit: `cd backend && pytest tests/skills/ -v`

- [x] 7. ReviewResult/ReviewIssue Schemas + BaseReviewer

  **What to do**:
  - Implement `backend/review/schemas.py`:
    - `ReviewIssue` Pydantic model:
      ```python
      class ReviewIssue(BaseModel):
          severity: Literal["critical", "major", "minor", "info"]
          category: str           # e.g., "structure", "compliance", "technical"
          section_id: str | None  # Which section the issue is in
          location_excerpt: str   # Exact text excerpt where issue found
          description: str        # What's wrong
          suggestion: str         # How to fix it
          requires_human: bool    # Whether auto-fix is unsafe
      ```
    - `ReviewResult` Pydantic model:
      ```python
      class ReviewResult(BaseModel):
          reviewer_name: str
          status: Literal["pass", "fail", "warning"]
          issues: list[ReviewIssue]
          summary: str
          score: int  # 0-100
          metadata: dict = {}
      ```
    - `ReviewAggregation` model: aggregates results from all 8 reviewers, computes overall pass/fail
  - Implement `backend/review/base.py`:
    - `BaseReviewer(BaseSkill)` — extends BaseSkill with reviewer-specific behavior:
      - `reviewer_name: str`
      - `review_criteria: str` — description of what this reviewer checks
      - `async def review(self, sections: list[SectionData], config: ReviewConfig) -> ReviewResult`
      - `_build_prompt(sections, criteria, rules) -> list[dict]` — constructs review prompt
      - `_parse_response(llm_output: str) -> ReviewResult` — parses LLM output into structured ReviewResult
    - `ReviewConfig` model: `rules: list[Rule]`, `style_guide: str | None`, `pass_threshold: int` (default 70)
  - TDD: Test schema validation, test aggregation logic, test prompt building

  **Must NOT do**:
  - Do NOT implement any concrete reviewers yet
  - Do NOT allow reviewers to do multi-turn reasoning (single prompt → structured output)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core schema design that all 8 reviewers and frontend depend on — must be frozen correctly
  - **Skills**: [`python-patterns`, `coding-standards`]
    - `python-patterns`: Pydantic v2 discriminated unions, literal types
    - `coding-standards`: Schema design patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 5, 6, 8
  - **Parallel Group**: Wave 1.2
  - **Blocks**: Tasks 19-26, 27
  - **Blocked By**: Task 2

  **References**:

  **External References**:
  - Pydantic v2 Literal types for enum-like fields
  - JSON schema generation from Pydantic models for LLM structured output

  **WHY Each Reference Matters**:
  - ReviewResult schema is FROZEN after implementation. Frontend, revision loop, quality dashboard, and audit all consume it.

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/review/test_schemas.py`, `backend/tests/review/test_base.py`
  - [ ] `cd backend && pytest tests/review/ -v` → PASS (5+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: ReviewResult schema validates correctly
    Tool: Bash (pytest)
    Steps:
      1. Create valid ReviewResult with 3 issues of different severities
      2. Assert validation passes
      3. Create invalid ReviewResult (severity="unknown") — assert ValidationError
      4. Test ReviewAggregation with mix of pass/fail results — assert overall status correct
    Expected Result: Valid data passes, invalid data raises ValidationError, aggregation logic correct
    Failure Indicators: Schema accepts invalid data, aggregation miscalculates
    Evidence: .sisyphus/evidence/task-7-schema-validation.txt

  Scenario: ReviewAggregation pass/fail logic
    Tool: Bash (pytest)
    Steps:
      1. All reviewers pass → overall pass
      2. One reviewer has critical issue → overall fail
      3. Two reviewers have major issues (above threshold) → overall fail
      4. Only minor issues → overall pass with warnings
    Expected Result: Pass/fail logic matches spec (any critical = fail)
    Failure Indicators: Wrong overall status
    Evidence: .sisyphus/evidence/task-7-aggregation-logic.txt
  ```

  **Commit**: YES
  - Message: `feat(review): ReviewResult/ReviewIssue schemas + BaseReviewer`
  - Files: `backend/review/schemas.py`, `backend/review/base.py`, `backend/tests/review/`
  - Pre-commit: `cd backend && pytest tests/review/ -v`

- [x] 8. Database Models (SQLAlchemy) + Initial Migration

  **What to do**:
  - Implement SQLAlchemy async ORM models in `backend/models/` matching the schema from Task 4:
    - `backend/models/task.py`: Task, TaskConfig
    - `backend/models/document.py`: SourceDocument, ParsedDocument
    - `backend/models/section.py`: Section
    - `backend/models/review.py`: ReviewResultModel, ReviewIssueModel
    - `backend/models/evidence.py`: EvidenceReference
    - `backend/models/skill.py`: SkillExecution
    - `backend/models/knowledge.py`: Rule, TerminologyEntry, KnowledgeChunk (with pgvector Vector column)
    - `backend/models/interaction.py`: UserComment
    - `backend/models/export.py`: ExportArtifact
    - `backend/models/version.py`: SectionVersion
    - `backend/models/template.py`: DocumentTemplate
    - `backend/models/audit.py`: AuditEntry
    - `backend/models/__init__.py`: export all models
  - All models use `mapped_column`, `Mapped` type hints (SQLAlchemy 2.0 style)
  - All models have `id` (UUID), `created_at`, `updated_at` via a `BaseMixin`
  - Proper relationship definitions (Task → Sections, Section → Versions, etc.)
  - Enum types as SQLAlchemy enum columns matching PostgreSQL enums from Task 4
  - Update Alembic migration if needed to match ORM models exactly
  - TDD: Test model instantiation, relationship loading, enum validation

  **Must NOT do**:
  - Do NOT use synchronous SQLAlchemy patterns
  - Do NOT add business logic in models — models are data only

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Many models with relationships, must match schema precisely
  - **Skills**: [`python-patterns`, `postgres-patterns`]
    - `python-patterns`: SQLAlchemy 2.0 async patterns, mapped_column
    - `postgres-patterns`: Relationship modeling, pgvector column types

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 5, 6, 7
  - **Parallel Group**: Wave 1.2
  - **Blocks**: Tasks 9, 10, 16, 37, 38, 40, 41, 44, 47, 48
  - **Blocked By**: Tasks 2, 4

  **References**:

  **Pattern References**:
  - Task 4 schema design — ORM models must match exactly

  **External References**:
  - SQLAlchemy 2.0 mapped_column + Mapped types
  - pgvector SQLAlchemy: `from pgvector.sqlalchemy import Vector`
  - UUID primary keys: `mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)`

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/models/test_models.py`
  - [ ] `cd backend && pytest tests/models/ -v` → PASS (model instantiation + relationship tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All models create and persist correctly
    Tool: Bash (pytest)
    Preconditions: Test database with migrations applied
    Steps:
      1. Create a Task instance, save to DB, retrieve by ID — assert fields match
      2. Create Section with SectionVersion — assert relationship loads correctly
      3. Create ReviewResult with 3 ReviewIssues — assert cascade works
      4. Create KnowledgeChunk with vector embedding — assert pgvector column accepts data
    Expected Result: All CRUD operations work, relationships load, enums validate
    Failure Indicators: SQLAlchemy errors, missing columns, relationship loading failures
    Evidence: .sisyphus/evidence/task-8-model-crud.txt

  Scenario: Enum validation works
    Tool: Bash (pytest)
    Steps:
      1. Create Task with status="created" — expect success
      2. Create Task with status="invalid_status" — expect error
    Expected Result: Valid enum values accepted, invalid rejected
    Failure Indicators: Invalid enum accepted without error
    Evidence: .sisyphus/evidence/task-8-enum-validation.txt
  ```

  **Commit**: YES
  - Message: `feat(db): SQLAlchemy ORM models + migration update`
  - Files: `backend/models/**`, `backend/tests/models/`
  - Pre-commit: `cd backend && pytest tests/ -v`

- [x] 9. LangGraph StateGraph Skeleton + Checkpoint Setup

  **What to do**:
  - Implement `backend/orchestrator/state.py`:
    - `DocumentState` TypedDict — the LangGraph state schema (CONTROL PLANE ONLY per G1):
      ```python
      class DocumentState(TypedDict):
          task_id: str
          current_phase: str  # "parsing", "extracting", "planning", "generating", "reviewing", "revising", "exporting"
          section_ids: list[str]  # IDs only — content lives in DB
          current_section_index: int
          outline_approved: bool
          review_round: int  # tracks revision loop count (max 3 per G8)
          review_passed: bool
          revision_needed_section_ids: list[str]
          final_approved: bool
          error: str | None
          progress_pct: int  # 0-100 for SSE updates
          progress_message: str
      ```
    - NO document content, section text, or review details in state — only IDs and flags
  - Implement `backend/orchestrator/graph.py`:
    - `build_document_graph() -> StateGraph` factory function that creates the full pipeline graph:
      - Nodes: `parse`, `extract_requirements`, `plan_outline`, `await_outline_approval`, `generate_sections`, `run_reviews`, `check_review`, `revise_sections`, `await_final_approval`, `export_document`
      - Edges: linear flow with conditional branching at `check_review` (pass → `await_final_approval`, fail + round < 3 → `revise_sections`, fail + round >= 3 → `await_final_approval`)
      - Each node is a thin wrapper that: reads from DB → calls skill → writes result to DB → updates state IDs/flags
    - Placeholder implementations for each node (just update state, no real logic yet)
  - Implement `backend/orchestrator/checkpoint.py`:
    - Configure `langgraph-checkpoint-postgres` with async PostgreSQL connection
    - Checkpointer saves state after each node execution for resumability
  - TDD: Test graph construction, test state transitions, test checkpoint save/restore

  **Must NOT do**:
  - Do NOT put document content in state (G1) — only IDs and status flags
  - Do NOT implement real skill calls yet — placeholder functions that update state
  - Do NOT add streaming/SSE in this task — that's Task 11

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core orchestration design requiring understanding of LangGraph StateGraph, conditional edges, and checkpointing
  - **Skills**: [`python-patterns`]
    - `python-patterns`: Async Python, TypedDict patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 10, 11
  - **Parallel Group**: Wave 1.3
  - **Blocks**: Tasks 17, 18
  - **Blocked By**: Task 8

  **References**:

  **Pattern References**:
  - `backend/models/task.py` (Task 8) — TaskStatus enum values must match `current_phase` values
  - `backend/skills/base.py` (Task 6) — SkillContext and SkillResult interfaces for node wrappers

  **External References**:
  - LangGraph StateGraph docs: `StateGraph(DocumentState)`, `add_node()`, `add_edge()`, `add_conditional_edges()`
  - LangGraph checkpoint-postgres: `AsyncPostgresSaver` for checkpoint persistence
  - LangGraph human-in-the-loop: `interrupt_before` / `interrupt_after` for approval nodes

  **WHY Each Reference Matters**:
  - Task 8 models define what IDs exist in the DB — state references them by ID
  - Task 6 BaseSkill interface defines how nodes will call skills — wrappers must match
  - LangGraph docs are essential — conditional edges syntax is non-obvious

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/orchestrator/test_graph.py`, `backend/tests/orchestrator/test_state.py`
  - [ ] `cd backend && pytest tests/orchestrator/ -v` → PASS (5+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Graph builds and runs through happy path with placeholders
    Tool: Bash (pytest)
    Preconditions: LangGraph installed, test DB running
    Steps:
      1. Build graph via `build_document_graph()`
      2. Create initial state with task_id="test-123", current_phase="parsing"
      3. Invoke graph with placeholder nodes (each just advances phase)
      4. Assert final state: current_phase="exporting", progress_pct=100
      5. Assert all node names are present in graph.nodes
    Expected Result: Graph executes all nodes in order, state transitions correctly
    Failure Indicators: Missing nodes, wrong phase transitions, graph build error
    Evidence: .sisyphus/evidence/task-9-graph-happy-path.txt

  Scenario: Revision loop respects max 3 rounds (G8)
    Tool: Bash (pytest)
    Steps:
      1. Set state with review_round=0, review_passed=False
      2. Run check_review node — assert routes to revise_sections
      3. Increment review_round to 3, review_passed=False
      4. Run check_review node — assert routes to await_final_approval (not revise again)
    Expected Result: Conditional edge enforces max 3 revision rounds
    Failure Indicators: Loops beyond 3, wrong routing at boundary
    Evidence: .sisyphus/evidence/task-9-revision-loop-max.txt

  Scenario: Checkpoint saves and restores state
    Tool: Bash (pytest)
    Preconditions: PostgreSQL running with checkpoint table
    Steps:
      1. Run graph until parse node completes
      2. Save checkpoint
      3. Load checkpoint — assert state matches (task_id, current_phase="extracting")
    Expected Result: State persists and restores correctly via PostgreSQL
    Failure Indicators: State lost, checkpoint table empty, restore fails
    Evidence: .sisyphus/evidence/task-9-checkpoint.txt
  ```

  **Commit**: YES
  - Message: `feat(orchestrator): LangGraph StateGraph skeleton + checkpoint setup`
  - Files: `backend/orchestrator/state.py`, `backend/orchestrator/graph.py`, `backend/orchestrator/checkpoint.py`, `backend/tests/orchestrator/`
  - Pre-commit: `cd backend && pytest tests/orchestrator/ -v`

- [x] 10. Task Service (CRUD API)

  **What to do**:
  - Implement `backend/services/task_service.py`:
    - `TaskService` class with async methods:
      - `create_task(name, doc_type, config=None) -> Task` — creates task with status "created"
      - `get_task(task_id) -> Task` — with eager-loaded relations (sections, config)
      - `list_tasks(skip, limit, status_filter) -> list[Task]` — paginated, filterable
      - `update_task_status(task_id, new_status) -> Task` — with audit event creation
      - `start_task(task_id) -> Task` — kicks off the LangGraph pipeline (background execution)
      - `delete_task(task_id)` — soft delete or hard delete for MVP
    - Uses async SQLAlchemy session from dependency injection
  - Implement `backend/api/tasks.py`:
    - API router mounted at `/api/v1/tasks`
    - Endpoints:
      - `POST /api/v1/tasks` — create task (body: `{name, doc_type, template_id?}`)
      - `GET /api/v1/tasks` — list tasks (query: `?skip=0&limit=20&status=created`)
      - `GET /api/v1/tasks/{task_id}` — get task detail with sections and config
      - `PUT /api/v1/tasks/{task_id}/status` — update status
      - `POST /api/v1/tasks/{task_id}/start` — start pipeline execution
      - `DELETE /api/v1/tasks/{task_id}` — delete task
    - Pydantic request/response schemas in `backend/schemas/task.py`
  - Implement `backend/schemas/task.py`:
    - `TaskCreate`, `TaskUpdate`, `TaskResponse`, `TaskListResponse`, `TaskDetailResponse`
  - Register router in `backend/api/router.py`
  - TDD: Test each endpoint with httpx.AsyncClient, test service methods with test DB

  **Must NOT do**:
  - Do NOT add authentication middleware (G6)
  - Do NOT implement file upload here — that's Task 16 (Document Service)
  - Do NOT implement the actual pipeline execution logic — `start_task` just triggers background execution of the graph

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Standard CRUD with async patterns, but multiple endpoints and service layer separation
  - **Skills**: [`backend-patterns`, `api-design`, `python-patterns`]
    - `backend-patterns`: FastAPI dependency injection, service layer pattern
    - `api-design`: REST resource naming, status codes, pagination
    - `python-patterns`: Async SQLAlchemy session management

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 9, 11
  - **Parallel Group**: Wave 1.3
  - **Blocks**: Tasks 16, 31
  - **Blocked By**: Task 8

  **References**:

  **Pattern References**:
  - `backend/models/task.py` (Task 8) — Task and TaskConfig ORM models, TaskStatus enum
  - `backend/core/database.py` (Task 2) — async session factory for dependency injection
  - `backend/api/router.py` (Task 2) — where to register the new router

  **External References**:
  - FastAPI dependency injection: `Depends(get_async_session)`
  - FastAPI background tasks: `BackgroundTasks` for pipeline execution
  - Pydantic v2 model_config for response serialization

  **WHY Each Reference Matters**:
  - Task 8 models are the exact ORM classes this service queries — field names must match
  - Task 2 database.py provides the session factory — DI pattern must be consistent
  - `start_task` needs `BackgroundTasks` to trigger LangGraph pipeline without blocking the request

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/api/test_tasks.py`, `backend/tests/services/test_task_service.py`
  - [ ] `cd backend && pytest tests/api/test_tasks.py tests/services/test_task_service.py -v` → PASS (8+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full CRUD lifecycle via API
    Tool: Bash (curl)
    Preconditions: Backend running, DB migrated
    Steps:
      1. POST /api/v1/tasks with {"name":"测试任务","doc_type":"report"} — expect 201, response has "id" and "status":"created"
      2. GET /api/v1/tasks — expect 200, array with 1 item
      3. GET /api/v1/tasks/{id} — expect 200, task detail with name "测试任务"
      4. PUT /api/v1/tasks/{id}/status with {"status":"parsing"} — expect 200, status updated
      5. DELETE /api/v1/tasks/{id} — expect 200 or 204
      6. GET /api/v1/tasks — expect 200, array with 0 items (or task marked deleted)
    Expected Result: All CRUD operations work, proper status codes, Chinese name persists
    Failure Indicators: 500 errors, missing fields, wrong status codes, encoding issues
    Evidence: .sisyphus/evidence/task-10-crud-lifecycle.txt

  Scenario: Task list pagination and filtering
    Tool: Bash (curl)
    Preconditions: 5 tasks created (3 "created", 2 "parsing")
    Steps:
      1. GET /api/v1/tasks?limit=2 — expect 2 items
      2. GET /api/v1/tasks?skip=2&limit=2 — expect 2 items (different from first)
      3. GET /api/v1/tasks?status=parsing — expect 2 items
    Expected Result: Pagination and filtering work correctly
    Failure Indicators: Wrong item count, no filtering effect
    Evidence: .sisyphus/evidence/task-10-pagination-filter.txt
  ```

  **Commit**: YES
  - Message: `feat(api): Task Service CRUD endpoints`
  - Files: `backend/services/task_service.py`, `backend/api/tasks.py`, `backend/schemas/task.py`, `backend/tests/api/test_tasks.py`, `backend/tests/services/test_task_service.py`
  - Pre-commit: `cd backend && pytest tests/api/test_tasks.py tests/services/test_task_service.py -v`

- [x] 11. SSE Progress Endpoint

  **What to do**:
  - Implement `backend/services/progress_service.py`:
    - `ProgressService` — manages SSE event streams per task:
      - In-memory event bus: `dict[str, asyncio.Queue]` mapping task_id → event queue
      - `publish(task_id, event_type, data)` — push event to queue
      - `subscribe(task_id) -> AsyncGenerator[ServerSentEvent]` — yields events as SSE stream
      - Event types: `phase_change`, `progress`, `section_complete`, `review_complete`, `error`, `done`
    - `ProgressEvent` Pydantic model: `event_type: str`, `task_id: str`, `phase: str`, `progress_pct: int`, `message: str`, `data: dict = {}`
  - Implement `backend/api/sse.py`:
    - API router mounted at `/api/v1/tasks/{task_id}/progress`
    - `GET /api/v1/tasks/{task_id}/progress` — returns `EventSourceResponse` (SSE stream)
    - Uses `sse-starlette` library for proper SSE formatting
  - Register router in `backend/api/router.py`
  - TDD: Test event publishing, test SSE endpoint returns proper event stream format

  **Must NOT do**:
  - Do NOT use WebSocket (G5) — SSE only
  - Do NOT persist events to database — in-memory only for MVP
  - Do NOT implement complex event bus (Redis pub/sub) — simple asyncio.Queue

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward SSE implementation with known patterns
  - **Skills**: [`backend-patterns`]
    - `backend-patterns`: FastAPI SSE patterns, async generator patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 9, 10
  - **Parallel Group**: Wave 1.3
  - **Blocks**: Task 17
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `backend/api/router.py` (Task 2) — where to register the SSE router
  - `backend/orchestrator/state.py` (Task 9) — `progress_pct` and `progress_message` fields in state

  **External References**:
  - `sse-starlette` library: `EventSourceResponse` for FastAPI SSE endpoints
  - MDN Server-Sent Events spec: `text/event-stream` content type, `data:` field format

  **WHY Each Reference Matters**:
  - Task 9 state defines the progress fields that this service will broadcast
  - `sse-starlette` provides the correct SSE response formatting — don't implement manually

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/api/test_sse.py`, `backend/tests/services/test_progress_service.py`
  - [ ] `cd backend && pytest tests/api/test_sse.py tests/services/test_progress_service.py -v` → PASS (4+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: SSE endpoint streams progress events
    Tool: Bash (curl)
    Preconditions: Backend running
    Steps:
      1. Start SSE listener in background: `curl -N http://localhost:8000/api/v1/tasks/test-123/progress &`
      2. In separate call, publish event: (via test helper or direct service call)
      3. Assert SSE listener receives: `event: progress\ndata: {"task_id":"test-123","progress_pct":50,...}\n\n`
      4. Kill SSE listener
    Expected Result: Events stream correctly with proper SSE format (event:, data:, double newline)
    Failure Indicators: No events received, wrong format, connection drops
    Evidence: .sisyphus/evidence/task-11-sse-stream.txt

  Scenario: Multiple subscribers receive same events
    Tool: Bash (pytest)
    Steps:
      1. Create 2 subscribers for same task_id
      2. Publish 1 event
      3. Assert both subscribers receive the event
    Expected Result: Fan-out works — all subscribers get all events
    Failure Indicators: Only one subscriber receives event, events lost
    Evidence: .sisyphus/evidence/task-11-sse-fanout.txt
  ```

  **Commit**: YES
  - Message: `feat(api): SSE progress endpoint`
  - Files: `backend/services/progress_service.py`, `backend/api/sse.py`, `backend/tests/api/test_sse.py`, `backend/tests/services/test_progress_service.py`
  - Pre-commit: `cd backend && pytest tests/api/test_sse.py tests/services/test_progress_service.py -v`

### PHASE 2: Core Pipeline (Document → Sections)

- [x] 12. Document Parse Skill (DOCX + PDF + Markdown)

  **What to do**:
  - Implement `backend/skills/parse.py`:
    - `DocumentParseSkill(BaseSkill)` — parses uploaded documents into structured form:
      - `name = "document_parse"`
      - Input: `ParseInput(file_path: str, file_type: Literal["docx","pdf","md"])`
      - Output: `ParseOutput(structure: list[SectionNode], raw_text: str, metadata: dict)`
      - `SectionNode`: `title: str`, `level: int`, `content: str`, `children: list[SectionNode]`
    - DOCX parser: `python-docx` — extract headings (by style), paragraphs, tables (as text)
    - PDF parser: `pdfplumber` — extract text by page, detect headings by font size heuristic
    - Markdown parser: `markdown` lib or regex — split by `#` heading levels
    - Common post-processing: build section tree from flat heading list, strip empty sections
  - Save parsed result to `parsed_documents` table via DB session
  - Register skill in registry
  - TDD: Test each parser with sample files, test section tree building

  **Must NOT do**:
  - Do NOT extract images or embedded media — text only for MVP
  - Do NOT use LLM for parsing — deterministic parsing only
  - Do NOT support scanned PDFs (no OCR)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple file format parsers with tree-building logic
  - **Skills**: [`python-patterns`]
    - `python-patterns`: File I/O patterns, data structure building

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 13, 14, 15
  - **Parallel Group**: Wave 2.1
  - **Blocks**: Tasks 16, 17
  - **Blocked By**: Tasks 5, 6

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill interface to implement
  - `backend/skills/registry.py` (Task 6) — register with `@registry.register`
  - `backend/models/document.py` (Task 8) — ParsedDocument model for DB persistence

  **External References**:
  - `python-docx`: `Document(path).paragraphs` for text, `paragraph.style.name` for heading detection
  - `pdfplumber`: `pdf.pages[i].extract_text()` for text extraction
  - Python `markdown` or regex-based heading parser for `.md` files

  **WHY Each Reference Matters**:
  - Task 6 BaseSkill is the FROZEN interface — `execute()` signature must match exactly
  - Task 8 ParsedDocument model defines DB schema — output must match `structure_json` and `raw_text` columns

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/skills/test_parse.py`
  - [ ] `cd backend && pytest tests/skills/test_parse.py -v` → PASS (6+ tests: docx, pdf, md, tree building, empty doc, registration)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Parse a DOCX file into section tree
    Tool: Bash (pytest)
    Preconditions: Sample DOCX with 3 headings (H1, H2, H2) + paragraphs under each
    Steps:
      1. Create sample DOCX programmatically in test (python-docx)
      2. Call DocumentParseSkill.execute() with file path
      3. Assert output.structure has 1 root node with 2 children
      4. Assert root node title matches H1 text
      5. Assert raw_text contains all paragraph text
    Expected Result: Section tree built correctly from DOCX headings
    Failure Indicators: Wrong tree structure, missing text, level mismatch
    Evidence: .sisyphus/evidence/task-12-parse-docx.txt

  Scenario: Parse a Markdown file into section tree
    Tool: Bash (pytest)
    Steps:
      1. Create temp .md file with: `# Title\n\nPara1\n\n## Section A\n\nPara2\n\n## Section B\n\nPara3`
      2. Call skill with file_type="md"
      3. Assert 1 root (level 1) with 2 children (level 2)
    Expected Result: Markdown headings parsed into correct tree
    Failure Indicators: All sections at same level, missing content
    Evidence: .sisyphus/evidence/task-12-parse-md.txt

  Scenario: Empty document handled gracefully
    Tool: Bash (pytest)
    Steps:
      1. Create empty DOCX file
      2. Call skill — should NOT raise exception
      3. Assert output.structure is empty list, raw_text is ""
    Expected Result: Graceful handling, no crash
    Failure Indicators: Exception raised, None returned
    Evidence: .sisyphus/evidence/task-12-parse-empty.txt
  ```

  **Commit**: YES
  - Message: `feat(skill): Document Parse Skill (DOCX, PDF, Markdown)`
  - Files: `backend/skills/parse.py`, `backend/tests/skills/test_parse.py`, test fixtures
  - Pre-commit: `cd backend && pytest tests/skills/test_parse.py -v`

- [x] 13. Requirement Extraction Skill

  **What to do**:
  - Implement `backend/skills/extract_requirements.py`:
    - `RequirementExtractionSkill(BaseSkill)` — uses LLM to extract structured requirements from parsed document:
      - `name = "requirement_extraction"`
      - Input: `ExtractInput(task_id: str, parsed_text: str, doc_type: str)`
      - Output: `ExtractOutput(requirements: list[Requirement], constraints: list[str], key_terms: list[str])`
      - `Requirement`: `id: str`, `description: str`, `category: str`, `priority: Literal["must","should","nice"]`, `source_excerpt: str`
    - LLM prompt: pass parsed text + doc_type → ask LLM to extract requirements in JSON format
    - Use `LLMClient.complete_json()` (Task 5) for structured output
    - Save extracted requirements to task config or separate table
  - Register skill in registry
  - TDD: Mock LLM response, test extraction parsing, test edge cases (no requirements found)

  **Must NOT do**:
  - Do NOT use multi-turn extraction — single prompt only (G9 spirit)
  - Do NOT hardcode prompts — store prompt template as configurable string

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: LLM-driven skill with structured output parsing
  - **Skills**: [`python-patterns`, `cost-aware-llm-pipeline`]
    - `python-patterns`: Pydantic model validation
    - `cost-aware-llm-pipeline`: LLM prompt patterns for structured extraction

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 12, 14, 15
  - **Parallel Group**: Wave 2.1
  - **Blocks**: Task 17
  - **Blocked By**: Tasks 5, 6

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill.execute() interface
  - `backend/core/llm.py` (Task 5) — LLMClient.complete_json() for structured LLM output

  **WHY Each Reference Matters**:
  - Task 5 LLMClient is the ONLY way to call LLMs (G2) — use complete_json for JSON extraction
  - Task 6 BaseSkill defines how this skill is invoked by the orchestrator

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/skills/test_extract_requirements.py`
  - [ ] `cd backend && pytest tests/skills/test_extract_requirements.py -v` → PASS (4+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Extract requirements from sample document text
    Tool: Bash (pytest)
    Preconditions: LLM mocked to return structured JSON with 3 requirements
    Steps:
      1. Call skill with sample parsed text about a "系统设计报告"
      2. Assert output.requirements has 3 items
      3. Assert each requirement has id, description, category, priority
      4. Assert output.key_terms is non-empty list
    Expected Result: Requirements extracted with correct structure
    Failure Indicators: Empty requirements, missing fields, JSON parse error
    Evidence: .sisyphus/evidence/task-13-extract-requirements.txt

  Scenario: Handle document with no extractable requirements
    Tool: Bash (pytest)
    Preconditions: LLM mocked to return empty requirements list
    Steps:
      1. Call skill with minimal text (e.g., "简介文档")
      2. Assert output.requirements is empty list (not None, not error)
      3. Assert skill result is still success=True
    Expected Result: Graceful empty result
    Failure Indicators: Exception, None output, success=False
    Evidence: .sisyphus/evidence/task-13-extract-empty.txt
  ```

  **Commit**: YES
  - Message: `feat(skill): Requirement Extraction Skill`
  - Files: `backend/skills/extract_requirements.py`, `backend/tests/skills/test_extract_requirements.py`
  - Pre-commit: `cd backend && pytest tests/skills/test_extract_requirements.py -v`

- [x] 14. Outline Planning Skill

  **What to do**:
  - Implement `backend/skills/outline.py`:
    - `OutlinePlanningSkill(BaseSkill)` — uses LLM to generate document outline from requirements:
      - `name = "outline_planning"`
      - Input: `OutlineInput(task_id: str, requirements: list[Requirement], doc_type: str, template_schema: dict | None)`
      - Output: `OutlineOutput(sections: list[OutlineSection])`
      - `OutlineSection`: `title: str`, `level: int`, `description: str`, `target_word_count: int`, `depends_on: list[str]` (for future parallel generation), `children: list[OutlineSection]`
    - LLM prompt: pass requirements + optional template schema → generate hierarchical outline
    - If template_schema provided, outline must follow its structure (sections, required headings)
    - Save outline sections to `sections` table with status "draft"
  - Register skill in registry
  - TDD: Mock LLM, test outline generation, test template conformance, test section persistence

  **Must NOT do**:
  - Do NOT implement parallel section generation yet — just set `depends_on` field
  - Do NOT auto-approve outline — that's Task 18 (human-in-the-loop)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: LLM-driven outline generation with template conformance logic
  - **Skills**: [`python-patterns`, `cost-aware-llm-pipeline`]
    - `python-patterns`: Tree data structures, Pydantic nesting
    - `cost-aware-llm-pipeline`: LLM structured output for hierarchical data

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 12, 13, 15
  - **Parallel Group**: Wave 2.1
  - **Blocks**: Task 17
  - **Blocked By**: Tasks 5, 6

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill interface
  - `backend/core/llm.py` (Task 5) — LLMClient.complete_json()
  - `backend/models/section.py` (Task 8) — Section model with level, order_index, parent_id

  **WHY Each Reference Matters**:
  - Task 8 Section model defines the DB schema — outline must produce fields that match (title, level, order_index, parent_id)
  - Template schema drives the outline structure — if provided, LLM must follow it

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/skills/test_outline.py`
  - [ ] `cd backend && pytest tests/skills/test_outline.py -v` → PASS (4+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Generate outline from requirements
    Tool: Bash (pytest)
    Preconditions: LLM mocked to return 5-section outline (1 root, 4 children)
    Steps:
      1. Call skill with 3 sample requirements and doc_type="report"
      2. Assert output.sections has hierarchical structure
      3. Assert each section has title, level, description, target_word_count
      4. Verify sections saved to DB with correct parent_id relationships
    Expected Result: Outline generated with proper hierarchy and DB persistence
    Failure Indicators: Flat structure, missing fields, DB save failure
    Evidence: .sisyphus/evidence/task-14-outline-generation.txt

  Scenario: Template-constrained outline follows schema
    Tool: Bash (pytest)
    Preconditions: Template schema with required sections ["概述", "技术方案", "风险分析"]
    Steps:
      1. Call skill with template_schema containing required sections
      2. Assert output.sections includes all required sections
      3. Assert LLM prompt includes template structure guidance
    Expected Result: Outline conforms to template
    Failure Indicators: Missing required sections, template ignored
    Evidence: .sisyphus/evidence/task-14-outline-template.txt
  ```

  **Commit**: YES
  - Message: `feat(skill): Outline Planning Skill`
  - Files: `backend/skills/outline.py`, `backend/tests/skills/test_outline.py`
  - Pre-commit: `cd backend && pytest tests/skills/test_outline.py -v`

- [x] 15. Section Writing Skill

  **What to do**:
  - Implement `backend/skills/write_section.py`:
    - `SectionWritingSkill(BaseSkill)` — uses LLM to write content for a single section:
      - `name = "section_writing"`
      - Input: `WriteInput(task_id: str, section_id: str, section_title: str, section_description: str, target_word_count: int, context: SectionContext)`
      - `SectionContext`: `requirements: list[str]`, `preceding_sections: list[SectionSummary]`, `style_guide: str | None`, `knowledge_excerpts: list[str]` (from RAG, empty for now)
      - Output: `WriteOutput(content: str, word_count: int, references_used: list[str])`
    - LLM prompt: section title + description + context → write section content
    - Save content as new SectionVersion (version_number=1) in `section_versions` table
    - Sequential execution: called once per section by orchestrator (not parallel for MVP)
  - Register skill in registry
  - TDD: Mock LLM, test content generation, test version creation, test context building

  **Must NOT do**:
  - Do NOT implement parallel section writing — sequential for MVP, `depends_on` for future
  - Do NOT implement RAG integration yet — `knowledge_excerpts` will be empty until Task 39

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core generation skill with context management and version tracking
  - **Skills**: [`python-patterns`, `cost-aware-llm-pipeline`]
    - `python-patterns`: Async patterns, Pydantic models
    - `cost-aware-llm-pipeline`: LLM prompt engineering for long-form generation

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 12, 13, 14
  - **Parallel Group**: Wave 2.1
  - **Blocks**: Tasks 17, 41
  - **Blocked By**: Tasks 5, 6

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill interface
  - `backend/core/llm.py` (Task 5) — LLMClient.complete()
  - `backend/models/version.py` (Task 8, 37) — SectionVersion model (version_number, content, change_source)

  **WHY Each Reference Matters**:
  - Task 8 SectionVersion model: each generation creates version_number=1, change_source="generation"
  - Context from preceding sections prevents contradictions between sections

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/skills/test_write_section.py`
  - [ ] `cd backend && pytest tests/skills/test_write_section.py -v` → PASS (4+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Write a section and create SectionVersion
    Tool: Bash (pytest)
    Preconditions: LLM mocked to return 500-word content, section exists in DB
    Steps:
      1. Call skill with section_title="技术方案", target_word_count=500
      2. Assert output.content is non-empty string
      3. Assert output.word_count is close to target (within 50% tolerance)
       4. Query DB: SectionVersion created for section with version_number=1
       5. Assert SectionVersion.change_source="generation"
    Expected Result: Content generated and persisted as version
    Failure Indicators: Empty content, no version in DB, version_number wrong
    Evidence: .sisyphus/evidence/task-15-write-section.txt

  Scenario: Context from preceding sections included in prompt
    Tool: Bash (pytest)
    Steps:
      1. Create 2 preceding sections with summaries
      2. Call skill for 3rd section
      3. Assert LLM prompt includes preceding section summaries (via mock inspection)
    Expected Result: Preceding context passed to LLM for coherence
    Failure Indicators: LLM called without preceding context
    Evidence: .sisyphus/evidence/task-15-write-context.txt
  ```

  **Commit**: YES
  - Message: `feat(skill): Section Writing Skill`
  - Files: `backend/skills/write_section.py`, `backend/tests/skills/test_write_section.py`
  - Pre-commit: `cd backend && pytest tests/skills/test_write_section.py -v`

- [x] 16. Document Service (Upload, Parse, Sections CRUD)

  **What to do**:
  - Implement `backend/services/document_service.py`:
    - `DocumentService` class:
      - `upload_document(task_id, file: UploadFile) -> SourceDocument` — save file to `uploads/{task_id}/`, create SourceDocument record
      - `get_source_documents(task_id) -> list[SourceDocument]` — list uploaded files for a task
      - `get_parsed_document(task_id) -> ParsedDocument` — get parsed structure
      - `get_sections(task_id) -> list[Section]` — get all sections with current version content
      - `get_section(section_id) -> Section` — get single section with all versions
      - `update_section_content(section_id, content, change_summary) -> SectionVersion` — creates new version
    - File storage: local filesystem under `uploads/` directory (abstracted for future MinIO)
    - Upload validation: max 50MB, allowed types (docx, pdf, md)
  - Implement `backend/api/documents.py`:
    - API router at `/api/v1/tasks/{task_id}/documents`
    - Endpoints:
      - `POST /api/v1/tasks/{task_id}/documents/upload` — multipart file upload
      - `GET /api/v1/tasks/{task_id}/documents` — list source documents
      - `GET /api/v1/tasks/{task_id}/sections` — list sections with current content
      - `GET /api/v1/tasks/{task_id}/sections/{section_id}` — section detail with versions
      - `PUT /api/v1/tasks/{task_id}/sections/{section_id}` — update section content (human edit)
  - Pydantic schemas in `backend/schemas/document.py`
  - Register router in router.py
  - TDD: Test upload, retrieval, section CRUD, file size validation

  **Must NOT do**:
  - Do NOT implement complex file storage abstraction — simple local filesystem with path helper
  - Do NOT trigger parsing automatically on upload — orchestrator does that

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: File upload handling + CRUD with version management
  - **Skills**: [`backend-patterns`, `api-design`, `python-patterns`]
    - `backend-patterns`: File upload in FastAPI, service layer
    - `api-design`: REST nested resources, multipart upload
    - `python-patterns`: File I/O, path management

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Task 17 (partially), Task 18 (no)
  - **Parallel Group**: Wave 2.2 (can start once Task 8, 12 are done)
  - **Blocks**: Task 17, Task 34
  - **Blocked By**: Tasks 8, 12

  **References**:

  **Pattern References**:
  - `backend/models/document.py` (Task 8) — SourceDocument, ParsedDocument models
  - `backend/models/section.py` (Task 8) — Section model
  - `backend/models/version.py` (Task 8, 37) — SectionVersion model
  - `backend/api/tasks.py` (Task 10) — follow same router + service pattern

  **WHY Each Reference Matters**:
  - Task 10 established the router/service pattern — this task must follow the same DI and response shape
  - Task 8 models define exact column names — service must match

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/api/test_documents.py`, `backend/tests/services/test_document_service.py`
  - [ ] `cd backend && pytest tests/api/test_documents.py tests/services/test_document_service.py -v` → PASS (8+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Upload a DOCX file and retrieve it
    Tool: Bash (curl)
    Preconditions: Backend running, task exists
    Steps:
      1. POST /api/v1/tasks/{task_id}/documents/upload with multipart DOCX file — expect 201
      2. GET /api/v1/tasks/{task_id}/documents — expect array with 1 item, filename matches
      3. Verify file exists on filesystem under uploads/{task_id}/
    Expected Result: File uploaded, persisted to disk and DB
    Failure Indicators: 500 error, file not saved, DB record missing
    Evidence: .sisyphus/evidence/task-16-upload-docx.txt

  Scenario: Reject oversized file upload (>50MB)
    Tool: Bash (curl)
    Steps:
      1. Create a 60MB dummy file
      2. POST upload — expect 413 or 400 with error message about size limit
    Expected Result: Upload rejected with clear error
    Failure Indicators: File accepted, no error message
    Evidence: .sisyphus/evidence/task-16-upload-reject-size.txt

  Scenario: Section content update creates new version
    Tool: Bash (curl)
    Preconditions: Task with sections already generated
    Steps:
      1. PUT /api/v1/tasks/{task_id}/sections/{id} with {"content":"更新内容","change_summary":"手动修改"}
      2. GET section — assert content is "更新内容"
      3. Assert version_number incremented (was 1, now 2)
    Expected Result: Content updated, new version created
    Failure Indicators: Version not incremented, old content returned
    Evidence: .sisyphus/evidence/task-16-section-update.txt
  ```

  **Commit**: YES
  - Message: `feat(api): Document Service + upload + sections CRUD`
  - Files: `backend/services/document_service.py`, `backend/api/documents.py`, `backend/schemas/document.py`, `backend/tests/api/test_documents.py`
  - Pre-commit: `cd backend && pytest tests/api/test_documents.py -v`

- [x] 17. LangGraph Generation Pipeline (Parse → Extract → Outline → Write)

  **What to do**:
  - Wire up the LangGraph skeleton (Task 9) with real skill implementations:
    - `parse` node: calls DocumentParseSkill (Task 12) — reads uploaded file, saves ParsedDocument
    - `extract_requirements` node: calls RequirementExtractionSkill (Task 13) — extracts from parsed text
    - `plan_outline` node: calls OutlinePlanningSkill (Task 14) — generates outline sections
    - `generate_sections` node: iterates through sections sequentially, calls SectionWritingSkill (Task 15) for each
  - Each node:
    1. Reads input data from DB (using task_id from state)
    2. Creates SkillContext, calls skill.execute()
    3. Saves SkillExecution record (tokens used, cost, timing)
    4. Writes output to DB
    5. Updates state (IDs, progress_pct, progress_message)
    6. Publishes SSE event via ProgressService (Task 11)
  - Update progress percentages: parse=10%, extract=20%, outline=40%, sections=40-90% (proportional per section)
  - Error handling: if any skill fails after retries, set state.error, transition to error handling
  - TDD: Integration test with mocked LLM — run full pipeline, verify DB state at each stage

  **Must NOT do**:
  - Do NOT implement review nodes yet — only generation pipeline
  - Do NOT implement parallel section generation — sequential loop
  - Do NOT bypass the skill interface — all logic goes through BaseSkill.execute()

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Integration of 4 skills into orchestrator with state management, DB I/O, and error handling
  - **Skills**: [`python-patterns`, `backend-patterns`]
    - `python-patterns`: Async orchestration, error handling patterns
    - `backend-patterns`: Service layer integration, transaction management

  **Parallelization**:
  - **Can Run In Parallel**: NO — depends on all Wave 2.1 tasks
  - **Parallel Group**: Wave 2.2
  - **Blocks**: Tasks 18, 19-26
  - **Blocked By**: Tasks 9, 11, 12, 13, 14, 15, 16

  **References**:

  **Pattern References**:
  - `backend/orchestrator/graph.py` (Task 9) — placeholder nodes to replace with real implementations
  - `backend/orchestrator/state.py` (Task 9) — DocumentState fields to update
  - `backend/skills/parse.py` (Task 12) — ParseSkill to call in parse node
  - `backend/skills/extract_requirements.py` (Task 13) — ExtractSkill for extract node
  - `backend/skills/outline.py` (Task 14) — OutlineSkill for plan_outline node
  - `backend/skills/write_section.py` (Task 15) — WritingSkill for generate_sections node
  - `backend/services/progress_service.py` (Task 11) — publish SSE events
  - `backend/models/skill.py` (Task 8) — SkillExecution model for tracking

  **WHY Each Reference Matters**:
  - This is the integration task — it connects ALL previous tasks into a working pipeline
  - Each node wrapper follows the same pattern: read DB → call skill → write DB → update state → publish SSE
  - SkillExecution tracking is essential for cost monitoring and debugging

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/orchestrator/test_pipeline.py`
  - [ ] `cd backend && pytest tests/orchestrator/test_pipeline.py -v` → PASS (5+ tests: full pipeline, parse failure, extract failure, progress events)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full generation pipeline runs end-to-end
    Tool: Bash (pytest)
    Preconditions: All skills registered, LLM mocked, test DB, uploaded DOCX file
    Steps:
      1. Create task, upload sample DOCX
      2. Start pipeline via graph invocation
      3. Assert state progresses: parsing → extracting → planning → generating
      4. Assert DB has: ParsedDocument, extracted requirements in config, Section rows, SectionVersion rows
      5. Assert SkillExecution records created for each skill call
      6. Assert final state: progress_pct=90 (waiting for review)
    Expected Result: Pipeline completes, all artifacts in DB
    Failure Indicators: Pipeline stalls, missing DB records, wrong state transitions
    Evidence: .sisyphus/evidence/task-17-pipeline-e2e.txt

  Scenario: Skill failure triggers error state
    Tool: Bash (pytest)
    Preconditions: LLM mocked to fail on outline skill (after retries)
    Steps:
      1. Start pipeline
      2. Parse and extract succeed
      3. Outline skill fails after 3 retries
      4. Assert state.error is set with descriptive message
      5. Assert task status updated to "failed"
    Expected Result: Graceful error with clear message, no partial corrupt state
    Failure Indicators: Unhandled exception, state stuck, no error message
    Evidence: .sisyphus/evidence/task-17-pipeline-error.txt

  Scenario: SSE events published during pipeline
    Tool: Bash (pytest)
    Preconditions: ProgressService available
    Steps:
      1. Subscribe to task progress events
      2. Run pipeline
      3. Assert events received: phase_change (parse, extract, outline, generate), progress updates
    Expected Result: Client receives real-time progress
    Failure Indicators: No events, wrong event types
    Evidence: .sisyphus/evidence/task-17-pipeline-sse.txt
  ```

  **Commit**: YES
  - Message: `feat(orchestrator): generation pipeline (parse → extract → outline → write)`
  - Files: `backend/orchestrator/graph.py` (updated), `backend/tests/orchestrator/test_pipeline.py`
  - Pre-commit: `cd backend && pytest tests/orchestrator/ -v`

- [x] 18. Human-in-the-Loop: Outline Approval Interrupt

  **What to do**:
  - Implement outline approval interrupt in LangGraph pipeline:
    - After `plan_outline` node, pipeline pauses at `await_outline_approval` node
    - `await_outline_approval` uses LangGraph's `interrupt` mechanism to pause execution
    - State is checkpointed (Task 9 checkpointer)
  - Implement approval API endpoint in `backend/api/tasks.py`:
    - `POST /api/v1/tasks/{task_id}/approve-outline` — body: `{approved: bool, feedback?: str}`
    - If approved: resume pipeline from checkpoint → continue to `generate_sections`
    - If rejected: update outline sections based on feedback, re-run `plan_outline`, pause again
    - Rejection also creates an audit event
  - Implement `backend/services/approval_service.py`:
    - `ApprovalService.approve_outline(task_id, approved, feedback)` — handles the approval logic
    - Resumes LangGraph execution from checkpoint
  - TDD: Test approval flow, rejection + re-plan flow, checkpoint resume

  **Must NOT do**:
  - Do NOT implement final review approval here — that's Task 30
  - Do NOT allow more than 3 outline rejections — force approval after max

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: LangGraph interrupt/resume mechanics with API integration
  - **Skills**: [`python-patterns`, `backend-patterns`]
    - `python-patterns`: Async flow control
    - `backend-patterns`: API endpoint design for async workflow resumption

  **Parallelization**:
  - **Can Run In Parallel**: NO — depends on Task 17
  - **Parallel Group**: Wave 2.2 (after Task 17)
  - **Blocks**: Task 29
  - **Blocked By**: Task 17

  **References**:

  **Pattern References**:
  - `backend/orchestrator/graph.py` (Task 9/17) — `await_outline_approval` node placeholder
  - `backend/orchestrator/checkpoint.py` (Task 9) — checkpoint save/restore for interrupt
  - `backend/models/audit.py` (Task 8) — AuditEntry for recording approvals/rejections

  **External References**:
  - LangGraph human-in-the-loop: `interrupt_before=["await_outline_approval"]` in graph compilation
  - LangGraph resume: `graph.ainvoke(None, config={"thread_id": task_id})` to resume from checkpoint

  **WHY Each Reference Matters**:
  - LangGraph interrupt/resume is the specific API for pausing and continuing the graph — must use correctly
  - Checkpoint (Task 9) ensures state survives server restarts between approval

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `backend/tests/orchestrator/test_approval.py`, `backend/tests/api/test_approval.py`
  - [ ] `cd backend && pytest tests/orchestrator/test_approval.py tests/api/test_approval.py -v` → PASS (5+ tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Pipeline pauses for outline approval
    Tool: Bash (curl + pytest)
    Preconditions: Pipeline running, reached outline phase
    Steps:
      1. Start task pipeline
      2. Assert pipeline pauses after outline generation (state: outline_approved=False)
      3. GET /api/v1/tasks/{task_id} — assert status is "awaiting_approval"
      4. GET /api/v1/tasks/{task_id}/sections — assert outline sections visible
    Expected Result: Pipeline paused, outline visible for review
    Failure Indicators: Pipeline continues without pausing, no outline in response
    Evidence: .sisyphus/evidence/task-18-pause-outline.txt

  Scenario: Approve outline resumes pipeline
    Tool: Bash (curl)
    Steps:
      1. POST /api/v1/tasks/{task_id}/approve-outline with {"approved":true}
      2. Assert 200 response
      3. Wait 2s, GET task — assert status moved past "awaiting_approval" to "generating"
    Expected Result: Pipeline resumes after approval
    Failure Indicators: Pipeline stays paused, 500 error on approve
    Evidence: .sisyphus/evidence/task-18-approve-resume.txt

  Scenario: Reject outline triggers re-planning
    Tool: Bash (curl)
    Steps:
      1. POST /api/v1/tasks/{task_id}/approve-outline with {"approved":false,"feedback":"缺少风险分析章节"}
      2. Assert pipeline re-runs plan_outline node
      3. Assert pipeline pauses again for approval
      4. Assert audit event created with rejection reason
    Expected Result: Re-planning occurs, new outline generated
    Failure Indicators: Pipeline doesn't re-run, same outline shown
    Evidence: .sisyphus/evidence/task-18-reject-replan.txt
  ```

  **Commit**: YES
  - Message: `feat(orchestrator): human-in-the-loop outline approval`
  - Files: `backend/services/approval_service.py`, `backend/api/tasks.py` (updated), `backend/tests/orchestrator/test_approval.py`
  - Pre-commit: `cd backend && pytest tests/orchestrator/ -v`

### PHASE 3: Review Engine (8 Reviewers + Revision Loop)

> **Reviewer Pattern (shared by Tasks 19-26):**
> Each reviewer extends `BaseReviewer(BaseSkill)` from Task 7. Each:
> 1. Receives sections + task config (rules, style guide, template)
> 2. Builds a review prompt with specific criteria
> 3. Calls LLM via `LLMClient.complete_json()` for structured output
> 4. Parses response into `ReviewResult` with `list[ReviewIssue]`
> 5. Each issue has `severity`, `category`, `section_id`, `location_excerpt`, `description`, `suggestion`
> 6. Registers in skill registry
> All 8 reviewers can run in PARALLEL (Waves 3.1 + 3.2).

- [x] 19. Structure Reviewer

  **What to do**:
  - Implement `backend/review/structure_reviewer.py`:
    - `StructureReviewer(BaseReviewer)` — checks document structure completeness:
      - `reviewer_name = "structure"`
      - Checks: section hierarchy correctness, required sections present (per template), section ordering logic, heading level consistency, section length balance (no empty or stub sections)
      - Criteria prompt: "检查文档结构：章节层级是否正确、必需章节是否齐全、章节顺序是否合理、标题层级是否一致、各章节篇幅是否均衡"
  - TDD: Mock LLM, test with well-structured and poorly-structured sample documents

  **Must NOT do**:
  - Do NOT check content quality — only structural aspects
  - Do NOT use multi-turn review (G9)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES — with Tasks 20, 21, 22, 23, 24, 25, 26
  - **Parallel Group**: Wave 3.1
  - **Blocks**: Task 27
  - **Blocked By**: Tasks 6, 7, 17

  **References**:
  - `backend/review/base.py` (Task 7) — BaseReviewer interface, ReviewResult/ReviewIssue schemas
  - `backend/core/llm.py` (Task 5) — LLMClient.complete_json()
  - `backend/models/review.py` (Task 8) — ReviewResultModel for DB persistence

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_structure_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect missing required section
    Tool: Bash (pytest)
    Preconditions: Template requires ["概述","技术方案","总结"], document has only ["概述","技术方案"]
    Steps:
      1. LLM mocked to return issue for missing "总结"
      2. Call reviewer
      3. Assert ReviewResult has 1 issue with severity="major", category="structure"
      4. Assert issue.description mentions "总结"
    Expected Result: Missing section detected with clear suggestion
    Evidence: .sisyphus/evidence/task-19-structure-missing.txt

  Scenario: Well-structured document passes
    Tool: Bash (pytest)
    Steps:
      1. LLM mocked to return no issues
      2. Assert ReviewResult.status="pass", issues=[]
    Expected Result: Clean document passes review
    Evidence: .sisyphus/evidence/task-19-structure-pass.txt
  ```

  **Commit**: YES (grouped with Tasks 20-22)
  - Message: `feat(review): Structure, Compliance, Technical, Evidence reviewers`
  - Files: `backend/review/structure_reviewer.py`, `backend/tests/review/test_structure_reviewer.py`

- [x] 20. Compliance Reviewer

  **What to do**:
  - Implement `backend/review/compliance_reviewer.py`:
    - `ComplianceReviewer(BaseReviewer)` — checks format rules and hard constraints:
      - `reviewer_name = "compliance"`
      - Checks: format rule violations, mandatory field presence, naming conventions, numbering formats, table/figure labeling, terminology consistency with rules DB
      - Uses `rules` from task config to check against (Rule model from Task 8)
      - Criteria: "检查合规性：格式规则是否遵守、必填字段是否齐全、编号格式是否正确、表格图片是否标注、术语是否与规则库一致"

  **Must NOT do**:
  - Do NOT check subjective quality — only objective rule violations

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**: Same as Task 19 (Wave 3.1, parallel with all reviewers)
  **Blocked By**: Tasks 6, 7, 17

  **References**: Same as Task 19 + `backend/models/knowledge.py` (Task 8) — Rule model for compliance rules

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_compliance_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect compliance violations
    Tool: Bash (pytest)
    Preconditions: Rules include "all tables must be numbered"
    Steps:
      1. LLM mocked to find 2 unnumbered tables
      2. Assert 2 issues, each with section_id and location_excerpt pointing to table text
    Expected Result: Violations located with excerpts
    Evidence: .sisyphus/evidence/task-20-compliance-violation.txt

  Scenario: No rules configured — still runs without error
    Tool: Bash (pytest)
    Steps:
      1. Call with empty rules list
      2. Assert reviewer completes with status="pass" or generic check only
    Expected Result: Graceful handling when no rules configured
    Evidence: .sisyphus/evidence/task-20-compliance-no-rules.txt
  ```

  **Commit**: YES (grouped with Tasks 19, 21, 22)
  - Files: `backend/review/compliance_reviewer.py`, `backend/tests/review/test_compliance_reviewer.py`

- [x] 21. Technical Reviewer

  **What to do**:
  - Implement `backend/review/technical_reviewer.py`:
    - `TechnicalReviewer(BaseReviewer)` — checks technical correctness:
      - `reviewer_name = "technical"`
      - Checks: logical argument completeness, technical claims accuracy, methodology soundness, calculation correctness, technical terminology usage, specification references validity
      - Criteria: "检查技术正确性：论证逻辑是否完整、技术论述是否准确、方法论是否合理、计算是否正确、技术术语使用是否恰当"

  **Must NOT do**:
  - Do NOT verify external references (no web access) — only internal logical consistency

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**: Same as Task 19 (Wave 3.1)
  **Blocked By**: Tasks 6, 7, 17

  **References**: Same as Task 19

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_technical_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect logical gap in technical argument
    Tool: Bash (pytest)
    Steps:
      1. LLM mocked to find 1 issue: "技术方案缺少性能基准测试说明"
      2. Assert issue has severity="major", section_id pointing to technical section
    Expected Result: Technical gap identified with section reference
    Evidence: .sisyphus/evidence/task-21-technical-gap.txt
  ```

  **Commit**: YES (grouped with Tasks 19, 20, 22)
  - Files: `backend/review/technical_reviewer.py`, `backend/tests/review/test_technical_reviewer.py`

- [x] 22. Evidence Reviewer

  **What to do**:
  - Implement `backend/review/evidence_reviewer.py`:
    - `EvidenceReviewer(BaseReviewer)` — checks that claims are backed by evidence:
      - `reviewer_name = "evidence"`
      - Checks: unsupported claims, missing data citations, vague references ("studies show..."), claim-evidence alignment
      - Criteria: "检查证据支撑：结论是否有数据/证据支持、引用是否明确、是否存在空泛表述、论据与论点是否对应"
      - Each issue should reference the claim text and suggest what evidence is needed

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**: Same as Task 19 (Wave 3.1)
  **Blocked By**: Tasks 6, 7, 17

  **References**: Same as Task 19

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_evidence_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect unsupported claim
    Tool: Bash (pytest)
    Steps:
      1. Section contains "本方案可提升效率300%" with no supporting data
      2. LLM mocked to flag this as unsupported
      3. Assert issue with location_excerpt containing "300%", suggestion to add evidence
    Expected Result: Unsupported claim detected with precise location
    Evidence: .sisyphus/evidence/task-22-evidence-unsupported.txt
  ```

  **Commit**: YES (grouped with Tasks 19-21)
  - Files: `backend/review/evidence_reviewer.py`, `backend/tests/review/test_evidence_reviewer.py`

- [x] 23. Consistency Reviewer

  **What to do**:
  - Implement `backend/review/consistency_reviewer.py`:
    - `ConsistencyReviewer(BaseReviewer)` — checks cross-section consistency:
      - `reviewer_name = "consistency"`
      - Checks: term usage consistency (same concept = same term), number consistency across sections, date/timeline consistency, unit consistency, name/abbreviation consistency, cross-reference accuracy
      - Criteria: "检查一致性：术语使用是否前后一致、数据/数字是否吻合、日期/时间线是否一致、单位是否统一、名称/缩写是否一致、交叉引用是否准确"
      - Reviews ALL sections together (not one-by-one) to catch cross-section issues

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**:
  - **Can Run In Parallel**: YES — with all other reviewers
  - **Parallel Group**: Wave 3.2
  - **Blocks**: Task 27
  - **Blocked By**: Tasks 6, 7, 17

  **References**: Same as Task 19

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_consistency_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect term inconsistency across sections
    Tool: Bash (pytest)
    Steps:
      1. Section A uses "机器学习", Section B uses "ML" for same concept
      2. LLM mocked to flag inconsistency
      3. Assert issue references both sections
    Expected Result: Cross-section inconsistency found
    Evidence: .sisyphus/evidence/task-23-consistency-terms.txt
  ```

  **Commit**: YES (grouped with Tasks 24-26)
  - Message: `feat(review): Consistency, Style, Coverage, Risk reviewers`
  - Files: `backend/review/consistency_reviewer.py`, `backend/tests/review/test_consistency_reviewer.py`

- [x] 24. Style Reviewer

  **What to do**:
  - Implement `backend/review/style_reviewer.py`:
    - `StyleReviewer(BaseReviewer)` — checks writing style and tone:
      - `reviewer_name = "style"`
      - Checks: formality level appropriateness, perspective consistency (第一人称/第三人称), tone consistency, sentence complexity balance, jargon overuse, paragraph length
      - Uses `style_guide` from task config if provided
      - Criteria: "检查文风：正式程度是否适当、人称视角是否一致、语气是否统一、句式是否多变、行话是否过多、段落长度是否合理"

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**: Same as Task 23 (Wave 3.2)
  **Blocked By**: Tasks 6, 7, 17

  **References**: Same as Task 19 + `style_guide` field from TaskConfig (Task 8)

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_style_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect style violation
    Tool: Bash (pytest)
    Steps:
      1. Document mixes 第一人称 and 第三人称
      2. LLM mocked to flag perspective inconsistency
      3. Assert issue with severity="minor"
    Expected Result: Style issue detected
    Evidence: .sisyphus/evidence/task-24-style-perspective.txt
  ```

  **Commit**: YES (grouped with Tasks 23, 25, 26)
  - Files: `backend/review/style_reviewer.py`, `backend/tests/review/test_style_reviewer.py`

- [x] 25. Coverage Reviewer

  **What to do**:
  - Implement `backend/review/coverage_reviewer.py`:
    - `CoverageReviewer(BaseReviewer)` — checks requirement coverage:
      - `reviewer_name = "coverage"`
      - Checks: each extracted requirement addressed in at least one section, scoring items/evaluation criteria all covered, no orphan sections (sections not linked to any requirement)
      - Needs access to extracted requirements (from Task 13 output, stored in DB)
      - Criteria: "检查覆盖度：每个需求点是否都在文档中有所体现、评分项/考核标准是否全部覆盖、是否有孤立章节无法追溯到需求"

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**: Same as Task 23 (Wave 3.2)
  **Blocked By**: Tasks 6, 7, 17

  **References**: Same as Task 19 + requirements data from RequirementExtractionSkill output (stored in task config or parsed_documents)

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_coverage_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect uncovered requirement
    Tool: Bash (pytest)
    Steps:
      1. Requirements include "安全性分析", but no section covers it
      2. LLM mocked to flag uncovered requirement
      3. Assert issue with severity="major", description referencing "安全性分析"
    Expected Result: Coverage gap identified
    Evidence: .sisyphus/evidence/task-25-coverage-gap.txt
  ```

  **Commit**: YES (grouped with Tasks 23, 24, 26)
  - Files: `backend/review/coverage_reviewer.py`, `backend/tests/review/test_coverage_reviewer.py`

- [x] 26. Risk Reviewer

  **What to do**:
  - Implement `backend/review/risk_reviewer.py`:
    - `RiskReviewer(BaseReviewer)` — checks for risky content:
      - `reviewer_name = "risk"`
      - Checks: sensitive/confidential terms, exaggerated claims, unsubstantiated superlatives, absolute statements without qualification, potential legal/compliance risks, data privacy concerns
      - Criteria: "检查风险：是否包含敏感/机密词汇、是否有夸大表述、是否有未限定的绝对化表述、是否有法律/合规风险、是否有数据隐私问题"
      - Risk issues default to `requires_human=true` (human review recommended)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`python-patterns`]

  **Parallelization**: Same as Task 23 (Wave 3.2)
  **Blocked By**: Tasks 6, 7, 17

  **References**: Same as Task 19

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/review/test_risk_reviewer.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Detect sensitive content
    Tool: Bash (pytest)
    Steps:
      1. Document contains "本公司属于行业第一" (exaggerated superlative)
      2. LLM mocked to flag as risk
      3. Assert issue with severity="major", requires_human=True
    Expected Result: Risky content flagged for human review
    Evidence: .sisyphus/evidence/task-26-risk-sensitive.txt
  ```

  **Commit**: YES (grouped with Tasks 23-25)
  - Files: `backend/review/risk_reviewer.py`, `backend/tests/review/test_risk_reviewer.py`

### Wave 3.3 — Review Aggregation, Rewrite, Revision Loop, Final Approval (Tasks 27-30)

- [x] 27. Review Service + Aggregation

  **What to do**:
  - Create `backend/services/review_service.py` — orchestrates running ALL 8 reviewers on a document
  - Method `run_all_reviews(task_id: str, document_id: str) -> AggregatedReview`:
    - Loads all registered reviewers from a registry (list, not discovery)
    - Runs each reviewer sequentially (MVP — parallel later)
    - Collects `ReviewResult` from each
    - Aggregates into `AggregatedReview` model
  - Create `backend/models/review_aggregation.py`:
    - `AggregatedReview`: `task_id, document_id, review_round: int, reviewer_results: list[ReviewResult], overall_status: str, critical_count: int, major_count: int, minor_count: int, overall_score: float, created_at`
    - `overall_status` logic: any `critical` issue → "rejected", any `major` issue → "needs_revision", all pass → "approved"
    - `overall_score`: weighted average of individual reviewer scores
  - Store aggregation result in `review_rounds` table (new migration)
  - Emit SSE progress events: `review_started`, `reviewer_N_complete`, `review_aggregated`
  - API endpoint `POST /api/v1/tasks/{task_id}/reviews/run` — triggers review run
  - API endpoint `GET /api/v1/tasks/{task_id}/reviews/{round}` — returns aggregated result
  - API endpoint `GET /api/v1/tasks/{task_id}/reviews/latest` — returns latest round

  **Must NOT do**:
  - G9: Do NOT add retry logic for individual reviewer failures — fail fast, report which reviewer failed
  - G1: Do NOT load full document content into aggregation model — reference by IDs only
  - Do NOT run reviewers in parallel (MVP — sequential is fine)
  - Do NOT implement reviewer weighting or priority ordering

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex service orchestration combining 8 reviewers with aggregation logic and multiple API endpoints
  - **Skills**: [`backend-patterns`, `python-patterns`]
    - `backend-patterns`: Service layer orchestration, API endpoint design
    - `python-patterns`: Async patterns, dataclass/Pydantic model design
  - **Skills Evaluated but Omitted**:
    - `api-design`: Endpoints are straightforward CRUD, not complex API design

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3.3 (sequential dependency within wave)
  - **Blocks**: Tasks 29, 30
  - **Blocked By**: Tasks 7, 17, 19-26 (needs BaseReviewer + all 8 reviewers + DB models)

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill interface that all reviewers extend
  - `backend/review/base.py` (Task 7) — BaseReviewer and ReviewResult/ReviewIssue schemas
  - `backend/services/document_service.py` (Task 12) — Service layer pattern to follow
  - `backend/services/progress_service.py` (Task 11) — SSE event emission pattern

  **API/Type References**:
  - `backend/models/review_aggregation.py` (this task creates it) — AggregatedReview schema
  - `backend/models/` (Task 10) — Existing DB model patterns and migration approach
  - Tasks 19-26 — All 8 reviewer implementations that this service orchestrates

  **External References**:
  - FastAPI dependency injection for accessing services: https://fastapi.tiangolo.com/tutorial/dependencies/

  **WHY Each Reference Matters**:
  - BaseReviewer (Task 7): Each reviewer returns ReviewResult — this service must collect and aggregate them
  - ProgressService (Task 11): Must emit SSE events during review execution so frontend shows progress
  - document_service (Task 12): Follow same service class structure (constructor injection, async methods)

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/services/test_review_service.py` → PASS (5+ tests)
  - [ ] Tests cover: run all reviewers, aggregation logic (critical→rejected, major→needs_revision, all_pass→approved), SSE events emitted, API endpoints return correct data

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Full review run with mixed results
    Tool: Bash (pytest + curl)
    Steps:
      1. Seed a document with 3 sections in DB
      2. Mock 8 reviewers — 6 return "pass", 1 returns major issue, 1 returns minor issue
      3. Call POST /api/v1/tasks/{task_id}/reviews/run
      4. Assert response contains aggregated result with overall_status="needs_revision"
      5. Assert critical_count=0, major_count=1, minor_count=1
      6. Call GET /api/v1/tasks/{task_id}/reviews/latest
      7. Assert returns same aggregation with all 8 reviewer_results
    Expected Result: Aggregation correctly reflects mixed reviewer outcomes
    Evidence: .sisyphus/evidence/task-27-review-aggregation.txt

  Scenario: Critical issue forces rejection
    Tool: Bash (pytest)
    Steps:
      1. Mock one reviewer returning severity="critical" issue
      2. Run review aggregation
      3. Assert overall_status="rejected"
      4. Assert critical_count >= 1
    Expected Result: Single critical issue causes overall rejection
    Evidence: .sisyphus/evidence/task-27-critical-rejection.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(review): add review service with aggregation and API endpoints`
  - Files: `backend/services/review_service.py`, `backend/models/review_aggregation.py`, `backend/api/review.py`, `backend/tests/services/test_review_service.py`, migration file

- [x] 28. Rewrite & Polish Skill

  **What to do**:
  - Create `backend/skills/rewrite.py` — extends BaseSkill
  - Purpose: Takes a section + list of ReviewIssue items → produces rewritten section content addressing the issues
  - `execute(context: SkillContext) -> SkillResult`:
    - Input in context: `section_id`, `section_content`, `issues: list[ReviewIssue]` (only non-human-required issues)
    - Builds LLM prompt: "Given this section content and these review issues, rewrite the section to address each issue while preserving the original meaning and style"
    - Includes issue descriptions and suggestions in the prompt
    - Calls `llm_client.complete()` to get rewritten content
    - Returns `SkillResult` with rewritten content and metadata (which issues were addressed)
  - The skill does NOT update the database — the caller (revision loop) handles persistence
  - Add prompt template to `backend/skills/prompts/rewrite.txt`

  **Must NOT do**:
  - Do NOT address issues with `requires_human=True` — skip them, include in metadata as "skipped_human_required"
  - G2: Do NOT import openai directly — use llm_client
  - Do NOT attempt to rewrite the entire document — one section at a time
  - Do NOT add version management logic — caller handles that
  - G3: Do NOT add configurable rewrite strategies — single approach for MVP

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: LLM integration skill with structured prompt engineering
  - **Skills**: [`python-patterns`, `coding-standards`]
    - `python-patterns`: Clean async implementation, proper error handling
    - `coding-standards`: Code quality, naming conventions
  - **Skills Evaluated but Omitted**:
    - `cost-aware-llm-pipeline`: Overkill for single skill — litellm handles routing

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 27)
  - **Parallel Group**: Wave 3.3 (parallel with Task 27)
  - **Blocks**: Task 29
  - **Blocked By**: Tasks 5, 6, 7 (needs LLMClient, BaseSkill, ReviewIssue schema)

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill interface to extend
  - `backend/skills/write_section.py` (Task 15) — Sibling content skill, follow same structure
  - `backend/skills/prompts/` (Task 15) — Prompt template file pattern

  **API/Type References**:
  - `backend/review/base.py` (Task 7) — ReviewIssue schema (input to this skill)
  - `backend/core/llm.py` (Task 5) — LLMClient.complete() method signature

  **WHY Each Reference Matters**:
  - section_generation_skill (Task 15): Same pattern — load prompt template, inject context, call LLM, return SkillResult
  - ReviewIssue (Task 7): This skill must parse issue descriptions/suggestions to build the rewrite prompt

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/skills/test_rewrite_skill.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Rewrite section addressing review issues
    Tool: Bash (pytest)
    Steps:
      1. Create SkillContext with section_content="本公司是行业最优秀的企业" and issues=[{severity: "major", description: "夸大宣传", suggestion: "使用客观数据支撑"}]
      2. Mock LLM to return rewritten content without superlatives
      3. Execute rewrite_skill
      4. Assert SkillResult.content does not contain "最优秀"
      5. Assert metadata includes addressed_issues count
    Expected Result: Section rewritten with issues addressed
    Evidence: .sisyphus/evidence/task-28-rewrite-basic.txt

  Scenario: Skip human-required issues
    Tool: Bash (pytest)
    Steps:
      1. Pass 3 issues: 2 auto-fixable, 1 with requires_human=True
      2. Execute rewrite_skill
      3. Assert only 2 issues included in LLM prompt
      4. Assert metadata.skipped_human_required contains the skipped issue
    Expected Result: Human-required issues are not auto-fixed
    Evidence: .sisyphus/evidence/task-28-skip-human.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(skills): add rewrite & polish skill for auto-revision`
  - Files: `backend/skills/rewrite.py`, `backend/skills/prompts/rewrite.txt`, `backend/tests/skills/test_rewrite_skill.py`

- [x] 29. Revision Loop in LangGraph

  **What to do**:
  - Add revision loop to the LangGraph graph in `backend/orchestrator/graph.py` (Task 9)
  - New nodes:
    - `run_reviews` — calls ReviewService.run_all_reviews(), stores AggregatedReview
    - `check_review_result` — conditional edge: approved → `final_approval`, needs_revision → `auto_revise`, rejected → `final_approval` (force human)
    - `auto_revise` — for each section with issues (where requires_human=False): call RewriteSkill, create new version of section, increment review_round in state
    - `check_revision_limit` — conditional: if review_round >= 3 (G8) → `final_approval` (force human), else → `run_reviews`
  - State additions to `DocumentState` (Task 9):
    - `review_round: int` (already planned, confirm it exists)
    - `review_passed: bool`
    - `pending_human_issues: list[str]` (issue IDs requiring human review)
  - Update SSE progress events: `revision_round_N_started`, `revision_round_N_complete`, `max_revisions_reached`
  - The loop: generate_sections → run_reviews → check_result → (auto_revise → check_limit → run_reviews)* → final_approval

  **Must NOT do**:
  - G8: Do NOT exceed 3 auto-revision loops — after 3, force human decision regardless
  - G1: Do NOT store section content in DocumentState — only IDs and status flags
  - Do NOT add sophisticated diff tracking between revisions (Task 37 handles version management)
  - Do NOT allow skipping the review step
  - Do NOT add partial re-review (re-run ALL reviewers each round for MVP)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex state machine logic with conditional edges, loop control, and integration of multiple services
  - **Skills**: [`python-patterns`, `backend-patterns`]
    - `python-patterns`: Complex control flow, async orchestration
    - `backend-patterns`: Service integration patterns
  - **Skills Evaluated but Omitted**:
    - `coding-standards`: Less relevant for graph/orchestration logic

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential within Wave 3.3
  - **Blocks**: Task 30
  - **Blocked By**: Tasks 9, 27, 28 (needs graph, review service, rewrite skill)

  **References**:

  **Pattern References**:
  - `backend/orchestrator/graph.py` (Task 9) — Existing LangGraph graph definition to extend
  - `backend/orchestrator/graph.py` (Tasks 9, 12-17) — Existing node implementations to follow pattern
  - `backend/services/review_service.py` (Task 27) — ReviewService.run_all_reviews() to call
  - `backend/skills/rewrite.py` (Task 28) — RewriteSkill to invoke for auto-revision

  **API/Type References**:
  - `backend/orchestrator/state.py` (Task 9) — DocumentState TypedDict to extend
  - `backend/models/review_aggregation.py` (Task 27) — AggregatedReview for checking overall_status

  **External References**:
  - LangGraph conditional edges: https://langchain-ai.github.io/langgraph/concepts/low_level/#conditional-edges

  **WHY Each Reference Matters**:
  - graph.py (Task 9): Must add new nodes and edges to the EXISTING graph — not create a new one
  - DocumentState (Task 9): Must verify review_round field exists and add pending_human_issues if not present
  - ReviewService (Task 27): The run_reviews node calls this service — must match its API
  - RewriteSkill (Task 28): The auto_revise node iterates sections and calls this skill per section

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/orchestrator/test_revision_loop.py` → PASS (5+ tests)
  - [ ] Tests cover: happy path (pass first round), single revision loop, max 3 revisions limit, critical rejection skips to human, SSE events

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Document passes review on first attempt
    Tool: Bash (pytest)
    Steps:
      1. Mock all 8 reviewers to return "pass" with no issues
      2. Execute graph from run_reviews node
      3. Assert graph transitions: run_reviews → check_review_result → final_approval
      4. Assert review_round=1, review_passed=True
    Expected Result: No revision needed, proceeds to final approval
    Evidence: .sisyphus/evidence/task-29-first-pass.txt

  Scenario: Max revision limit enforced (G8)
    Tool: Bash (pytest)
    Steps:
      1. Mock reviewers to always return major issues (never pass)
      2. Execute revision loop
      3. Assert loop runs exactly 3 times (review_round increments 1→2→3)
      4. After round 3, assert graph transitions to final_approval (force human)
      5. Assert SSE event "max_revisions_reached" emitted
    Expected Result: Loop stops at 3 and forces human decision
    Evidence: .sisyphus/evidence/task-29-max-revisions.txt

  Scenario: Auto-revision fixes issues and re-review passes
    Tool: Bash (pytest)
    Steps:
      1. Round 1: mock reviewers to return 2 major issues
      2. Mock RewriteSkill to return updated content
      3. Round 2: mock reviewers to return "pass"
      4. Assert loop: run_reviews → auto_revise → run_reviews → final_approval
      5. Assert review_round=2
    Expected Result: One revision cycle resolves issues
    Evidence: .sisyphus/evidence/task-29-revision-success.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(orchestrator): add revision loop with review-rewrite cycle and G8 limit`
  - Files: `backend/orchestrator/graph.py` (modified), `backend/tests/orchestrator/test_revision_loop.py`

- [x] 30. Final Review Approval Gate

  **What to do**:
  - Add approval node functions to `backend/orchestrator/graph.py` — LangGraph node
  - Purpose: Human intervention point — pauses the graph until user approves or requests changes
  - Node behavior:
    - Sets `DocumentState.current_phase = "awaiting_approval"`
    - Stores summary of review results (pass/fail, issue counts, human-required issues)
    - Emits SSE event `approval_required` with review summary
    - Graph PAUSES here (LangGraph interrupt/checkpoint mechanism)
  - API endpoints:
    - `GET /api/v1/tasks/{task_id}/approval` — returns current approval state (review summary, pending human issues)
    - `POST /api/v1/tasks/{task_id}/approval` with body `{"action": "approve" | "request_changes", "notes": "optional"}`
    - If `approve`: resume graph → proceed to export-ready state
    - If `request_changes` with notes: resume graph → route back to auto_revise (counts toward G8 limit)
  - Create `backend/models/approval.py`:
    - `ApprovalRequest`: `action: Literal["approve", "request_changes"]`, `notes: Optional[str]`
    - `ApprovalState`: `task_id, status, review_summary, pending_human_issues, created_at`

  **Must NOT do**:
  - Do NOT auto-approve — always require explicit human action
  - Do NOT implement complex approval workflows (multi-stage, multi-role)
  - G6: Do NOT add user authentication to approval endpoint
  - Do NOT allow approval if reviews haven't been run
  - Do NOT implement approval rollback

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: LangGraph interrupt/checkpoint mechanism is complex, must integrate with graph state and API
  - **Skills**: [`backend-patterns`, `python-patterns`]
    - `backend-patterns`: API design for human-in-the-loop patterns
    - `python-patterns`: Async flow control, state management
  - **Skills Evaluated but Omitted**:
    - `api-design`: Approval endpoints are simple, don't need full API design patterns

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential within Wave 3.3
  - **Blocks**: Tasks 31-36 (frontend needs approval API to integrate)
  - **Blocked By**: Tasks 9, 29 (needs graph + revision loop in place)

  **References**:

  **Pattern References**:
  - `backend/orchestrator/graph.py` (Task 9) — Graph definition to add approval node
  - `backend/orchestrator/graph.py` (Task 14) — First human approval gate (outline approval) — follow same pattern
  - `backend/services/progress_service.py` (Task 11) — SSE event emission for approval_required

  **API/Type References**:
  - `backend/orchestrator/state.py` (Task 9) — DocumentState fields for approval tracking
  - `backend/models/review_aggregation.py` (Task 27) — Review summary data to surface in approval state

  **External References**:
  - LangGraph human-in-the-loop: https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/

  **WHY Each Reference Matters**:
  - outline_approval.py (Task 14): This is the SECOND human gate — must follow the exact same interrupt/resume pattern established by the first gate
  - ReviewAggregation (Task 27): Approval gate must surface the review summary so user sees what reviewers found before deciding

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/orchestrator/test_final_approval.py` → PASS (4+ tests)
  - [ ] Tests cover: graph pauses at approval, approve resumes to export-ready, request_changes routes back to revision, cannot approve without reviews

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Approve and proceed
    Tool: Bash (curl)
    Steps:
      1. Run reviews on a document (mock reviewers to pass)
      2. Graph reaches final_approval node and pauses
      3. GET /api/v1/tasks/{task_id}/approval → assert status="awaiting_approval" with review summary
      4. POST /api/v1/tasks/{task_id}/approval body={"action": "approve"}
      5. Assert graph resumes, DocumentState.current_phase changes to "approved"
      6. Assert SSE event "task_approved" emitted
    Expected Result: Human approval advances pipeline to export-ready
    Evidence: .sisyphus/evidence/task-30-approve.txt

  Scenario: Request changes loops back
    Tool: Bash (curl)
    Steps:
      1. Graph at final_approval node
      2. POST /api/v1/tasks/{task_id}/approval body={"action": "request_changes", "notes": "Fix section 3 tone"}
      3. Assert graph routes back to auto_revise
      4. Assert review_round increments
      5. Assert notes stored in approval history
    Expected Result: User feedback triggers another revision round
    Evidence: .sisyphus/evidence/task-30-request-changes.txt

  Scenario: Cannot approve without reviews
    Tool: Bash (curl)
    Steps:
      1. Create a task that has NOT been reviewed yet
      2. POST /api/v1/tasks/{task_id}/approval body={"action": "approve"}
      3. Assert HTTP 400 with error message "Reviews must be completed before approval"
    Expected Result: Approval blocked without review data
    Evidence: .sisyphus/evidence/task-30-no-review-block.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(orchestrator): add final review approval gate with human-in-the-loop`
  - Files: `backend/orchestrator/graph.py` (modified), `backend/models/approval.py`, `backend/api/approval.py`, `backend/tests/orchestrator/test_final_approval.py`

### PHASE 4: Frontend Core (Tasks 31-36)

### Wave 4.1 — Layout + Task Home (Tasks 31-32, parallel)

- [x] 31. App Shell & Layout

  **What to do**:
  - Create Next.js app with App Router in `frontend/`
  - `frontend/app/layout.tsx` — Root layout with Chinese locale (`lang="zh-CN"`)
  - Sidebar navigation component `frontend/components/layout/sidebar.tsx`:
    - Links: 任务列表 (Task Home `/`), 工作台 (Workbench `/tasks/[id]`), 知识库 (Knowledge Base `/knowledge`)
    - Active state highlighting based on current route
    - Collapsible on mobile (responsive)
  - Header component `frontend/components/layout/header.tsx`:
    - App title: "文档智能平台"
    - Breadcrumb showing current location
  - Global styles in `frontend/app/globals.css` — Tailwind CSS setup
  - `frontend/lib/api.ts` — API client wrapper using `fetch` with base URL from env
  - `frontend/lib/hooks/use-sse.ts` — Custom hook for SSE connections:
    - `useSSE(taskId: string)` → returns `{ events, isConnected, error }`
    - Auto-reconnect on disconnect
    - Cleanup on unmount
  - `frontend/lib/types.ts` — Shared TypeScript types mirroring backend models (Task, Document, ReviewResult, etc.)
  - Install and configure TanStack Query in `frontend/app/providers.tsx`

  **Must NOT do**:
  - G7: Do NOT add Redux, Zustand, or any state management beyond TanStack Query
  - G6: Do NOT add login/auth pages or route guards
  - Do NOT add internationalization (i18n) — Chinese only, hardcoded strings
  - Do NOT add dark mode toggle
  - Do NOT use WebSocket — SSE only (G5)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Layout/UI scaffolding with responsive design, component structure
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: Next.js App Router patterns, component organization
    - `coding-standards`: TypeScript conventions, naming standards
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Not needed for layout scaffolding — Playwright used in QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 32)
  - **Parallel Group**: Wave 4.1
  - **Blocks**: Tasks 33-36
  - **Blocked By**: Task 4 (frontend project setup from monorepo scaffolding)

  **References**:

  **Pattern References**:
  - `frontend/package.json` (Task 4) — Project dependencies already configured
  - `frontend/tailwind.config.ts` (Task 4) — Tailwind configuration to use

  **API/Type References**:
  - `backend/models/` (Tasks 10, 27, 30) — Backend models to mirror in frontend types
  - `backend/services/progress_service.py` (Task 11) — SSE event format to consume

  **External References**:
  - Next.js App Router: https://nextjs.org/docs/app
  - TanStack Query with Next.js: https://tanstack.com/query/latest/docs/framework/react/guides/ssr

  **WHY Each Reference Matters**:
  - Task 4 frontend setup: Must build on the existing package.json and config — don't recreate
  - ProgressService (Task 11): SSE hook must match the exact event format the backend emits
  - Backend models: TypeScript types must mirror Pydantic schemas for type-safe API consumption

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/layout.test.tsx` → PASS (basic render tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: App shell renders with navigation
    Tool: Playwright
    Steps:
      1. Navigate to http://localhost:3000
      2. Assert sidebar visible with selector `.sidebar` or `nav[role="navigation"]`
      3. Assert nav contains links: text "任务列表", "工作台", "知识库"
      4. Assert header contains text "文档智能平台"
      5. Assert HTML lang attribute is "zh-CN"
      6. Take screenshot
    Expected Result: Full app shell renders with Chinese UI and navigation
    Evidence: .sisyphus/evidence/task-31-app-shell.png

  Scenario: SSE hook connects and receives events
    Tool: Bash (node script)
    Steps:
      1. Start backend with a mock SSE endpoint
      2. Create test script that instantiates SSE connection to /api/v1/tasks/test/progress
      3. Assert EventSource connects (readyState=OPEN)
      4. Send a test event from backend
      5. Assert event received in client
    Expected Result: SSE hook establishes connection and receives events
    Evidence: .sisyphus/evidence/task-31-sse-hook.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add app shell layout with sidebar, header, SSE hook, and TanStack Query`
  - Files: `frontend/app/layout.tsx`, `frontend/app/providers.tsx`, `frontend/components/layout/sidebar.tsx`, `frontend/components/layout/header.tsx`, `frontend/lib/api.ts`, `frontend/lib/hooks/use-sse.ts`, `frontend/lib/types.ts`

- [x] 32. Task Home Page (任务列表)

  **What to do**:
  - Create `frontend/app/page.tsx` — Task list page (home route `/`)
  - Features:
    - List all tasks with: title, document type, status badge, created date, last updated
    - Status badges with colors: 进行中 (blue), 审核中 (yellow), 已完成 (green), 待审批 (orange)
    - "新建任务" button opens creation dialog
    - Click task row → navigates to `/tasks/[id]` (workbench)
  - Create `frontend/components/task/task-list.tsx` — Task list with TanStack Query
  - Create `frontend/components/task/create-task-dialog.tsx`:
    - Form fields: 任务名称 (task name), 文档类型 (dropdown: 投标书/技术方案/可行性报告), 上传文档 (file upload)
    - File upload accepts .docx, .pdf, .md (task documents — NO .txt; see "Supported File Types" in Verification Strategy)
    - Two-step submission: (1) `POST /api/v1/tasks` with JSON `{name, doc_type}` → returns task ID, (2) if file selected, `POST /api/v1/tasks/{id}/documents/upload` with multipart form data
  - TanStack Query hooks in `frontend/lib/hooks/use-tasks.ts`:
    - `useTasks()` — fetch all tasks
    - `useCreateTask()` — mutation for creating task, then uploading file if present
  - Empty state: "暂无任务，点击'新建任务'开始" with illustration

  **Must NOT do**:
  - Do NOT add pagination (MVP — list all tasks)
  - Do NOT add search or filtering
  - Do NOT add task deletion or bulk operations
  - G7: Do NOT manage task state outside TanStack Query
  - Do NOT add drag-and-drop reordering

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI component with list rendering, dialog, file upload, status badges
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: React component patterns, TanStack Query hooks
    - `coding-standards`: TypeScript types, component naming
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: QA covers UI testing via Playwright scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 31)
  - **Parallel Group**: Wave 4.1
  - **Blocks**: Tasks 33-36
  - **Blocked By**: Task 4 (frontend project setup)

  **References**:

  **Pattern References**:
  - `frontend/lib/api.ts` (Task 31) — API client for making requests
  - `frontend/lib/types.ts` (Task 31) — TypeScript types for Task model

  **API/Type References**:
  - `backend/api/tasks.py` (Task 10) — `POST /api/v1/tasks`, `GET /api/v1/tasks` endpoints
  - `backend/models/task.py` (Task 10) — Task model fields to display

  **External References**:
  - TanStack Query mutations: https://tanstack.com/query/latest/docs/framework/react/guides/mutations

  **WHY Each Reference Matters**:
  - Backend task endpoints: Must match exact request/response format — check field names and types
  - api.ts (Task 31): Use the shared API client, don't create a separate fetch wrapper

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/task-list.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Create task with file upload
    Tool: Playwright
    Steps:
      1. Navigate to http://localhost:3000
      2. Click button with text "新建任务"
      3. Assert dialog visible with form fields
      4. Fill input[name="name"] with "测试投标书"
      5. Select dropdown option "投标书"
      6. Upload file test-doc.docx via file input
      7. Click submit button
      8. Assert dialog closes
      9. Assert task list contains new item with text "测试投标书"
      10. Assert status badge shows "已创建"
    Expected Result: Task created and appears in list
    Evidence: .sisyphus/evidence/task-32-create-task.png

  Scenario: Empty state display
    Tool: Playwright
    Preconditions: Restart backend with env SEED_DEMO_DATA=false, then run reset_db.py + seed.py so only templates exist (no demo task)
    Steps:
      1. Navigate to http://localhost:3000
      2. Assert page contains text "暂无任务"
      3. Assert "新建任务" button is visible
    Expected Result: Friendly empty state shown when no tasks exist (seed only created templates, no demo task)
    Evidence: .sisyphus/evidence/task-32-empty-state.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add task home page with list, creation dialog, and file upload`
  - Files: `frontend/app/page.tsx`, `frontend/components/task/task-list.tsx`, `frontend/components/task/create-task-dialog.tsx`, `frontend/lib/hooks/use-tasks.ts`

### Wave 4.2 — Workbench Page (Tasks 33-35, partially parallel)

- [x] 33. Workbench — Left Panel (Outline & Structure)

  **What to do**:
  - Create `frontend/app/tasks/[id]/page.tsx` — Workbench page with 3-panel layout
  - This task focuses on the LEFT panel and overall page structure
  - Top bar: shows task name, status badge, and a **"开始处理" (Start Processing) button** — visible only when task status is `created` (i.e., documents uploaded but pipeline not yet started). Clicking it calls `POST /api/v1/tasks/{id}/start` and transitions task to `parsing` status. Button disappears once pipeline is running.
  - **NOTE**: Document upload happens in the create-task dialog (Task 32), NOT in the workbench. By the time the user reaches this page, documents are already uploaded. The workbench is for processing, viewing, and reviewing — not uploading.
  - Left panel `frontend/components/workbench/outline-panel.tsx`:
    - Tree view showing document outline (sections, subsections)
    - Each node shows: title, status icon (draft/reviewing/approved), word count
    - Click section → loads content in center panel
    - "审批大纲" (Approve Outline) button — calls `POST /api/v1/tasks/{id}/approve-outline`

  **Must NOT do**:
  - Do NOT implement the center panel content (Task 34)
  - Do NOT implement the right panel (Task 35)
  - Do NOT add keyboard shortcuts for navigation
  - Do NOT implement undo/redo for outline changes
  - Do NOT add inline outline editing (edit titles, add/remove sections) — no backend endpoint exists for MVP; outline is AI-generated and read-only until approved
  - Do NOT add drag-and-drop reordering of sections — no reorder endpoint exists for MVP

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex layout with tree view, drag-drop, interactive outline panel
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: Complex component composition, CSS Grid layout
    - `coding-standards`: TypeScript, component organization
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Playwright coverage in QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (partially with Tasks 34, 35 — but 34/35 depend on the 3-panel layout from this task)
  - **Parallel Group**: Wave 4.2 (start first, 34/35 can start once layout shell exists)
  - **Blocks**: Tasks 34, 35 (they plug into the layout)
  - **Blocked By**: Tasks 31, 32, 14 (layout + task page + outline approval API)

  **References**:

  **Pattern References**:
  - `frontend/components/layout/sidebar.tsx` (Task 31) — Component structure pattern
  - `frontend/lib/hooks/use-tasks.ts` (Task 32) — TanStack Query hook pattern

  **API/Type References**:
  - `backend/api/documents.py` (Task 16) — Document/section endpoints
  - `backend/api/tasks.py` (Task 18) — `POST /api/v1/tasks/{id}/approve-outline`
  - `frontend/lib/types.ts` (Task 31) — Document, Section TypeScript types

  **WHY Each Reference Matters**:
  - Document endpoints: Must know exact section structure returned by API to build tree view
  - Outline approval API (Task 14): Button triggers this endpoint — must match request format

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/outline-panel.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: 3-panel layout renders correctly
    Tool: Playwright
    Steps:
      1. Create a task with document and 3 sections via API
      2. Navigate to /tasks/{id}
      3. Assert 3-panel layout visible (left, center, right panels)
      4. Assert left panel contains outline tree with 3 section titles
      5. Assert each section shows status icon
      6. Take full-page screenshot
    Expected Result: Workbench renders with 3-panel layout and populated outline
    Evidence: .sisyphus/evidence/task-33-workbench-layout.png

  Scenario: Start processing from workbench
    Tool: Playwright
    Preconditions: Task status is "created" (documents uploaded, pipeline not started)
    Steps:
      1. Navigate to /tasks/{id} where task status is "created"
      2. Assert "开始处理" button is visible in top bar
      3. Click button with text "开始处理"
      4. Assert button disappears (pipeline started)
      5. Assert SSE events begin arriving (status changes to "parsing")
    Expected Result: Pipeline starts via explicit user action, start button disappears
    Evidence: .sisyphus/evidence/task-33-start-processing.png

  Scenario: Approve outline
    Tool: Playwright
    Steps:
      1. Navigate to /tasks/{id} where outline is pending approval
      2. Click button with text "审批大纲"
      3. Assert confirmation dialog appears
      4. Confirm approval
      5. Assert outline status changes (approve button disappears or becomes disabled)
      6. Assert SSE event updates reflected in UI
    Expected Result: Outline approval triggers backend and UI updates
    Evidence: .sisyphus/evidence/task-33-approve-outline.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add workbench page with 3-panel layout and outline panel`
  - Files: `frontend/app/tasks/[id]/page.tsx`, `frontend/components/workbench/outline-panel.tsx`, `frontend/lib/hooks/use-document.ts`

- [x] 34. Workbench — Center Panel (Content Editor)

  **What to do**:
  - Create `frontend/components/workbench/content-panel.tsx` — Center panel content display
  - Features:
    - Displays the currently selected section's content (from outline panel click)
    - Rich text display using a simple markdown renderer (react-markdown)
    - Section header showing: section title, word count, generation status
    - Progress indicator when section is being generated (SSE integration)
    - Diff view toggle: show changes between current and previous version (basic text diff)
  - Create `frontend/components/workbench/section-content.tsx` — Section content renderer
  - Create `frontend/components/workbench/generation-progress.tsx` — SSE-driven progress bar
  - TanStack Query hooks:
    - `useSection(sectionId)` — fetch section content

  **Must NOT do**:
  - Do NOT implement a full rich text editor (WYSIWYG) — display only with markdown rendering
  - Do NOT allow inline content editing by user (MVP — content is AI-generated only)
  - Do NOT implement real-time collaborative editing
  - Do NOT add copy/paste formatting preservation
  - Do NOT add a "重新生成" (Regenerate) button — no single-section regeneration endpoint exists for MVP; full re-generation is done via the orchestrator pipeline
  - G11: Do NOT render complex formatting (tables, charts) — headings + paragraphs only

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Content display panel with markdown rendering, progress indicators, SSE integration
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: React component patterns, SSE event consumption
    - `coding-standards`: TypeScript, clean component structure
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Playwright in QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 35, after Task 33 layout exists)
  - **Parallel Group**: Wave 4.2
  - **Blocks**: Task 36
  - **Blocked By**: Task 33 (needs 3-panel layout), Task 15 (section generation API)

  **References**:

  **Pattern References**:
  - `frontend/components/workbench/outline-panel.tsx` (Task 33) — Sibling panel component pattern
  - `frontend/lib/hooks/use-sse.ts` (Task 31) — SSE hook for generation progress

  **API/Type References**:
  - `backend/api/documents.py` (Task 16) — `GET /api/v1/tasks/{task_id}/sections` (list), `GET /api/v1/tasks/{task_id}/sections/{section_id}` (detail with versions)
  - `frontend/lib/types.ts` (Task 31) — Section type with content, status, version fields

  **WHY Each Reference Matters**:
  - SSE hook (Task 31): Generation progress events drive the progress bar — must use same hook
  - Section API (Task 16): Content panel fetches and displays section data — must match response shape from `GET /api/v1/tasks/{task_id}/sections/{section_id}`

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/content-panel.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Display section content
    Tool: Playwright
    Steps:
      1. Create task with document containing section with markdown content "# 项目概述\n\n本项目旨在..."
      2. Navigate to /tasks/{id}
      3. Click first section in outline panel
      4. Assert center panel shows rendered heading "项目概述"
      5. Assert paragraph text visible below heading
      6. Assert word count displayed in section header
    Expected Result: Section content renders as formatted markdown
    Evidence: .sisyphus/evidence/task-34-section-content.png

  Scenario: Section generation progress
    Tool: Playwright
    Steps:
      1. Navigate to /tasks/{id} with a section in "generating" state
      2. Assert progress indicator visible in center panel
      3. Mock SSE events: progress 25%, 50%, 75%, 100%
      4. Assert progress bar updates with each event
      5. After 100%, assert content appears replacing progress indicator
    Expected Result: Real-time generation progress shown via SSE
    Evidence: .sisyphus/evidence/task-34-generation-progress.png
  ```

  **Commit**: YES (grouped with Task 35)
  - Message: `feat(frontend): add workbench content panel with markdown rendering and progress`
  - Files: `frontend/components/workbench/content-panel.tsx`, `frontend/components/workbench/section-content.tsx`, `frontend/components/workbench/generation-progress.tsx`

- [x] 35. Workbench — Right Panel (Review & Progress)

  **What to do**:
  - Create `frontend/components/workbench/review-panel.tsx` — Right panel showing review status and progress
  - Features:
    - **Progress Section**: Pipeline progress steps (解析 → 提取需求 → 生成大纲 → 审批 → 生成内容 → 审核 → 修订 → 最终审批)
      - Each step shows: status icon (pending/running/done/error), duration if completed
      - Current step highlighted with animation
      - Driven by SSE events from progress_service
    - **Review Summary Section** (visible after reviews run):
      - Overall status badge (通过/需修订/拒绝)
      - Score display (e.g., "综合评分: 78/100")
      - Issue counts by severity: 严重 (critical), 重要 (major), 建议 (minor)
      - Expandable list of issues grouped by reviewer
    - **Action Buttons**:
      - "运行审核" (Run Reviews) — `POST /api/v1/tasks/{id}/reviews/run`
      - "批准" / "需要修改" (Approve/Request Changes) — calls approval API (Task 30)
    - Revision round indicator: "第 N 轮审核" with history

  **Must NOT do**:
  - G12: Do NOT add charts or graphs for scores — static number display only
  - Do NOT add individual reviewer detail pages (that's Task 36 Review Dashboard)
  - Do NOT add issue filtering or sorting
  - Do NOT implement inline issue annotations (that's Task 44)
  - G7: Do NOT use separate state management — TanStack Query only

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex panel with progress visualization, SSE-driven updates, review summary display
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: SSE-driven reactive UI, component composition
    - `coding-standards`: TypeScript, consistent styling
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Covered by Playwright QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 34, after Task 33 layout exists)
  - **Parallel Group**: Wave 4.2
  - **Blocks**: Task 36
  - **Blocked By**: Task 33 (3-panel layout), Task 27 (review API), Task 30 (approval API)

  **References**:

  **Pattern References**:
  - `frontend/lib/hooks/use-sse.ts` (Task 31) — SSE hook for progress events
  - `frontend/components/workbench/outline-panel.tsx` (Task 33) — Sibling panel pattern

  **API/Type References**:
  - `backend/api/review.py` (Task 27) — Review run and results endpoints
  - `backend/api/approval.py` (Task 30) — Approval endpoints
  - `backend/models/review_aggregation.py` (Task 27) — AggregatedReview shape for display
  - `backend/services/progress_service.py` (Task 11) — SSE event types for pipeline steps

  **WHY Each Reference Matters**:
  - SSE events (Task 11): Progress steps are driven entirely by SSE — must handle each event type
  - AggregatedReview (Task 27): Review summary display maps directly from this model's fields
  - Approval API (Task 30): Action buttons call these endpoints — must match request format

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/review-panel.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Pipeline progress display
    Tool: Playwright
    Steps:
      1. Navigate to /tasks/{id} where task is in "generating content" phase
      2. Assert right panel shows pipeline steps
      3. Assert steps before current show ✓ (done) icons
      4. Assert current step "生成内容" is highlighted/animated
      5. Assert steps after current show pending state
      6. Mock SSE event for step completion
      7. Assert next step becomes highlighted
    Expected Result: Real-time pipeline progress visualization
    Evidence: .sisyphus/evidence/task-35-pipeline-progress.png

  Scenario: Review summary with issues
    Tool: Playwright
    Steps:
      1. Run reviews on task (mock reviewers: 2 major, 3 minor issues)
      2. Navigate to /tasks/{id}
      3. Assert right panel shows "需修订" badge
      4. Assert issue counts: "重要: 2, 建议: 3"
      5. Expand issue list
      6. Assert issues grouped by reviewer name
      7. Assert each issue shows severity, description, suggestion
    Expected Result: Review results displayed with structured issue list
    Evidence: .sisyphus/evidence/task-35-review-summary.png
  ```

  **Commit**: YES (grouped with Task 34)
  - Message: `feat(frontend): add workbench review panel with progress and review summary`
  - Files: `frontend/components/workbench/review-panel.tsx`, `frontend/lib/hooks/use-reviews.ts`

### Wave 4.3 — Review Dashboard (Task 36)

- [x] 36. Review Dashboard Page (审核面板)

  **What to do**:
  - Create `frontend/app/tasks/[id]/reviews/page.tsx` — Dedicated review dashboard
  - Features:
    - Full-page view of review results for a task (separate from workbench)
    - **Reviewer Cards**: One card per reviewer showing:
      - Reviewer name (Chinese: 格式审核, 一致性审核, etc.)
      - Status (通过/未通过)
      - Score
      - Issue count by severity
      - Click to expand full issue list
    - **Issue Detail View**:
      - All issues in a filterable table
      - Columns: 审核员, 严重程度, 类别, 位置, 描述, 建议
      - Filter by: severity (严重/重要/建议), reviewer, section
      - Sort by severity (default: critical first)
    - **Revision History Timeline**:
      - Shows each review round: round number, date, result, issue counts
      - Visual timeline (vertical, chronological)
    - Link back to workbench

  **Must NOT do**:
  - G12: Do NOT add charts, graphs, or visualizations — tables and cards only
  - Do NOT add issue editing or status tracking (approved/wontfix)
  - Do NOT add bulk issue actions
  - Do NOT add export review results
  - Do NOT add reviewer configuration UI

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Data-rich dashboard with cards, filterable table, timeline component
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: Data display patterns, filtering, component composition
    - `coding-standards`: TypeScript, clean code
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Covered by QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Wave 4.2)
  - **Parallel Group**: Wave 4.3 (standalone)
  - **Blocks**: None in Phase 4
  - **Blocked By**: Tasks 33-35 (needs workbench established), Task 27 (review API)

  **References**:

  **Pattern References**:
  - `frontend/components/workbench/review-panel.tsx` (Task 35) — Review data display patterns (reuse components where possible)
  - `frontend/lib/hooks/use-reviews.ts` (Task 35) — Review data hooks

  **API/Type References**:
  - `backend/api/review.py` (Task 27) — `GET /api/v1/tasks/{id}/reviews/latest`, review data endpoints
  - `backend/models/review_aggregation.py` (Task 27) — AggregatedReview, ReviewResult, ReviewIssue types
  - `frontend/lib/types.ts` (Task 31) — Frontend TypeScript types for review models

  **WHY Each Reference Matters**:
  - review-panel.tsx (Task 35): Reuse the same components (reviewer cards, issue display) — don't rebuild
  - Review API (Task 27): Dashboard consumes the same endpoints as the review panel but shows more detail

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/review-dashboard.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Review dashboard with all 8 reviewers
    Tool: Playwright
    Steps:
      1. Run reviews on task (all 8 reviewers produce results)
      2. Navigate to /tasks/{id}/reviews
      3. Assert 8 reviewer cards visible
      4. Assert each card shows Chinese name, score, status
      5. Click on "格式审核" card
      6. Assert expanded view shows issues from that reviewer
      7. Take screenshot of full dashboard
    Expected Result: All 8 reviewers displayed with expandable details
    Evidence: .sisyphus/evidence/task-36-review-dashboard.png

  Scenario: Filter issues by severity
    Tool: Playwright
    Steps:
      1. Dashboard shows issues from multiple reviewers with mixed severities
      2. Click severity filter "重要" (major)
      3. Assert table shows only major-severity issues
      4. Assert issue count label updates to reflect filtered count
      5. Click "全部" to remove filter
      6. Assert all issues shown again
    Expected Result: Issue table filters correctly by severity
    Evidence: .sisyphus/evidence/task-36-filter-severity.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add review dashboard with reviewer cards, issue table, and revision timeline`
  - Files: `frontend/app/tasks/[id]/reviews/page.tsx`, `frontend/components/review/reviewer-card.tsx`, `frontend/components/review/issue-table.tsx`, `frontend/components/review/revision-timeline.tsx`

### PHASE 5: Advanced Features (Tasks 37-45)

### Wave 5.1 — Version Management + RAG Foundation (Tasks 37-39, parallel)

- [x] 37. Version Management Service

  **What to do**:
  - Create `backend/services/version_service.py` — Manages document/section version history
  - SQLAlchemy model in `backend/models/version.py` — implements the `section_versions` table already defined in Task 4's migration (DO NOT create a new migration for this table; Task 4 owns the schema):
    - `SectionVersion`: `id, section_id, version_number: int, content: str, change_source: str ("generation"|"revision"|"manual"), change_summary: str, parent_version_id: Optional[str], created_at`
    - Each section generation or rewrite creates a new version
  - Methods:
    - `create_version(section_id, content, source, summary) -> SectionVersion`
    - `get_versions(section_id) -> list[SectionVersion]` — ordered by version_number
    - `get_version(version_id) -> SectionVersion`
    - `get_diff(version_a_id, version_b_id) -> DiffResult` — returns line-level text diff
    - `rollback_section(section_id, target_version_id)` — sets section content to target version
  - `DiffResult` model: `additions: int, deletions: int, hunks: list[DiffHunk]`
  - `DiffHunk`: `old_start, old_count, new_start, new_count, lines: list[DiffLine]`
  - Use Python `difflib` for diff computation (not external library)
  - API endpoints:
    - `GET /api/v1/sections/{id}/versions` — list versions
    - `GET /api/v1/sections/{id}/versions/{vid}/diff?compare_to={vid2}` — get diff
    - `POST /api/v1/sections/{id}/rollback` with body `{"target_version_id": "..."}`
  - Integration: Update `section_generation_skill` (Task 15) and `rewrite_skill` (Task 28) callers to create versions on each content change

  **Must NOT do**:
  - Do NOT implement document-level versioning (section-level only for MVP)
  - Do NOT add branching or merge capabilities
  - Do NOT store diffs — store full content per version, compute diffs on demand
  - Do NOT add version comparison beyond two versions at a time
  - Do NOT implement version tagging or labeling

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Backend service with data model, diff computation, API endpoints, and cross-task integration
  - **Skills**: [`backend-patterns`, `python-patterns`]
    - `backend-patterns`: Service layer design, REST API endpoints
    - `python-patterns`: difflib usage, data modeling
  - **Skills Evaluated but Omitted**:
    - `database-migrations`: Simple table addition, doesn't need migration patterns skill

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 38, 39)
  - **Parallel Group**: Wave 5.1
  - **Blocks**: Task 42 (Version Diff UI)
  - **Blocked By**: Tasks 10, 15, 28 (needs DB models, section generation, rewrite skill)

  **References**:

  **Pattern References**:
  - `backend/services/document_service.py` (Task 12) — Service layer pattern
  - `backend/skills/rewrite.py` (Task 28) — Where version creation hooks in after rewrite

  **API/Type References**:
  - `backend/models/document.py` (Task 10) — Section model that versions reference
  - Python `difflib.unified_diff` — For generating text diffs

  **WHY Each Reference Matters**:
  - document_service (Task 12): Follow same service structure (constructor, async methods, DB session handling)
  - rewrite_skill caller: Must identify WHERE in the pipeline to hook version creation (after each rewrite)

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/services/test_version_service.py` → PASS (5+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Create versions and compute diff
    Tool: Bash (pytest + curl)
    Steps:
      1. Create section with initial content "本项目旨在提升效率"
      2. Create version 1 via API
      3. Update content to "本项目旨在显著提升生产效率和质量"
      4. Create version 2 via API
      5. GET /api/v1/sections/{id}/versions → assert 2 versions
      6. GET /api/v1/sections/{id}/versions/{v2}/diff?compare_to={v1}
      7. Assert diff shows additions > 0, contains "显著" and "和质量" as added
    Expected Result: Version history tracked and diffs computed correctly
    Evidence: .sisyphus/evidence/task-37-version-diff.txt

  Scenario: Rollback to previous version
    Tool: Bash (curl)
    Steps:
      1. Section has 3 versions (v1, v2, v3)
      2. POST /api/v1/sections/{id}/rollback body={"target_version_id": v1.id}
      3. GET section content → assert matches v1 content
      4. GET versions → assert v4 created (rollback creates new version, not delete)
    Expected Result: Rollback creates new version with old content
    Evidence: .sisyphus/evidence/task-37-rollback.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(version): add version management service with diff and rollback`
  - Files: `backend/services/version_service.py`, `backend/models/version.py`, `backend/api/version.py`, migration file, `backend/tests/services/test_version_service.py`

- [x] 38. RAG Service + pgvector Setup

  **What to do**:
  - Create `backend/services/rag_service.py` — Retrieval-Augmented Generation service
  - Enable pgvector extension in PostgreSQL (Task 4's migration already includes `CREATE EXTENSION IF NOT EXISTS vector`)
  - SQLAlchemy model in `backend/models/knowledge.py` — implements the `knowledge_chunks` table already defined in Task 4's migration (DO NOT create a new migration for this table; Task 4 owns the schema):
    - `KnowledgeChunk`: `id, source_document_id, chunk_index: int, content: str, embedding: Vector(1536), metadata: dict, created_at`
    - Using pgvector's `Vector` column type
  - Methods:
    - `ingest_document(document_id: str, chunks: list[str])` — creates embeddings via litellm and stores chunks
    - `search(query: str, top_k: int = 5) -> list[KnowledgeChunk]` — cosine similarity search
    - `delete_document_chunks(document_id: str)` — cleanup
    - `list_documents() -> list[dict]` — returns ingested documents with chunk counts (backs GET /documents)
    - `get_stats() -> dict` — returns total_documents, total_chunks, last_updated (backs GET /stats)
  - Embedding generation: Use `llm_client.embed(texts)` method (add to LLMClient in Task 5 if not present)
  - Chunking strategy: Simple fixed-size chunks (500 chars) with 50-char overlap
  - Search: Basic `SELECT ... ORDER BY embedding <=> query_embedding LIMIT top_k`
  - API endpoints in `backend/api/knowledge.py`:
    - `POST /api/v1/knowledge/ingest` — ingest document into knowledge base (accepts multipart file upload, chunks, embeds, stores)
    - `POST /api/v1/knowledge/search` with body `{"query": "...", "top_k": 5}` — search knowledge
    - `GET /api/v1/knowledge/documents` — list all ingested documents with chunk counts (for Task 45 Knowledge Base UI)
    - `DELETE /api/v1/knowledge/documents/{document_id}` — delete document and its chunks from vector store
    - `GET /api/v1/knowledge/stats` — returns `{"total_documents": int, "total_chunks": int, "last_updated": datetime|null}`

  **Must NOT do**:
  - G10: Do NOT implement hybrid search (vector + keyword) — cosine similarity only
  - G10: Do NOT add reranking
  - Do NOT implement sophisticated chunking (semantic, recursive) — fixed-size only
  - Do NOT add metadata filtering in search
  - Do NOT add document-level relevance scoring
  - Do NOT implement embedding caching

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: pgvector setup, embedding pipeline, vector search — requires careful integration
  - **Skills**: [`postgres-patterns`, `python-patterns`]
    - `postgres-patterns`: pgvector extension setup, vector column types, similarity queries
    - `python-patterns`: Async database operations, embedding pipeline
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: Less relevant than postgres-specific patterns for this task

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 37, 39)
  - **Parallel Group**: Wave 5.1
  - **Blocks**: Task 39 (Retrieval Skill), Task 45 (Knowledge Base UI)
  - **Blocked By**: Tasks 5, 10 (needs LLMClient for embeddings, DB setup)

  **References**:

  **Pattern References**:
  - `backend/services/document_service.py` (Task 16) — Service layer pattern with async DB access
  - `backend/core/llm.py` (Task 5) — LLMClient for embedding calls

  **API/Type References**:
  - `backend/models/` (Task 10) — SQLAlchemy model patterns, Base class
  - pgvector-python: https://github.com/pgvector/pgvector-python — SQLAlchemy integration

  **External References**:
  - pgvector docs: https://github.com/pgvector/pgvector
  - litellm embedding: https://docs.litellm.ai/docs/embedding/supported_embedding

  **WHY Each Reference Matters**:
  - LLMClient (Task 5): Must use the SAME litellm abstraction for embeddings — may need to add `embed()` method
  - pgvector-python: Need SQLAlchemy column type `Vector(1536)` and operator `<=>` for cosine distance

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/services/test_rag_service.py` → PASS (4+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Ingest and search knowledge
    Tool: Bash (pytest)
    Steps:
      1. Ingest document with content "投标书需要包含公司资质、项目经验、技术方案"
      2. Mock embedding API to return deterministic vectors
      3. Search with query "公司资质要求"
      4. Assert results contain the ingested chunk
      5. Assert results ordered by similarity (highest first)
    Expected Result: Vector search returns relevant chunks
    Evidence: .sisyphus/evidence/task-38-rag-search.txt

  Scenario: pgvector extension active
    Tool: Bash (psql or pytest)
    Steps:
      1. Run migration to create vector extension
      2. Query: SELECT * FROM pg_extension WHERE extname = 'vector'
      3. Assert extension exists
      4. Insert a test row with Vector(1536) column
      5. Assert insert succeeds
    Expected Result: pgvector extension is properly installed and functional
    Evidence: .sisyphus/evidence/task-38-pgvector-setup.txt

  Scenario: List, stats, and delete knowledge documents
    Tool: Bash (curl)
    Preconditions: Backend running, at least 1 document ingested
    Steps:
      1. GET /api/v1/knowledge/stats — assert total_documents >= 1, total_chunks >= 1
      2. GET /api/v1/knowledge/documents — assert array with >= 1 item, each has id, filename, chunk_count
      3. Save first document's id
      4. DELETE /api/v1/knowledge/documents/{id} — expect 204
      5. GET /api/v1/knowledge/documents — assert the deleted document is gone
      6. GET /api/v1/knowledge/stats — assert total_documents decremented by 1
    Expected Result: CRUD operations for knowledge documents work correctly
    Failure Indicators: 404 on list endpoint, delete returns 500, stats not updated
    Evidence: .sisyphus/evidence/task-38-knowledge-crud.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(rag): add RAG service with pgvector for knowledge base search and management`
  - Files: `backend/services/rag_service.py`, `backend/models/knowledge.py`, `backend/api/knowledge.py`, `backend/schemas/knowledge.py`, migration files, `backend/tests/services/test_rag_service.py`

- [x] 39. Retrieval Skill (RAG Integration)

  **What to do**:
  - Create `backend/skills/retrieval.py` — extends BaseSkill
  - Purpose: Retrieves relevant context from knowledge base to enhance section generation
  - `execute(context: SkillContext) -> SkillResult`:
    - Input: `query` (typically section title + outline description), `top_k` (default 5)
    - Calls `rag_service.search(query, top_k)`
    - Returns `SkillResult` with retrieved chunks formatted as context
    - Output format: numbered list of relevant excerpts with source attribution
  - Integration point: Called by `section_generation_skill` (Task 15) BEFORE generating content
    - Section generation prompt should include retrieved context as reference material
  - Update `section_generation_skill` to optionally call retrieval_skill first

  **Must NOT do**:
  - G10: Do NOT add query expansion or reformulation
  - G10: Do NOT add reranking of retrieved results
  - Do NOT implement retrieval caching
  - Do NOT make retrieval mandatory — it should gracefully handle empty knowledge base
  - Do NOT add user-facing retrieval controls (e.g., "search these sources")

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Skill integration connecting RAG service to content generation pipeline
  - **Skills**: [`python-patterns`, `coding-standards`]
    - `python-patterns`: Async service integration, error handling
    - `coding-standards`: Clean interfaces, type safety
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: Simple skill, doesn't need full backend architecture guidance

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 38)
  - **Parallel Group**: After Wave 5.1
  - **Blocks**: None directly
  - **Blocked By**: Tasks 6, 38 (needs BaseSkill, RAG service)

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill interface
  - `backend/skills/write_section.py` (Task 15) — Skill to integrate with
  - `backend/services/rag_service.py` (Task 38) — RAG service to call

  **API/Type References**:
  - `backend/models/knowledge.py` (Task 38) — KnowledgeChunk model returned by search

  **WHY Each Reference Matters**:
  - section_generation_skill (Task 15): This skill's output is injected into section generation prompts — must coordinate format
  - RAG service (Task 38): Direct dependency — calls search method

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/skills/test_retrieval_skill.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Retrieve relevant context for section generation
    Tool: Bash (pytest)
    Steps:
      1. Seed knowledge base with 10 chunks about "投标流程"
      2. Execute retrieval_skill with query="投标书技术方案编写要求"
      3. Assert SkillResult.content contains formatted context excerpts
      4. Assert at least 3 relevant chunks returned
      5. Assert source attribution present for each chunk
    Expected Result: Relevant knowledge retrieved and formatted for LLM consumption
    Evidence: .sisyphus/evidence/task-39-retrieval-basic.txt

  Scenario: Graceful handling of empty knowledge base
    Tool: Bash (pytest)
    Steps:
      1. Empty knowledge base (no chunks)
      2. Execute retrieval_skill with any query
      3. Assert SkillResult.content indicates no relevant context found
      4. Assert no error thrown
    Expected Result: Skill returns gracefully with empty results
    Evidence: .sisyphus/evidence/task-39-empty-kb.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(skills): add retrieval skill for RAG-enhanced content generation`
  - Files: `backend/skills/retrieval.py`, `backend/tests/skills/test_retrieval_skill.py`, `backend/skills/write_section.py` (modified)

### Wave 5.2 — Templates + Export (Tasks 40-41, parallel)

- [x] 40. Template Service

  **What to do**:
  - Create `backend/services/template_service.py` — Manages document templates
  - SQLAlchemy model in `backend/models/template.py` — implements the `templates` table already defined in Task 4's migration (DO NOT create a new migration for this table; Task 4 owns the schema):
    - `DocumentTemplate`: `id, name: str, doc_type: str, description: str, outline_structure: dict, section_prompts: dict, metadata: dict, is_default: bool, created_at`
    - `outline_structure`: JSON defining default section hierarchy for this doc type
    - `section_prompts`: JSON mapping section type → generation prompt hints
  - Methods:
    - `get_templates(doc_type: Optional[str]) -> list[DocumentTemplate]`
    - `get_template(template_id) -> DocumentTemplate`
    - `create_template(data) -> DocumentTemplate`
    - `apply_template(task_id, template_id)` — sets the task's outline to template structure
  - Seed 3 built-in templates:
    - 投标书 (Bid Document): typical structure (公司概况, 技术方案, 项目管理, 报价, ...)
    - 技术方案 (Technical Proposal): structure (背景分析, 需求分析, 技术架构, 实施计划, ...)
    - 可行性报告 (Feasibility Report): structure (项目背景, 市场分析, 技术可行性, 经济分析, ...)
  - API endpoints:
  - `GET /api/v1/templates` — list templates (optional `?doc_type=投标书`)
  - `GET /api/v1/templates/{id}` — get template details
    - `POST /api/v1/tasks/{id}/apply-template` with body `{"template_id": "..."}`

  **Must NOT do**:
  - G3: Do NOT add template editor UI in this task (separate task if needed)
  - G3: Do NOT make templates overly abstract — concrete structures for 3 doc types
  - Do NOT add template versioning
  - Do NOT add template inheritance or composition
  - Do NOT allow template deletion (seed data only for MVP)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Service with data model, seed data, and API endpoints
  - **Skills**: [`backend-patterns`, `python-patterns`]
    - `backend-patterns`: Service layer, REST endpoints
    - `python-patterns`: Data modeling, JSON schema design
  - **Skills Evaluated but Omitted**:
    - `api-design`: Simple CRUD, doesn't need full API design patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 41)
  - **Parallel Group**: Wave 5.2
  - **Blocks**: Task 46 (seed data uses templates)
  - **Blocked By**: Tasks 10, 12 (needs DB models, document service)

  **References**:

  **Pattern References**:
  - `backend/services/document_service.py` (Task 12) — Service layer pattern
  - `backend/skills/outline.py` (Task 14) — Outline generation that uses templates

  **API/Type References**:
  - `backend/models/document.py` (Task 10) — Document model that templates connect to

  **WHY Each Reference Matters**:
  - outline_generation_skill (Task 14): Templates provide the default structure that outline generation uses as a starting point
  - Document model: apply_template modifies the document's outline — must understand document schema

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/services/test_template_service.py` → PASS (4+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: List and apply template
    Tool: Bash (curl)
    Steps:
      1. GET /api/v1/templates?doc_type=投标书 → assert at least 1 template
      2. Create a new task
      3. POST /api/v1/tasks/{id}/apply-template body={"template_id": bid_template_id}
      4. GET /api/v1/tasks/{id}/sections → assert outline matches template structure
      5. Assert sections created match template's outline_structure
    Expected Result: Template applied creates correct document outline
    Evidence: .sisyphus/evidence/task-40-apply-template.txt

  Scenario: Three built-in templates seeded
    Tool: Bash (curl)
    Steps:
      1. GET /api/v1/templates → assert 3 templates returned
      2. Assert names: "投标书", "技术方案", "可行性报告"
      3. For each: assert outline_structure is non-empty dict
    Expected Result: All 3 seed templates present and valid
    Evidence: .sisyphus/evidence/task-40-seed-templates.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(templates): add template service with 3 built-in document templates`
  - Files: `backend/services/template_service.py`, `backend/models/template.py`, `backend/api/template.py`, migration file, seed data, `backend/tests/services/test_template_service.py`

- [x] 41. DOCX Export Service

  **What to do**:
  - Create `backend/services/export_service.py` — Exports document to DOCX format
  - Uses `python-docx` library
  - Method `export_docx(task_id: str) -> bytes`:
    - Loads document with all sections (latest version of each)
    - Creates DOCX with:
      - Document title as Heading 1
      - Each section title as Heading 2
      - Subsection titles as Heading 3
      - Section content as normal paragraphs
      - Basic formatting: headings, paragraphs, bullet lists (parsed from markdown)
    - Returns bytes (DOCX file content)
  - Markdown-to-DOCX conversion: Parse basic markdown (headings, bold, italic, lists) into python-docx elements
  - API endpoint:
    - `GET /api/v1/tasks/{id}/export/docx` — returns DOCX file as download (Content-Disposition: attachment)

  **Must NOT do**:
  - G11: Do NOT add custom styles, headers, footers, or page numbers
  - G11: Do NOT add table of contents generation
  - G11: Do NOT add image embedding
  - Do NOT add PDF export (explicitly excluded from MVP)
  - Do NOT add template-based DOCX styling
  - Do NOT add watermarks or logos

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: File generation service with markdown parsing and python-docx integration
  - **Skills**: [`python-patterns`, `backend-patterns`]
    - `python-patterns`: Binary file handling, markdown parsing
    - `backend-patterns`: File download endpoint design
  - **Skills Evaluated but Omitted**:
    - `api-design`: Single endpoint, simple download

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 40)
  - **Parallel Group**: Wave 5.2
  - **Blocks**: Task 43 (Export UI)
  - **Blocked By**: Tasks 10, 12 (needs document models and service)

  **References**:

  **Pattern References**:
  - `backend/services/document_service.py` (Task 12) — Loading document with sections

  **API/Type References**:
  - `backend/models/document.py` (Task 10) — Document and Section models
  - python-docx: https://python-docx.readthedocs.io/

  **WHY Each Reference Matters**:
  - Document service (Task 12): Must load the complete document structure before converting to DOCX
  - python-docx docs: Need correct API for adding headings, paragraphs, and basic formatting

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/services/test_export_service.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Export document as DOCX
    Tool: Bash (curl + python)
    Steps:
      1. Create task with document containing 3 sections with markdown content
      2. GET /api/v1/tasks/{id}/export/docx
      3. Assert HTTP 200 with Content-Type application/vnd.openxmlformats-officedocument.wordprocessingml.document
      4. Save response to test.docx
      5. Use python-docx to open test.docx and verify: 3 section headings present, paragraph content matches
    Expected Result: Valid DOCX file with correct structure and content
    Evidence: .sisyphus/evidence/task-41-export-docx.txt

  Scenario: Markdown formatting preserved
    Tool: Bash (pytest)
    Steps:
      1. Section content includes: "## 子标题\n\n**重点内容**和*斜体内容*\n\n- 列表项1\n- 列表项2"
      2. Export to DOCX
      3. Assert Heading 3 "子标题" present
      4. Assert bold run "重点内容" present
      5. Assert 2 bullet list items present
    Expected Result: Basic markdown formatting converted to DOCX formatting
    Evidence: .sisyphus/evidence/task-41-markdown-format.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(export): add DOCX export service with markdown-to-docx conversion`
  - Files: `backend/services/export_service.py`, `backend/api/export.py`, `backend/tests/services/test_export_service.py`

### Wave 5.3 — Frontend Advanced Pages (Tasks 42-45, parallel)

- [x] 42. Version Diff UI

  **What to do**:
  - Create `frontend/app/tasks/[id]/versions/page.tsx` — Version comparison page
  - Features:
    - Section selector: dropdown to choose which section's versions to view
    - Version list: chronological list of versions for selected section
      - Each entry: version number, date, change_source badge (生成/修订/手动), summary
    - Diff viewer: side-by-side or unified diff view
      - Version A selector (left/old) and Version B selector (right/new)
      - Highlighted additions (green) and deletions (red)
      - Line numbers
    - Rollback button: "回滚到此版本" with confirmation dialog
  - Components:
    - `frontend/components/version/diff-viewer.tsx` — Diff display component
    - `frontend/components/version/version-list.tsx` — Version history list
  - TanStack Query hooks in `frontend/lib/hooks/use-versions.ts`:
    - `useVersions(sectionId)` — fetch version list
    - `useDiff(versionAId, versionBId)` — fetch computed diff
    - `useRollback(sectionId)` — mutation

  **Must NOT do**:
  - Do NOT add inline diff editing
  - Do NOT add merge capabilities
  - Do NOT add version branching visualization
  - Do NOT implement more than 2-version comparison
  - G7: TanStack Query only for state

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex diff visualization with side-by-side view, syntax highlighting
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: Complex component composition, data-driven rendering
    - `coding-standards`: TypeScript, clean component structure
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Playwright in QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 43, 44, 45)
  - **Parallel Group**: Wave 5.3
  - **Blocks**: None
  - **Blocked By**: Task 37 (version management API)

  **References**:

  **Pattern References**:
  - `frontend/components/workbench/` (Tasks 33-35) — Component patterns from workbench

  **API/Type References**:
  - `backend/api/version.py` (Task 37) — Version and diff API endpoints
  - `backend/models/version.py` (Task 37) — SectionVersion, DiffResult types

  **WHY Each Reference Matters**:
  - Version API (Task 37): Frontend consumes diff results — must match DiffHunk/DiffLine format for rendering

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/diff-viewer.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: View diff between two versions
    Tool: Playwright
    Steps:
      1. Create section with 3 versions via API
      2. Navigate to /tasks/{id}/versions
      3. Select section from dropdown
      4. Assert version list shows 3 entries
      5. Select version 1 and version 3 for comparison
      6. Assert diff viewer shows additions in green, deletions in red
      7. Assert line numbers visible
      8. Take screenshot
    Expected Result: Side-by-side diff rendered with color coding
    Evidence: .sisyphus/evidence/task-42-diff-view.png

  Scenario: Rollback to previous version
    Tool: Playwright
    Steps:
      1. Navigate to version page, select version 1
      2. Click "回滚到此版本" button
      3. Assert confirmation dialog appears with warning text
      4. Confirm rollback
      5. Assert success notification
      6. Assert version list now shows new version (v4) with source "回滚"
    Expected Result: Rollback creates new version and updates UI
    Evidence: .sisyphus/evidence/task-42-rollback.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add version diff viewer with comparison and rollback`
  - Files: `frontend/app/tasks/[id]/versions/page.tsx`, `frontend/components/version/diff-viewer.tsx`, `frontend/components/version/version-list.tsx`, `frontend/lib/hooks/use-versions.ts`

- [x] 43. Export UI

  **What to do**:
  - Create `frontend/app/tasks/[id]/export/page.tsx` — Export page
  - Features:
    - Export preview: Shows document structure (section titles and word counts)
    - Export button: "导出 DOCX" — triggers download
    - Export status: Shows if document is ready for export (all sections generated, reviews complete)
    - Pre-export checklist:
      - ✓ 所有章节已生成 (All sections generated)
      - ✓ 审核已通过 (Reviews passed)
      - ✓ 最终审批已完成 (Final approval complete)
      - ✗ items block export button (disabled with explanation)
    - Download handling: fetch blob → trigger browser download with filename `{task_name}.docx`
  - Simple page — not complex

  **Must NOT do**:
  - Do NOT add PDF export option
  - Do NOT add export customization (format, style selection)
  - Do NOT add batch export (multiple documents)
  - Do NOT add export history/log
  - Do NOT add print preview

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple page with checklist and download button
  - **Skills**: [`frontend-patterns`]
    - `frontend-patterns`: File download patterns, component structure
  - **Skills Evaluated but Omitted**:
    - `coding-standards`: Simple page doesn't need full standards guidance

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 42, 44, 45)
  - **Parallel Group**: Wave 5.3
  - **Blocks**: None
  - **Blocked By**: Task 41 (export API), Task 31 (app shell)

  **References**:

  **Pattern References**:
  - `frontend/lib/api.ts` (Task 31) — API client for download requests

  **API/Type References**:
  - `backend/api/export.py` (Task 41) — `GET /api/v1/tasks/{id}/export/docx` endpoint

  **WHY Each Reference Matters**:
  - Export API (Task 41): Must handle binary response correctly — fetch as blob, not JSON

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/export-page.test.tsx` → PASS (2+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Export DOCX download
    Tool: Playwright
    Steps:
      1. Create fully reviewed and approved task
      2. Navigate to /tasks/{id}/export
      3. Assert all checklist items show ✓
      4. Assert "导出 DOCX" button is enabled
      5. Click export button
      6. Assert download triggered (check downloads directory)
      7. Assert downloaded file has .docx extension
    Expected Result: DOCX file downloaded successfully
    Evidence: .sisyphus/evidence/task-43-export-download.png

  Scenario: Export blocked when not ready
    Tool: Playwright
    Steps:
      1. Create task with sections NOT yet reviewed
      2. Navigate to /tasks/{id}/export
      3. Assert checklist shows ✗ for "审核已通过"
      4. Assert export button is disabled
      5. Assert tooltip or message explains why export is blocked
    Expected Result: Export properly gated by completion status
    Evidence: .sisyphus/evidence/task-43-export-blocked.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add export page with readiness checklist and DOCX download`
  - Files: `frontend/app/tasks/[id]/export/page.tsx`, `frontend/components/export/export-checklist.tsx`

- [x] 44. Annotation UI (Issue Inline Display)

  **What to do**:
  - Enhance `frontend/components/workbench/content-panel.tsx` (Task 34) with inline issue annotations
  - Features:
    - Review issues overlaid on section content at their `location_excerpt` positions
    - Issue markers: colored underlines or highlights on the relevant text
      - Critical: red underline
      - Major: orange underline
      - Minor: yellow underline
    - Hover/click on marked text → popover showing:
      - Reviewer name, severity badge, category
      - Issue description
      - Suggestion (if provided)
    - Toggle button: "显示/隐藏审核标注" (Show/Hide Annotations)
    - Issue navigation: "上一个问题" / "下一个问题" arrows to jump between issues
  - Create `frontend/components/workbench/annotation-overlay.tsx` — Annotation rendering
  - Create `frontend/components/workbench/issue-popover.tsx` — Issue detail popover

  **Must NOT do**:
  - Do NOT allow editing issues (read-only annotations)
  - Do NOT add issue resolution status (accept/reject)
  - Do NOT implement precise character-level highlighting (match on excerpt text, approximate)
  - Do NOT add annotation persistence (derived from review results, not stored separately)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex overlay UI with hover interactions, text highlighting, popovers
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: Overlay patterns, event handling, popover positioning
    - `coding-standards`: TypeScript, component structure
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Playwright in QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 42, 43, 45)
  - **Parallel Group**: Wave 5.3
  - **Blocks**: None
  - **Blocked By**: Task 34 (content panel to enhance), Task 27 (review results with location_excerpt)

  **References**:

  **Pattern References**:
  - `frontend/components/workbench/content-panel.tsx` (Task 34) — Component to enhance with annotations
  - `frontend/components/workbench/review-panel.tsx` (Task 35) — Issue data patterns

  **API/Type References**:
  - `backend/models/review_aggregation.py` (Task 27) — ReviewIssue with location_excerpt field
  - `frontend/lib/types.ts` (Task 31) — ReviewIssue TypeScript type

  **WHY Each Reference Matters**:
  - content-panel.tsx (Task 34): This task MODIFIES the existing content panel — don't create a new one
  - ReviewIssue.location_excerpt: This field is used to match issue positions in the rendered content

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/annotation-overlay.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Inline annotations displayed on content
    Tool: Playwright
    Steps:
      1. Task has section with review issues containing location_excerpt values
      2. Navigate to /tasks/{id}, select the reviewed section
      3. Assert colored underlines visible on content text
      4. Assert at least one red (critical), one orange (major) highlight visible
      5. Click on highlighted text
      6. Assert popover appears with reviewer name, description, suggestion
      7. Take screenshot
    Expected Result: Issues annotated inline with interactive popovers
    Evidence: .sisyphus/evidence/task-44-annotations.png

  Scenario: Toggle annotations on/off
    Tool: Playwright
    Steps:
      1. Annotations visible on content
      2. Click "隐藏审核标注" toggle button
      3. Assert all annotation highlights disappear
      4. Assert content text still visible (just no highlights)
      5. Click "显示审核标注" to re-enable
      6. Assert highlights reappear
    Expected Result: Annotations can be toggled without losing data
    Evidence: .sisyphus/evidence/task-44-toggle-annotations.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add inline review annotations with issue popovers`
  - Files: `frontend/components/workbench/annotation-overlay.tsx`, `frontend/components/workbench/issue-popover.tsx`, `frontend/components/workbench/content-panel.tsx` (modified)

- [x] 45. Knowledge Base UI

  **What to do**:
  - Create `frontend/app/knowledge/page.tsx` — Knowledge base management page
  - Features:
    - **Upload Section**: Drag-and-drop zone to upload reference documents
      - Accepts .docx, .pdf, .md, .txt files (knowledge base scope — .txt IS allowed; see "Supported File Types" in Verification Strategy)
      - Shows upload progress bar
      - After upload: triggers ingestion into RAG (POST /api/v1/knowledge/ingest)
    - **Document List**: Table of ingested documents
      - Columns: 文档名称, 类型, 块数 (chunk count), 上传时间
      - Delete button per document (removes chunks from vector store)
    - **Search Test**: Input field to test knowledge search
      - Enter query → shows top 5 retrieved chunks with similarity scores
      - Helps user verify knowledge base quality
    - **Stats**: Total documents, total chunks, last updated

  **Must NOT do**:
  - Do NOT add document preview/viewer
  - Do NOT add chunk editing or manual chunk creation
  - Do NOT add folder organization for documents
  - Do NOT add search filters (metadata, date range)
  - Do NOT add import from URL

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI page with drag-drop upload, data table, search interface
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: File upload patterns, data display
    - `coding-standards`: TypeScript, component structure
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Playwright in QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 42, 43, 44)
  - **Parallel Group**: Wave 5.3
  - **Blocks**: None
  - **Blocked By**: Task 38 (RAG service API), Task 31 (app shell)

  **References**:

  **Pattern References**:
  - `frontend/components/task/create-task-dialog.tsx` (Task 32) — File upload pattern
  - `frontend/lib/api.ts` (Task 31) — API client for requests

  **API/Type References**:
  - `backend/api/knowledge.py` (Task 38) — Endpoints: `POST /api/v1/knowledge/ingest`, `POST /api/v1/knowledge/search`, `GET /api/v1/knowledge/documents`, `DELETE /api/v1/knowledge/documents/{id}`, `GET /api/v1/knowledge/stats`
  - `backend/models/knowledge.py` (Task 38) — KnowledgeChunk type

  **WHY Each Reference Matters**:
  - File upload (Task 32): Reuse the same upload approach (FormData, progress tracking)
  - Knowledge API (Task 38): Must match request/response format — document list uses GET /documents, deletion uses DELETE /documents/{id}, stats uses GET /stats

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/knowledge-page.test.tsx` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Upload and ingest document
    Tool: Playwright
    Steps:
      1. Navigate to /knowledge
      2. Upload test-reference.docx via drag-drop zone
      3. Assert upload progress bar appears and completes
      4. Assert "正在处理..." (Processing) indicator
      5. Assert document appears in list with chunk count > 0
    Expected Result: Document uploaded and chunked into knowledge base
    Evidence: .sisyphus/evidence/task-45-upload-knowledge.png

  Scenario: Test knowledge search
    Tool: Playwright
    Steps:
      1. Knowledge base has ingested documents
      2. Enter query "投标书编写规范" in search test input
      3. Click search button
      4. Assert results section shows 5 chunks
      5. Assert each chunk shows content excerpt and similarity score
    Expected Result: Knowledge search returns relevant results
    Evidence: .sisyphus/evidence/task-45-search-test.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add knowledge base page with upload, search, and document management`
  - Files: `frontend/app/knowledge/page.tsx`, `frontend/components/knowledge/upload-zone.tsx`, `frontend/components/knowledge/search-test.tsx`, `frontend/lib/hooks/use-knowledge.ts`

### PHASE 6: Polish & Integration (Tasks 46-51)

### Wave 6.1 — Backend Polish (Tasks 46-48, parallel)

- [x] 46. Seed Data & Demo Flow

  **What to do**:
  - Create `backend/scripts/seed.py` — Database seed script
  - Seeds:
    - 3 document templates (already from Task 40 — this script ensures they exist on fresh DB)
    - 1 demo task with pre-populated document:
      - Task: "示例投标书 — 智慧城市项目"
      - Document type: 投标书
      - Outline: 6 sections (公司概况, 项目理解, 技术方案, 实施计划, 项目团队, 商务报价)
      - 2 sections pre-generated with sample content (so demo shows partial progress)
      - Outline already approved
    - 5 knowledge base reference documents (small text snippets about 投标书 best practices)
  - Make seed script idempotent (check before insert, don't duplicate)
  - Add environment variable `SEED_DEMO_DATA` (default: `true`). When `false`, seed script skips demo task and knowledge docs (only ensures templates exist). This enables testing empty-state UI scenarios.
  - Add to Docker entrypoint: `cd /app/backend && python scripts/seed.py` runs on first start
  - Add `backend/scripts/reset_db.py` — drops all tables and re-seeds (dev utility)

  **Must NOT do**:
  - Do NOT seed more than 1 demo task (keep it focused)
  - Do NOT seed with real company data — use clearly fictional "示例公司"
  - Do NOT make seed data depend on LLM calls — all content is static strings
  - Do NOT seed review results (user should trigger reviews themselves to see the flow)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Script writing with predefined data, straightforward
  - **Skills**: [`python-patterns`]
    - `python-patterns`: Script structure, idempotent operations
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: Seed script doesn't need architectural patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 47, 48)
  - **Parallel Group**: Wave 6.1
  - **Blocks**: Task 51 (e2e smoke test uses seed data)
  - **Blocked By**: Tasks 10, 40, 38 (needs DB models, templates, knowledge models)

  **References**:

  **Pattern References**:
  - `backend/models/` (Task 10) — All model classes for creating seed records
  - `backend/services/template_service.py` (Task 40) — Template creation

  **API/Type References**:
  - All backend models — seed script creates instances of every major model

  **WHY Each Reference Matters**:
  - Models (Task 10): Must use correct field names and types when constructing seed records
  - Templates (Task 40): Ensure seed templates match what Task 40 already seeds (avoid duplicates)

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/scripts/test_seed.py` → PASS (2+ tests, idempotency check)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Seed fresh database
    Tool: Bash
    Steps:
      1. Reset DB: cd backend && python scripts/reset_db.py
      2. Run seed: cd backend && python scripts/seed.py
      3. GET /api/v1/tasks → assert 1 demo task "示例投标书 — 智慧城市项目"
      4. GET /api/v1/templates → assert 3 templates
      5. GET /api/v1/knowledge/search body={"query": "投标", "top_k": 3} → assert results returned
    Expected Result: Seed data populates all major tables
    Evidence: .sisyphus/evidence/task-46-seed-data.txt

  Scenario: Seed is idempotent
    Tool: Bash
    Steps:
      1. Run seed twice: cd backend && python scripts/seed.py && python scripts/seed.py
      2. GET /api/v1/tasks → assert still only 1 demo task (not 2)
      3. GET /api/v1/templates → assert still only 3 templates
    Expected Result: Running seed twice doesn't create duplicates
    Evidence: .sisyphus/evidence/task-46-seed-idempotent.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(seed): add database seed script with demo task and reference data`
  - Files: `backend/scripts/seed.py`, `backend/scripts/reset_db.py`, `backend/tests/scripts/test_seed.py`

- [x] 47. Audit Log Service

  **What to do**:
  - Create `backend/services/audit_service.py` — Records all significant operations
  - Data model in `backend/models/audit.py`:
    - `AuditEntry`: `id, task_id: Optional[str], action: str, entity_type: str, entity_id: str, details: dict, timestamp`
    - `action` values: "created", "updated", "generated", "reviewed", "approved", "exported", "rolled_back"
    - `entity_type` values: "task", "document", "section", "review", "approval"
  - Methods:
    - `log(task_id, action, entity_type, entity_id, details=None)` — creates audit entry
    - `get_audit_log(task_id, limit=50, offset=0) -> list[AuditEntry]` — paginated history
    - `get_task_timeline(task_id) -> list[AuditEntry]` — full task history for timeline display
  - Integrate audit logging into existing services:
    - document_service: log document creation, section generation
    - review_service: log review runs, results
    - approval endpoints: log approvals, change requests
    - export_service: log exports
    - version_service: log rollbacks
  - API endpoint:
    - `GET /api/v1/tasks/{id}/audit` — returns audit log with pagination

  **Must NOT do**:
  - Do NOT add audit log search or filtering (MVP — chronological list only)
  - Do NOT add audit log export
  - Do NOT add audit log retention policy or cleanup
  - Do NOT add system-level audit (only task-level)
  - Do NOT add audit log visualization (timeline is in frontend Task 35 area)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Cross-cutting service with integration points across many existing services
  - **Skills**: [`backend-patterns`, `python-patterns`]
    - `backend-patterns`: Cross-cutting concern integration
    - `python-patterns`: Decorator/middleware patterns for logging
  - **Skills Evaluated but Omitted**:
    - `api-design`: Single paginated endpoint

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 46, 48)
  - **Parallel Group**: Wave 6.1
  - **Blocks**: None directly
  - **Blocked By**: Tasks 12, 27, 30, 37, 41 (services to integrate into)

  **References**:

  **Pattern References**:
  - `backend/services/document_service.py` (Task 12) — Service to add audit calls into
  - `backend/services/review_service.py` (Task 27) — Service to add audit calls into
  - `backend/services/version_service.py` (Task 37) — Service to add audit calls into

  **API/Type References**:
  - `backend/models/` (Task 10) — DB model patterns for AuditEntry

  **WHY Each Reference Matters**:
  - Each service reference: Must add `audit_service.log()` calls at the right points without changing existing behavior

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/services/test_audit_service.py` → PASS (4+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Audit trail for task lifecycle
    Tool: Bash (curl)
    Steps:
      1. Create task (POST /api/v1/tasks)
      2. Upload document
      3. Approve outline
      4. Run reviews
      5. GET /api/v1/tasks/{id}/audit
      6. Assert audit entries: task_created, document_uploaded, outline_approved, review_run
      7. Assert entries ordered chronologically
    Expected Result: Complete audit trail of task operations
    Evidence: .sisyphus/evidence/task-47-audit-trail.txt

  Scenario: Audit log pagination
    Tool: Bash (curl)
    Steps:
      1. Task with 10+ audit entries
      2. GET /api/v1/tasks/{id}/audit?limit=5&offset=0 → assert 5 entries
      3. GET /api/v1/tasks/{id}/audit?limit=5&offset=5 → assert next 5 entries
      4. Assert no overlap between pages
    Expected Result: Pagination works correctly
    Evidence: .sisyphus/evidence/task-47-audit-pagination.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(audit): add audit log service with cross-service integration`
  - Files: `backend/services/audit_service.py`, `backend/models/audit.py`, `backend/api/audit.py`, migration file, `backend/tests/services/test_audit_service.py`, modified service files

- [x] 48. Comparison Skill

  **What to do**:
  - Create `backend/skills/comparison.py` — extends BaseSkill
  - Purpose: Compares a generated section against reference material or requirements
  - `execute(context: SkillContext) -> SkillResult`:
    - Input: `section_content`, `reference_content` (from knowledge base or requirements), `comparison_type` ("requirements_match" | "reference_alignment")
    - For "requirements_match": checks if section content addresses the extracted requirements
    - For "reference_alignment": checks if section aligns with reference document style/content
    - Calls LLM with structured prompt asking for: coverage score (0-100), missing items, alignment notes
    - Returns `SkillResult` with comparison report
  - Can be used by reviewers or as a standalone analysis tool
  - API endpoint: `POST /api/v1/tasks/{id}/sections/{sid}/compare` with body `{"reference_id": "...", "type": "requirements_match"}`

  **Must NOT do**:
  - Do NOT implement automated comparison without LLM (no rule-based matching)
  - G2: All LLM calls via litellm
  - Do NOT add comparison visualization (frontend handles display)
  - Do NOT implement multi-document comparison (one section vs one reference)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: LLM-powered analysis skill with structured output
  - **Skills**: [`python-patterns`, `coding-standards`]
    - `python-patterns`: Clean async implementation
    - `coding-standards`: Type safety, naming
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: Simple skill, not a full service

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 46, 47)
  - **Parallel Group**: Wave 6.1
  - **Blocks**: None
  - **Blocked By**: Tasks 5, 6, 38 (needs LLMClient, BaseSkill, RAG service for reference retrieval)

  **References**:

  **Pattern References**:
  - `backend/skills/base.py` (Task 6) — BaseSkill interface
  - `backend/skills/retrieval.py` (Task 39) — Sibling skill pattern

  **API/Type References**:
  - `backend/core/llm.py` (Task 5) — LLMClient for LLM calls
  - `backend/services/rag_service.py` (Task 38) — For retrieving reference content

  **WHY Each Reference Matters**:
  - retrieval_skill (Task 39): Can retrieve reference content from knowledge base as input to comparison

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `backend/tests/skills/test_comparison_skill.py` → PASS (3+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Requirements coverage comparison
    Tool: Bash (pytest)
    Steps:
      1. Section content about "技术方案" covering 3 of 5 requirements
      2. Reference: extracted requirements list with 5 items
      3. Mock LLM to return coverage_score=60, missing=["需求4", "需求5"]
      4. Execute comparison_skill with type="requirements_match"
      5. Assert SkillResult contains score=60, missing items listed
    Expected Result: Comparison identifies coverage gaps
    Evidence: .sisyphus/evidence/task-48-requirements-compare.txt

  Scenario: Reference alignment check
    Tool: Bash (pytest)
    Steps:
      1. Section content and reference document excerpt
      2. Execute with type="reference_alignment"
      3. Assert result includes alignment notes and suggestions
    Expected Result: Alignment analysis provided
    Evidence: .sisyphus/evidence/task-48-reference-align.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(skills): add comparison skill for requirements and reference alignment`
  - Files: `backend/skills/comparison.py`, `backend/skills/prompts/comparison.txt`, `backend/api/comparison.py`, `backend/tests/skills/test_comparison_skill.py`

### Wave 6.2 — Quality Dashboard + Docker (Tasks 49-50, parallel)

- [x] 49. Quality Dashboard Page

  **What to do**:
  - Create `frontend/app/tasks/[id]/quality/page.tsx` — Quality overview dashboard
  - Features:
    - **Summary Cards** (static display, no charts):
      - 综合评分 (Overall Score): large number display with color (green ≥80, yellow ≥60, red <60)
      - 审核轮次 (Review Rounds): number of revision rounds completed
      - 问题统计 (Issue Stats): critical/major/minor counts with colored badges
      - 需求覆盖率 (Requirements Coverage): percentage from comparison skill
    - **Reviewer Scorecard**: Table of 8 reviewers with pass/fail status and individual scores
    - **Issue Trend** (text-based, not chart):
      - Per-round summary: "第1轮: 12问题 → 第2轮: 5问题 → 第3轮: 1问题"
      - Shows improvement trajectory as text
    - **Comparison Results** (if comparison skill was run):
      - Coverage score
      - Missing requirements list
    - Link to detailed review dashboard (Task 36)

  **Must NOT do**:
  - G12: Do NOT add charts library (Chart.js, Recharts, D3, etc.) — cards and tables only
  - G12: Do NOT add pie charts, bar charts, or line charts
  - Do NOT add historical trend across tasks (single-task view only)
  - Do NOT add quality score configuration or weighting UI
  - Do NOT add PDF report generation from dashboard

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Dashboard layout with summary cards and data display
  - **Skills**: [`frontend-patterns`, `coding-standards`]
    - `frontend-patterns`: Dashboard patterns, card layouts
    - `coding-standards`: TypeScript, clean components
  - **Skills Evaluated but Omitted**:
    - `e2e-testing`: Playwright in QA scenarios

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 50)
  - **Parallel Group**: Wave 6.2
  - **Blocks**: None
  - **Blocked By**: Tasks 27, 36, 48 (review data, review dashboard pattern, comparison results)

  **References**:

  **Pattern References**:
  - `frontend/app/tasks/[id]/reviews/page.tsx` (Task 36) — Review dashboard to link to
  - `frontend/components/review/reviewer-card.tsx` (Task 36) — Reuse reviewer card components

  **API/Type References**:
  - `backend/api/review.py` (Task 27) — Review aggregation data
  - `backend/api/comparison.py` (Task 48) — Comparison results

  **WHY Each Reference Matters**:
  - reviewer-card (Task 36): Reuse existing components — don't rebuild reviewer display
  - Review API: Quality dashboard consumes aggregated review data for score cards

  **Acceptance Criteria**:
  **TDD:**
  - [ ] `frontend/__tests__/quality-dashboard.test.tsx` → PASS (2+ tests)

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Quality dashboard displays scores
    Tool: Playwright
    Steps:
      1. Task with completed reviews (overall score 78, 2 rounds, 3 major + 5 minor issues)
      2. Navigate to /tasks/{id}/quality
      3. Assert "综合评分" card shows "78" in yellow color
      4. Assert "审核轮次" shows "2"
      5. Assert "问题统计" shows major:3, minor:5
      6. Assert reviewer scorecard table has 8 rows
      7. Take screenshot
    Expected Result: Quality metrics displayed as static summary cards
    Evidence: .sisyphus/evidence/task-49-quality-dashboard.png

  Scenario: Issue trend text display
    Tool: Playwright
    Steps:
      1. Task with 3 review rounds
      2. Assert trend text shows "第1轮: 12问题 → 第2轮: 5问题 → 第3轮: 1问题"
      3. Assert NO chart elements present (no canvas, svg chart, etc.)
    Expected Result: Text-based trend without charts (G12 compliance)
    Evidence: .sisyphus/evidence/task-49-issue-trend.png
  ```

  **Commit**: YES (standalone)
  - Message: `feat(frontend): add quality dashboard with summary cards and reviewer scorecard`
  - Files: `frontend/app/tasks/[id]/quality/page.tsx`, `frontend/components/quality/score-card.tsx`, `frontend/components/quality/reviewer-scorecard.tsx`

- [x] 50. Docker Compose Finalization

  **What to do**:
  - Update `docker-compose.yml` (Task 3) to production-ready MVP configuration
  - Services:
    - `postgres`: PostgreSQL 16 with pgvector extension
      - Volume for data persistence
      - Health check: `pg_isready`
    - `backend`: FastAPI application
      - Dockerfile: Python 3.11, pip install requirements, uvicorn
      - Depends on: postgres (health check)
      - Environment: DATABASE_URL, LITELLM config, CORS origins
      - Runs migrations on startup, then seed script, then uvicorn
      - Port: 8000
    - `frontend`: Next.js application
      - Dockerfile: Node 20, npm install, npm run build, npm start
      - Depends on: backend (health check)
      - Environment: NEXT_PUBLIC_API_URL=http://backend:8000
      - Port: 3000
  - Create `backend/Dockerfile` — Multi-stage build
  - Create `frontend/Dockerfile` — Multi-stage build
  - Create `.env.example` — Template with all required environment variables
  - Add `backend/healthcheck.py` — simple `/health` endpoint
  - Update `docker-compose.yml` health checks for all services
  - Add `scripts/start.sh` — one-command startup: `docker compose up -d`

  **Must NOT do**:
  - Do NOT add nginx reverse proxy (direct port exposure for MVP)
  - Do NOT add Redis or caching layer
  - Do NOT add logging aggregation (ELK, etc.)
  - Do NOT add SSL/TLS configuration
  - Do NOT add container resource limits (memory, CPU)
  - Do NOT add multiple environments (dev/staging/prod)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Docker multi-service orchestration with health checks, build stages, environment config
  - **Skills**: [`docker-patterns`, `deployment-patterns`]
    - `docker-patterns`: Dockerfile best practices, compose orchestration
    - `deployment-patterns`: Health checks, startup ordering, environment management
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: Not about backend code, about infrastructure

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 49)
  - **Parallel Group**: Wave 6.2
  - **Blocks**: Task 51 (e2e needs Docker running)
  - **Blocked By**: All backend + frontend tasks (needs complete codebase to containerize)

  **References**:

  **Pattern References**:
  - `docker-compose.yml` (Task 3) — Existing compose file to finalize
  - `backend/` and `frontend/` — Complete codebases to containerize

  **API/Type References**:
  - All environment variables used across backend and frontend services

  **External References**:
  - Docker multi-stage builds: https://docs.docker.com/build/building/multi-stage/
  - pgvector Docker: https://hub.docker.com/r/pgvector/pgvector

  **WHY Each Reference Matters**:
  - Existing docker-compose.yml (Task 3): MODIFY, don't recreate — preserve any existing configuration
  - pgvector Docker image: Must use pgvector-enabled PostgreSQL image, not vanilla postgres

  **Acceptance Criteria**:
  **TDD:**
  - [ ] No unit tests — infrastructure tested via QA scenarios

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Full stack startup from scratch
    Tool: Bash
    Steps:
      1. docker compose down -v (clean state)
      2. docker compose build (all 3 services)
      3. docker compose up -d
      4. Wait 30s for services to start
      5. docker compose ps → assert all 3 services "healthy"
      6. curl http://localhost:8000/health → assert 200 OK
      7. curl http://localhost:3000 → assert 200 OK with HTML content
      8. curl http://localhost:8000/api/v1/tasks → assert 200 with demo task from seed
    Expected Result: All services start and communicate correctly
    Evidence: .sisyphus/evidence/task-50-docker-startup.txt

  Scenario: Data persists across restarts
    Tool: Bash
    Steps:
      1. docker compose up -d (services running)
      2. Create a task via API: curl -X POST http://localhost:8000/api/v1/tasks ...
      3. docker compose down (stop, keep volumes)
      4. docker compose up -d (restart)
      5. curl http://localhost:8000/api/v1/tasks → assert created task still exists
    Expected Result: PostgreSQL data persists via Docker volume
    Evidence: .sisyphus/evidence/task-50-data-persistence.txt
  ```

  **Commit**: YES (standalone)
  - Message: `feat(docker): finalize Docker Compose with multi-stage builds and health checks`
  - Files: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.env.example`, `backend/healthcheck.py`, `scripts/start.sh`

### Wave 6.3 — End-to-End Smoke Test (Task 51)

- [x] 51. End-to-End Smoke Test

  **What to do**:
  - Create `e2e/smoke.test.ts` — Playwright end-to-end test covering the FULL user journey
  - Test flow (the complete happy path):
    1. Open app → assert home page loads with seed demo task
    2. Click "新建任务" → create new task "E2E测试投标书" with type 投标书, attach test DOCX file in dialog (`e2e/fixtures/test-doc.docx`)
    3. Assert task created and appears in task list with status "已创建"
    4. Click task row → navigate to workbench (/tasks/{id})
    5. Assert "开始处理" button visible (documents uploaded via create dialog)
    6. Click "开始处理" button → pipeline starts
    7. Wait for document parsing (SSE events)
    8. Assert outline generated in left panel
    9. Click "审批大纲" → approve outline
    10. Wait for section generation (SSE events, may take time with mock LLM)
    11. Assert sections appear in outline with content in center panel
    12. Click "运行审核" → wait for reviews to complete
    13. Assert review results in right panel with scores and issues
    14. Navigate to review dashboard (/tasks/{id}/reviews) → assert all 8 reviewers shown
    15. Navigate back to workbench
    16. If revision needed: assert auto-revision runs (or manually approve)
    17. Click "批准" on final approval
    18. Navigate to export page → assert checklist all green
    19. Click "导出 DOCX" → assert download
    20. Navigate to knowledge base → upload a reference doc → test search
    21. Navigate to quality dashboard → assert scores displayed
    22. Navigate to version page → assert versions listed for a section
  - Create `e2e/fixtures/test-doc.docx` — Simple DOCX with 3 sections of Chinese text
  - Configure Playwright for this project: `e2e/playwright.config.ts`
  - LLM mocking strategy: Use litellm's mock mode or set up a mock server that returns deterministic responses

  **Must NOT do**:
  - Do NOT test edge cases in e2e (that's for unit tests)
  - Do NOT make e2e depend on real LLM API calls — must work with mock/deterministic responses
  - Do NOT add e2e tests for error scenarios (happy path only for smoke test)
  - Do NOT add visual regression testing
  - Do NOT add performance benchmarks in e2e

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex 21-step end-to-end test requiring SSE waits, file operations, and multi-page navigation
  - **Skills**: [`e2e-testing`, `frontend-patterns`]
    - `e2e-testing`: Playwright configuration, test patterns, wait strategies
    - `frontend-patterns`: Understanding page structure for selector targeting
  - **Skills Evaluated but Omitted**:
    - `coding-standards`: E2E tests have their own conventions (e2e-testing skill covers this)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 6.3 (final, sequential)
  - **Blocks**: Final Verification Wave (F1-F4)
  - **Blocked By**: ALL previous tasks (needs complete system running)

  **References**:

  **Pattern References**:
  - All frontend pages (Tasks 31-36, 42-45, 49) — Page structure and selectors for test targets
  - `backend/services/progress_service.py` (Task 11) — SSE event types to wait for

  **API/Type References**:
  - All API endpoints — test calls APIs directly and via UI interactions
  - `frontend/lib/types.ts` (Task 31) — Understanding expected data shapes

  **External References**:
  - Playwright docs: https://playwright.dev/docs/intro

  **WHY Each Reference Matters**:
  - All pages: Must know exact selectors (button text, class names) to interact with
  - SSE events: Must wait for correct events between pipeline steps (e.g., wait for "section_generated" before checking content)

  **Acceptance Criteria**:
  **TDD:**
  - [ ] Not TDD — this IS the test

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Complete happy path smoke test
    Tool: Playwright
    Steps:
      1. docker compose up -d (fresh start with seed data)
      2. npx playwright test e2e/smoke.test.ts
       3. Assert all 22 steps pass
      4. Assert test captures screenshots at key milestones
      5. Assert test completes within 5 minutes (timeout)
    Expected Result: Full user journey works end-to-end
    Failure Indicators: Any step timeout, missing element, wrong status, download failure
    Evidence: .sisyphus/evidence/task-51-e2e-smoke/

  Scenario: Smoke test works with mock LLM
    Tool: Bash
    Steps:
      1. Set LITELLM_MOCK=true in .env
      2. docker compose up -d
      3. Run smoke test
      4. Assert test passes without real API calls
      5. Assert no OPENAI_API_KEY needed
    Expected Result: E2E test works fully offline with mock LLM
    Evidence: .sisyphus/evidence/task-51-mock-llm.txt
  ```

  **Commit**: YES (standalone)
  - Message: `test(e2e): add end-to-end smoke test covering complete user journey`
  - Files: `e2e/smoke.test.ts`, `e2e/playwright.config.ts`, `e2e/fixtures/test-doc.docx`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
>
> **These are REVIEW tasks, not implementation tasks.** Each agent reads the codebase and plan, runs verification commands, and produces a structured APPROVE/REJECT verdict. QA scenarios below define exactly what each agent must execute and verify.

- [x] F1. **Plan Compliance Audit** — `oracle`

  **What to do**:
  - Read `.sisyphus/plans/doc-agent-platform.md` end-to-end
  - For each "Must Have" in Work Objectives: verify implementation exists by reading the file, curling the endpoint, or running the command
  - For each "Must NOT Have" (G1-G12): grep the codebase for forbidden patterns — reject with file:line if found
  - Check `.sisyphus/evidence/` directory: verify evidence files exist for all 51 tasks
  - Compare final deliverables list against plan deliverables

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Verify all Must Have deliverables exist
    Tool: Bash
    Steps:
      1. Read plan Work Objectives "Must Have" section
      2. For each deliverable, run: ls -la <file_path> OR curl -s http://localhost:8000/<endpoint> OR run verification command
      3. Record pass/fail for each item
      4. Count: total must-haves vs verified
    Expected Result: ALL must-haves present — 0 missing
    Failure Indicators: Any file not found, any endpoint returning 404, any command failing
    Evidence: .sisyphus/evidence/F1-must-have-audit.md

  Scenario: Verify all Must NOT Have guardrails are respected
    Tool: Bash
    Steps:
      1. G1: grep -r "content" backend/orchestrator/ — verify no document body text stored in LangGraph state TypedDict
      2. G2: grep -rn "import openai" backend/ — must return 0 results (all via litellm)
      3. G5: grep -rn "websocket\|WebSocket" backend/ frontend/ — must return 0 results
      4. G6: grep -rn "authenticate\|authorization\|@login_required\|JWT" backend/ — must return 0 results
      5. G8: grep -rn "max.*revis\|MAX.*LOOP\|revision.*limit" backend/orchestrator/ — verify limit is 3
      6. Record pass/fail for each guardrail
    Expected Result: ALL guardrails respected — 0 violations
    Failure Indicators: Any grep returning unexpected matches
    Evidence: .sisyphus/evidence/F1-guardrail-audit.md

  Scenario: Verify evidence files exist for all tasks
    Tool: Bash
    Steps:
      1. ls -la .sisyphus/evidence/ | wc -l — count total evidence files
      2. For each task 1-51, check at least one evidence file matching pattern task-{N}-*
      3. Count: tasks with evidence vs total tasks
    Expected Result: All 51 tasks have at least one evidence file
    Failure Indicators: Any task missing evidence files
    Evidence: .sisyphus/evidence/F1-evidence-coverage.md
  ```

  **Output Format**: `Must Have [N/N] | Must NOT Have [N/N] | Evidence [N/51] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`

  **What to do**:
  - Run backend test suite: `cd backend && pytest tests/ -v --tb=short`
  - Run frontend test suite: `cd frontend && npm run test`
  - Run frontend build: `cd frontend && npm run build`
  - Grep all backend Python files for quality anti-patterns
  - Grep all frontend TypeScript files for quality anti-patterns
  - Check for AI slop patterns: excessive comments, over-abstraction, generic variable names

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`coding-standards`]

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Backend tests pass
    Tool: Bash
    Steps:
      1. cd backend && pytest tests/ -v --tb=short 2>&1
      2. Capture exit code
      3. Parse output: count passed, failed, errors
    Expected Result: Exit code 0, all tests pass, 0 failures, 0 errors
    Failure Indicators: Non-zero exit code, any FAILED or ERROR lines
    Evidence: .sisyphus/evidence/F2-backend-tests.txt

  Scenario: Frontend tests and build pass
    Tool: Bash
    Steps:
      1. cd frontend && npm run test 2>&1 — capture test output
      2. cd frontend && npm run build 2>&1 — capture build output
      3. Verify both exit with code 0
    Expected Result: All frontend tests pass, build completes with no type errors
    Failure Indicators: Non-zero exit code, TypeScript errors, test failures
    Evidence: .sisyphus/evidence/F2-frontend-tests.txt

  Scenario: No code quality anti-patterns
    Tool: Bash
    Steps:
      1. grep -rn "as any\|@ts-ignore\|@ts-nocheck" frontend/ --include="*.ts" --include="*.tsx" | wc -l — expect 0
      2. grep -rn "bare except:\|except:" backend/ --include="*.py" | grep -v "except.*:" | wc -l — check for bare except
      3. grep -rn "^[[:space:]]*print(" backend/ --include="*.py" | grep -v "tests/" | wc -l — no print() in prod code
      4. grep -rn "console\.log" frontend/ --include="*.ts" --include="*.tsx" | grep -v "__tests__/" | wc -l — no console.log in prod
      5. grep -rn "TODO\|FIXME\|HACK\|XXX" backend/ frontend/ --include="*.py" --include="*.ts" --include="*.tsx" | wc -l — document any remaining
    Expected Result: 0 instances of as any, bare except, print() in prod, console.log in prod
    Failure Indicators: Any non-zero count for prohibited patterns
    Evidence: .sisyphus/evidence/F2-quality-grep.txt
  ```

  **Output Format**: `Backend Tests [PASS/FAIL N/N] | Frontend Tests [PASS/FAIL] | Build [PASS/FAIL] | Anti-patterns [N found] | VERDICT: APPROVE/REJECT`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill for UI)

  **What to do**:
  - Start from completely clean state (fresh containers + DB)
  - Execute the full end-to-end user journey manually via Playwright browser automation
  - Verify every page, every interaction, every API response
  - Test cross-feature integration (features working together, not in isolation)
  - Test edge cases: empty state, invalid input, rapid clicks

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`playwright`, `e2e-testing`]

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Full end-to-end user journey
    Tool: Playwright
    Steps:
      1. docker compose down -v && docker compose up -d — fresh start
      2. Wait for http://localhost:3000 to respond (timeout: 30s)
      3. Navigate to http://localhost:3000 — verify task home page loads, see "任务列表" heading
       4. Click "新建任务" button — verify task creation dialog appears
       5. Fill in task name "测试报告", select doc_type "技术方案", attach sample DOCX file via file upload field in dialog, submit
       6. Verify task appears in list with status "已创建"
       7. Click task row → navigate to workbench page at /tasks/{id}
       8. Verify "开始处理" button is visible in top bar (documents already uploaded via create dialog)
       9. Click "开始处理" button to start pipeline
       10. Wait for parsing progress via SSE (right panel progress steps update)
       11. Verify outline sections appear in left panel (outline-panel.tsx tree view)
       12. Click "审批大纲" (approve outline) button in left panel
       13. Wait for section generation to complete (SSE progress updates in right panel)
       14. Verify right panel shows review summary with 8 reviewer scores
       15. Verify each reviewer shows structured ReviewIssue list (not empty)
       16. Verify at least one reviewer has issues with severity "critical" or "major"
       17. Click "需要修改" (Request Changes) button in right panel — triggers revision cycle
       18. Wait for revision + re-review cycle to complete (SSE progress shows 修订 → 审核)
       19. Navigate to export page — click "导出 DOCX"
       20. Verify DOCX file downloads successfully (non-zero file size)
       21. Take screenshot at each major step
    Expected Result: Complete user journey works end-to-end without errors
    Failure Indicators: Any page not loading, any button not responding, any API error, download failure
    Evidence: .sisyphus/evidence/F3-e2e-journey/

  Scenario: Edge case — empty state and error handling
    Tool: Playwright
    Preconditions: Restart backend with env SEED_DEMO_DATA=false, run reset_db.py + seed.py (templates only, no demo task)
    Steps:
      1. Navigate to http://localhost:3000 — verify empty state "暂无任务" (no tasks, only templates seeded)
      2. Verify empty state message displayed (not blank page, not error)
      3. Try to navigate to /tasks/nonexistent-uuid — verify 404 or redirect, not crash
      4. Create task, upload invalid file (e.g., .txt instead of .docx) — verify error message "不支持的文件类型" shown (NOTE: .txt is invalid for TASK uploads but valid for KNOWLEDGE BASE uploads — see "Supported File Types" in Verification Strategy)
      5. Create task, upload very small DOCX (1 paragraph) — verify it still processes
    Expected Result: All edge cases handled gracefully with user-facing messages in Chinese
    Failure Indicators: Blank pages, uncaught exceptions, English error messages, stack traces
    Evidence: .sisyphus/evidence/F3-edge-cases/
  ```

  **Output Format**: `E2E Journey [PASS/FAIL] | Edge Cases [N/N pass] | Screenshots [N captured] | VERDICT: APPROVE/REJECT`

- [x] F4. **Scope Fidelity Check** — `deep`

  **What to do**:
  - For each of the 51 tasks: read the task spec "What to do", then read the actual implementation via git diff
  - Verify 1:1 mapping — everything specified was built (no missing), nothing beyond spec was built (no creep)
  - Check all "Must NOT do" items per task are respected
  - Check guardrails G1-G12 compliance across all files
  - Detect cross-task contamination: any task touching another task's designated files
  - Flag any unaccounted file changes not covered by any task spec

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **QA Scenarios (MANDATORY):**
  ```
  Scenario: Verify spec-to-implementation fidelity for all tasks
    Tool: Bash
    Preconditions: All 51 tasks completed, all commits pushed
    Steps:
      1. Read .sisyphus/plans/doc-agent-platform.md — extract "What to do" and "Files:" for each task
      2. Run git log --oneline — list all commits
      3. Note: Some commits cover multiple tasks (grouped commits per Commit Strategy table).
         Map commits to tasks by matching commit message convention (e.g., "feat(review): 8 reviewers" covers Tasks 19-26)
      4. For each commit group: git diff <commit>^..<commit> — list files changed
      5. For each TASK (not commit): verify all files listed in the task's "Files:" field exist on disk
         Use `ls` or `test -f` to confirm file existence rather than relying solely on git diff
      6. For each task: verify key deliverables from "What to do" are present:
         - Functions/classes defined (grep for class/function names)
         - Endpoints registered (grep router files for route decorators)
         - Test files exist and contain test functions
      7. For each task: verify no "Must NOT do" items are present (grep for forbidden patterns)
      8. Tally: tasks fully compliant, tasks with missing items, tasks with scope creep
    Expected Result: 51/51 tasks fully compliant — all specified deliverables exist, no "Must NOT do" violations
    Failure Indicators: Any task's specified files missing, any "Must NOT do" pattern found in code
    Evidence: .sisyphus/evidence/F4-fidelity-matrix.md

  Scenario: Verify guardrail compliance across entire codebase
    Tool: Bash
    Steps:
      1. G1: Read backend/orchestrator/state.py — verify DocumentState TypedDict contains ONLY IDs/statuses/flags, NO content fields
      2. G2: grep -rn "from openai\|import openai" backend/ — must return 0
      3. G3: grep -rn "TemplateFactory\|AbstractTemplate\|BaseTemplate" backend/ — must return 0 (no premature abstraction)
      4. G4: grep -rn "def [a-z].*session\.execute\|def [a-z].*session\.query" backend/ | grep -v "async def" — must return 0 (no sync DB)
      5. G5: grep -rn "websocket\|WebSocket" backend/ frontend/ — must return 0
      6. G6: grep -rn "auth\|login\|password\|token" backend/api/ — must return 0 (no auth)
      7. G7: grep -rn "zustand\|redux\|jotai\|recoil" frontend/ — must return 0 (TanStack Query only)
      8. G8: grep -rn "max.*revis\|MAX.*LOOP\|revision.*limit" backend/orchestrator/ — verify limit is exactly 3
      9. G9: Check each reviewer file in backend/review/ — verify single LLM call pattern (no multi-turn)
      10. G10: grep -rn "rerank\|hybrid_search\|RRF" backend/ — must return 0
      11. G11: grep -rn "add_header\|add_footer\|custom_style" backend/ — must return 0
      12. G12: grep -rn "chart\|Chart\|plotly\|recharts\|d3" frontend/ — must return 0
    Expected Result: ALL 12 guardrails pass — 0 violations
    Failure Indicators: Any grep returning unexpected matches
    Evidence: .sisyphus/evidence/F4-guardrail-compliance.md

  Scenario: Detect cross-wave file contamination
    Tool: Bash
    Steps:
      1. Group commits by wave (using Commit Strategy table and commit messages)
      2. For each wave's commits: extract list of changed files
      3. Build ownership matrix: file → wave(s) that modified it
      4. Flag any file modified by 2+ waves where NOT expected:
         Allowlist (expected multi-wave files): docker-compose.yml, package.json, pyproject.toml,
         backend/orchestrator/graph.py (extended across waves), backend/main.py (router registration),
         frontend/app/layout.tsx (navigation updates)
      5. Count: contaminated files (non-allowlisted files touched by multiple unrelated waves)
    Expected Result: 0 contaminated files outside allowlist
    Failure Indicators: Non-allowlisted files modified by multiple unrelated waves
    Evidence: .sisyphus/evidence/F4-contamination-check.md
  ```

  **Output Format**: `Fidelity [N/51 compliant] | Guardrails [12/12 pass] | Contamination [CLEAN/N issues] | VERDICT: APPROVE/REJECT`

---

## Commit Strategy

| Task(s) | Commit Message | Key Files |
|---------|----------------|-----------|
| 1 | `feat(infra): scaffold monorepo with Docker Compose` | `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md` |
| 2 | `feat(infra): scaffold FastAPI backend project` | `backend/**` (pyproject.toml, main.py, config.py, etc.) |
| 3 | `feat(infra): scaffold Next.js frontend project` | `frontend/**` (package.json, next.config.js, etc.) |
| 4 | `feat(db): PostgreSQL schema design + Alembic migrations` | `backend/alembic.ini`, `backend/alembic/**` |
| 5 | `feat(skill): LLM abstraction layer via litellm` | `backend/core/llm.py`, tests |
| 6 | `feat(skill): BaseSkill interface + skill registry` | `backend/skills/base.py`, `backend/skills/registry.py`, tests |
| 7 | `feat(review): ReviewResult/ReviewIssue schemas + BaseReviewer` | `backend/review/schemas.py`, `backend/review/base.py`, tests |
| 8 | `feat(db): SQLAlchemy ORM models + migration update` | `backend/models/**`, tests |
| 9 | `feat(orchestrator): LangGraph StateGraph skeleton + checkpoint setup` | `backend/orchestrator/state.py`, `backend/orchestrator/graph.py`, `backend/orchestrator/checkpoint.py`, tests |
| 10 | `feat(api): Task Service CRUD endpoints` | `backend/services/task_service.py`, `backend/api/tasks.py`, `backend/schemas/task.py`, tests |
| 11 | `feat(api): SSE progress endpoint` | `backend/services/progress_service.py`, `backend/api/sse.py`, tests |
| 12 | `feat(skill): Document Parse Skill (DOCX, PDF, Markdown)` | `backend/skills/parse.py`, tests, fixtures |
| 13 | `feat(skill): Requirement Extraction Skill` | `backend/skills/extract_requirements.py`, tests |
| 14 | `feat(skill): Outline Planning Skill` | `backend/skills/outline.py`, tests |
| 15 | `feat(skill): Section Writing Skill` | `backend/skills/write_section.py`, tests |
| 16 | `feat(api): Document Service + upload + sections CRUD` | `backend/services/document_service.py`, `backend/api/documents.py`, `backend/schemas/document.py`, tests |
| 17 | `feat(orchestrator): generation pipeline (parse → extract → outline → write)` | `backend/orchestrator/graph.py` (updated), tests |
| 18 | `feat(orchestrator): human-in-the-loop outline approval` | `backend/services/approval_service.py`, `backend/api/tasks.py` (updated), tests |
| 19-22 | `feat(review): Structure, Compliance, Technical, Evidence reviewers` | `backend/review/structure_reviewer.py`, `backend/review/compliance_reviewer.py`, `backend/review/technical_reviewer.py`, `backend/review/evidence_reviewer.py`, tests |
| 23-26 | `feat(review): Consistency, Style, Coverage, Risk reviewers` | `backend/review/consistency_reviewer.py`, `backend/review/style_reviewer.py`, `backend/review/coverage_reviewer.py`, `backend/review/risk_reviewer.py`, tests |
| 27 | `feat(review): add review service with aggregation and API endpoints` | `backend/services/review_service.py`, `backend/models/review_aggregation.py`, `backend/api/review.py`, migration, tests |
| 28 | `feat(skills): add rewrite & polish skill for auto-revision` | `backend/skills/rewrite.py`, `backend/skills/prompts/rewrite.txt`, tests |
| 29 | `feat(orchestrator): add revision loop with review-rewrite cycle and G8 limit` | `backend/orchestrator/graph.py` (modified), tests |
| 30 | `feat(orchestrator): add final review approval gate with human-in-the-loop` | `backend/orchestrator/graph.py` (modified), `backend/models/approval.py`, `backend/api/approval.py`, tests |
| 31 | `feat(frontend): add app shell layout with sidebar, header, SSE hook, and TanStack Query` | `frontend/app/layout.tsx`, `frontend/app/providers.tsx`, `frontend/components/layout/`, `frontend/lib/api.ts`, `frontend/lib/hooks/use-sse.ts` |
| 32 | `feat(frontend): add task home page with list, creation dialog, and file upload` | `frontend/app/page.tsx`, `frontend/components/task/`, `frontend/lib/hooks/use-tasks.ts` |
| 33 | `feat(frontend): add workbench page with 3-panel layout and outline panel` | `frontend/app/tasks/[id]/page.tsx`, `frontend/components/workbench/outline-panel.tsx`, `frontend/lib/hooks/use-document.ts` |
| 34-35 | `feat(frontend): add workbench content + review panels` | `frontend/components/workbench/content-panel.tsx`, `frontend/components/workbench/section-content.tsx`, `frontend/components/workbench/generation-progress.tsx`, `frontend/components/workbench/review-panel.tsx`, `frontend/lib/hooks/use-reviews.ts` |
| 36 | `feat(frontend): add review dashboard with reviewer cards, issue table, and revision timeline` | `frontend/app/tasks/[id]/reviews/page.tsx`, `frontend/components/review/` |
| 37 | `feat(version): add version management service with diff and rollback` | `backend/services/version_service.py`, `backend/models/version.py`, `backend/api/version.py`, migration, tests |
| 38 | `feat(rag): add RAG service with pgvector for knowledge base search and management` | `backend/services/rag_service.py`, `backend/models/knowledge.py`, `backend/api/knowledge.py`, `backend/schemas/knowledge.py`, migration, tests |
| 39 | `feat(skills): add retrieval skill for RAG-enhanced content generation` | `backend/skills/retrieval.py`, `backend/skills/write_section.py` (modified), tests |
| 40 | `feat(templates): add template service with 3 built-in document templates` | `backend/services/template_service.py`, `backend/models/template.py`, `backend/api/template.py`, migration, seed data, tests |
| 41 | `feat(export): add DOCX export service with markdown-to-docx conversion` | `backend/services/export_service.py`, `backend/api/export.py`, tests |
| 42 | `feat(frontend): add version diff viewer with comparison and rollback` | `frontend/app/tasks/[id]/versions/page.tsx`, `frontend/components/version/` |
| 43 | `feat(frontend): add export page with readiness checklist and DOCX download` | `frontend/app/tasks/[id]/export/page.tsx`, `frontend/components/export/` |
| 44 | `feat(frontend): add inline review annotations with issue popovers` | `frontend/components/workbench/annotation-overlay.tsx`, `frontend/components/workbench/issue-popover.tsx`, `frontend/components/workbench/content-panel.tsx` (modified) |
| 45 | `feat(frontend): add knowledge base page with upload, search, and document management` | `frontend/app/knowledge/page.tsx`, `frontend/components/knowledge/` |
| 46 | `feat(seed): add database seed script with demo task and reference data` | `backend/scripts/seed.py`, `backend/scripts/reset_db.py`, tests |
| 47 | `feat(audit): add audit log service with cross-service integration` | `backend/services/audit_service.py`, `backend/models/audit.py`, `backend/api/audit.py`, migration, tests |
| 48 | `feat(skills): add comparison skill for requirements and reference alignment` | `backend/skills/comparison.py`, `backend/skills/prompts/comparison.txt`, `backend/api/comparison.py`, tests |
| 49 | `feat(frontend): add quality dashboard with summary cards and reviewer scorecard` | `frontend/app/tasks/[id]/quality/page.tsx`, `frontend/components/quality/` |
| 50 | `feat(docker): finalize Docker Compose with multi-stage builds and health checks` | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.env.example`, `scripts/start.sh` |
| 51 | `test(e2e): add end-to-end smoke test covering complete user journey` | `e2e/smoke.test.ts`, `e2e/playwright.config.ts`, `e2e/fixtures/test-doc.docx` |

---

## Success Criteria

### Verification Commands
```bash
# Backend tests
cd backend && pytest tests/ -v --tb=short  # Expected: ALL PASS

# Frontend tests
cd frontend && npm run test  # Expected: ALL PASS

# Frontend build
cd frontend && npm run build  # Expected: no errors

# Docker Compose
docker compose up -d  # Expected: 3 services healthy (frontend, backend, postgres)

# API smoke test
curl -s http://localhost:8000/api/v1/health | jq .  # Expected: {"status": "ok"}

# Create task
curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"name":"test","doc_type":"report"}' | jq .status  # Expected: "created"

# Full e2e (Playwright)
npx playwright test e2e/smoke.test.ts  # Expected: ALL PASS
```

### Final Checklist
- [ ] All "Must Have" present and verified
- [ ] All "Must NOT Have" (G1-G12) absent — no violations
- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] Frontend builds without type errors
- [ ] Docker Compose starts successfully
- [ ] End-to-end smoke test passes
- [ ] 8 reviewers produce structured ReviewIssue output
- [ ] Version management creates snapshots on revision
- [ ] Export produces valid DOCX file
- [ ] Human-in-the-loop interrupts work (outline approval + final review)
