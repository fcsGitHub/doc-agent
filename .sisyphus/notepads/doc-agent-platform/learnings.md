# Learnings — doc-agent-platform

## [2026-03-31] Session Start
- Plan file: `.sisyphus/plans/doc-agent-platform.md` (5040 lines, T1–T51 + F1–F4)
- Backend: flat layout under `backend/` — no `app/` nesting. Uvicorn target: `main:app`
- Frontend: flat layout under `frontend/` — no `src/`. App Router at `frontend/app/`
- Task document uploads accept .docx, .pdf, .md ONLY (NOT .txt)
- Knowledge base uploads accept .docx, .pdf, .md, .txt
- LangGraph state = control plane ONLY (IDs, statuses, flags). All content in PostgreSQL (G1)
- All LLM calls via litellm abstraction, no direct openai imports (G2)
- Max 3 auto-revision loops (G8)
- SSE not WebSocket (G5)
- No auth (G6)
- TanStack Query only for frontend state (G7)
- No charts in quality dashboard (G12)
- DB: `docagent` user/database, pgvector/pgvector:pg16
- QA commands run INSIDE docker containers
- python-docx (DOCX), pdfplumber (PDF), regex (Markdown) for parsing
- Wave execution: T1 first, then T2+T3+T4 in parallel (Wave 1.1)

## [2026-03-31] Task 4 — PostgreSQL Schema + Alembic Migrations
- 19 tables total: tasks, task_configs, source_documents, parsed_documents, sections, section_versions, review_results, review_issues, evidence_references, skill_executions, templates, rules, terminology_entries, knowledge_chunks, user_comments, export_artifacts, audit_events, review_rounds, approvals
- 4 enums: taskstatus (12 values), sectionstatus (5), reviewseverity (3), reviewstatus (3)
- pgvector: `vector(1536)` column on knowledge_chunks, IVFFlat index with cosine ops (lists=100)
- All UUIDs with `gen_random_uuid()`, all timestamps `TIMESTAMP WITH TIME ZONE`
- Alembic env.py uses async pattern: `async_engine_from_config` + `asyncpg` driver + `pool.NullPool`
- LSP errors on `alembic.op` and `alembic.context` are expected — runtime-injected by Alembic
- Migration file is raw SQL + SA operations (no ORM models) — ORM models come in Task 8
- 18 passing tests validate structure, enums, vector, constraints, downgrade completeness
- Evidence saved to `.sisyphus/evidence/task-4-schema-tests.txt`

## [2026-03-31] Task 3 — Next.js Frontend Scaffold
- Frontend scaffold created: Next.js 14.2.3 + App Router + TanStack Query v5
- No src/ directory — all code directly under frontend/
- Vitest + @testing-library/react for testing (NOT jest)
- next/font/google Noto_Sans_SC for Chinese font
- output: "standalone" in next.config.ts for Docker
- home.test.tsx mocks next/navigation redirect with vi.mock
- lang="zh-CN" on html element (required)
- All types in types/index.ts
- Evidence saved to `.sisyphus/evidence/task-3-frontend-build.txt`

## [2026-03-31] Task 7 — ReviewResult Schemas + BaseReviewer
- ReviewIssue severity: Literal["critical","major","minor","info"] — 4 levels (not 3)
- ReviewResult.status: Literal["pass","fail","warning"]
- ReviewAggregation.compute(): any critical=fail, any fail=fail, avg<threshold=fail, else warning/pass
- BaseReviewer.execute() extracts sections+config from SkillContext.input_data
- _build_prompt(): 2 messages [system, user] — single prompt only (G9)
- _parse_response(): gracefully handles invalid JSON — returns fail ReviewResult
- FROZEN SCHEMA: Frontend types/index.ts ReviewIssue/ReviewResult must stay in sync

## [2026-03-31] Task 6 — BaseSkill Interface + Registry
- BaseSkill is ABC with abstract execute(context) -> SkillResult
- SkillContext: task_id, section_id, input_data, llm_client (Any), db_session (Any)
- SkillResult: success, output, error, tokens_used, execution_time_ms
- execute_with_retry() checks exception TYPE NAME against retryable list (string matching)
- SkillRegistry is NOT a singleton in tests — create fresh instance per test
- Module-level get_skill_registry() for app-wide use
- RetryPolicy backoff_factor=0 in tests to skip actual delays

## [2026-03-31] Task 5 — LLM Abstraction Layer
- LLMClient wraps litellm.acompletion (async) — never import openai directly (G2)
- Retryable exceptions: litellm.RateLimitError, litellm.Timeout, litellm.ServiceUnavailableError
- complete_json() uses response_format={"type": "json_object"} + json.loads
- Module-level singleton: get_llm_client() for use in skills
- Tests mock litellm.acompletion with AsyncMock, patch asyncio.sleep to skip waits
- backend/config.py already had all LLM settings — no modifications needed
- LSP "litellm could not be resolved" is expected (Docker-only dep, like alembic.op/context)
- Evidence saved to `.sisyphus/evidence/task-5-llm-tests.txt`

## [2026-03-31] Task 8 — SQLAlchemy ORM Models
- All models use SQLAlchemy 2.0 style: Mapped[], mapped_column()
- Base class hierarchy: Base(DeclarativeBase) + UUIDMixin + TimestampMixin
- Enum columns use create_constraint=False (PostgreSQL enums already in migration)
- JSONB columns via from sqlalchemy.dialects.postgresql import JSONB
- KnowledgeChunk embedding: from pgvector.sqlalchemy import Vector; Vector(1536)
- metadata_ column name avoids Python keyword: mapped_column("metadata", JSONB, ...)
- ParsedDocument has no TimestampMixin — only created_at
- Tests are unit tests (no DB) — just instantiation checks
- __init__.py exports all models for clean imports: from models import Task, Section...
- 15 files created total: 12 model files + __init__.py + test __init__.py + test_models.py
- 6/6 tests passing

## [2026-03-31] Task 9 — LangGraph Skeleton
- `DocumentState` implemented as `TypedDict` control-plane state only (IDs + phase/flags/progress), no document content stored in graph state.
- StateGraph node names fixed to required workflow contract: parse → extract_requirements → plan_outline → await_outline_approval → generate_sections → run_reviews → check_review → revise_sections/await_final_approval → export_document.
- `check_review` routing rule codified in `route_review`: pass => final approval, fail with round < 3 => revise, fail with round >= 3 => force final human decision (G8).
- Human-in-the-loop nodes (`await_outline_approval`, `await_final_approval`) use `langgraph.types.interrupt` placeholders.
- Checkpoint config adds asyncpg-to-postgresql DSN normalization for `AsyncPostgresSaver` compatibility.
- Docker daemon unavailable in this execution environment (`dockerDesktopLinuxEngine` pipe missing), so pytest evidence includes required docker command failure and local fallback results.

## [2026-03-31] Task 10 — Task Service (CRUD API)
- FastAPI DELETE with status_code=204 CANNOT have response_model or return type annotation implying a body — use `response_class=Response` and return `Response(status_code=204)`.
- Central router pattern: `api/router.py` creates `APIRouter(prefix="/api/v1")` and includes sub-routers. `main.py` only includes the central router.
- UUID-as-string serialization: ORM Task.id is `uuid.UUID`; schemas use `str`. Convert with `str(task.id)` in helper dict builders.
- Service layer pattern: `TaskService` class with all methods accepting `db: AsyncSession` as first param, no singleton state.
- `from_attributes=True` (Pydantic v2 ConfigDict) enables `TaskResponse.model_validate(task)` from ORM objects.
- API tests: use `patch("api.tasks._service")` to mock the module-level service instance; use `app.dependency_overrides[get_db]` to inject mock DB session.
- Service tests: mock `db.execute` return values differently for count vs result queries (`scalar_one` vs `scalars().all()`).
- `db.flush()` after `db.add(task)` is needed to populate `task.id` before creating related TaskConfig.
- 19 tests total: 10 service tests + 9 API tests — all passing in 0.87s.
- Evidence saved to `.sisyphus/evidence/task-10-crud-lifecycle.txt`.

## [2026-03-31] Task 12 — Document Parse Skill (DOCX + PDF + Markdown)
- DocumentParseSkill extends BaseSkill, registered in global registry at module load
- Three parsers: _parse_docx (python-docx), _parse_pdf (pdfplumber), _parse_md (regex)
- _build_tree() uses stack-based algorithm to convert flat {title, level, content} list to nested SectionNode tree
- DOCX: para.style.name can be None — need `(para.style.name or "") if para.style else ""` guard
- PDF: pdfplumber not installed locally — use try/except import with `pdfplumber = None` fallback; mock in tests
- PDF heading heuristic: short line (<80 chars), ALL CAPS or no ending period, <=12 words
- PDF fallback: if no headings detected, wrap entire text in single SectionNode(title="全文", level=1)
- Markdown: regex `^(#{1,6})\s+(.+)$` for heading detection, line-by-line parsing
- DB persistence is optional — if context.db_session is None, skip; if save fails, don't crash skill
- ParsedDocument requires source_document_id (ForeignKey) — provide from input_data or fallback to task_id
- SectionNode is a dataclass with recursive children list; custom _section_node_to_dict() for JSON serialization
- 9 tests total: docx headings, markdown nested, empty docx, tree building (2), pdf mocked, registration, unsupported type, markdown no headings
- Docker unavailable locally — tests run with `set PYTHONPATH=. && python -m pytest` from backend/ dir
- Evidence saved to `.sisyphus/evidence/task-12-parse-{docx,md,empty}.txt`

## [2026-03-31] Task 13 — RequirementExtractionSkill
- LLM-driven skill: uses context.llm_client.complete_json() with single system+user prompt
- Chinese prompts for document analysis domain
- Graceful degradation: malformed LLM output (missing keys) returns empty but success=True
- _parse_extract_output handles all edge cases: missing keys, non-list values, invalid priority values
- Exception in execute() caught and returned as success=True with empty output (not failure)
- 5 tests: success with 3 reqs, empty doc, malformed response, registration, prompt content verification
- AsyncMock for llm_client — no real LLM calls in tests
- Evidence: task-13-extract-requirements.txt, task-13-extract-empty.txt

## [2026-03-31] Task 15 — SectionWritingSkill
- New skill file: `backend/skills/write_section.py`, registered at module load with name `section_writing`
- Free-form section generation must use `await context.llm_client.complete(...)` (NOT `complete_json()`)
- Prompt builder includes: section metadata, requirements, preceding summaries, optional style guide, and up to 3 knowledge excerpts
- Output contract stays JSON-serializable dict: `content`, `word_count`, `references_used`
- Word count uses MVP rule `len(content.split())`
- DB persistence uses best-effort `SectionVersion` insert + `flush()`; DB failures are swallowed to avoid skill failure
- Graceful degradation on LLM/other errors: return `success=True` with empty content payload and error string
- Tests added: basic generation, DB persistence, context-to-prompt inclusion, registry registration, LLM error fallback
- Evidence saved: `.sisyphus/evidence/task-15-write-section.txt`, `.sisyphus/evidence/task-15-write-context.txt`

## [2026-03-31] Task 16 — Document Service (Upload, Parsed Results, Sections CRUD)
- DocumentService class in ackend/services/document_service.py with 7 methods: upload_document, get_source_documents, get_parsed_document, get_sections, get_section, get_section_versions, update_section_content
- Upload validates extension (.docx/.pdf/.md only) and size (50MB max), saves to uploads/{task_id}/ on disk
- get_sections() returns list[dict[str, Any]] with current_content (latest version) and version_count — avoids extra ORM relationship complexity
- update_section_content() auto-increments version_number via func.max() query
- SectionVersion requires explicit id=uuid.uuid4() despite having UUIDMixin (safe because UUIDMixin provides default=uuid.uuid4 anyway)
- Schemas in ackend/schemas/document.py: SourceDocumentResponse, ParsedDocumentResponse, SectionResponse, SectionVersionResponse, SectionDetailResponse, SectionUpdateRequest
- API router in ackend/api/documents.py: prefix /tasks, 5 endpoints (upload, list docs, list sections, section detail, update section)
- Registered in ackend/api/router.py alongside tasks router
- API tests patch pi.documents._service (module-level instance) + override get_db dependency
- basedpyright: use dict[str, Any] (not dict[str, object]) for return types that get unpacked into Pydantic models — object causes reportArgumentType errors
- 10 tests total: 5 API + 5 service — all passing
- Evidence: task-16-upload-docx.txt, task-16-upload-reject-size.txt, task-16-section-update.txt

## [2026-03-31] Task 17 — LangGraph Generation Pipeline Integration
- Added `backend/orchestrator/nodes.py` to keep `graph.py` clean; node factories (`make_parse_node`, `make_extract_node`, `make_outline_node`, `make_generate_node`) inject `db` + `llm_client` through closures.
- Real nodes now execute skills via registry names: `document_parse`, `requirement_extraction`, `outline_planning`, `section_writing`.
- Each generation node publishes SSE progress through `ProgressService` with `phase_change`/`progress`/`section_complete`/`error` events.
- Each skill invocation now records `SkillExecution` rows best-effort (`db.flush()` wrapped to avoid hard-fail).
- `plan_outline_node` reads latest requirement extraction output from `skill_executions` and writes back `section_ids` from persisted `sections` table.
- `generate_sections_node` iterates sections sequentially (MVP), builds minimal `preceding_sections` context from already generated outputs, and updates progress from 40%→90%.
- `build_document_graph(db=None, llm_client=None)` is backward compatible: real async nodes only when both deps are provided; otherwise preserves old stubs so T9 graph tests continue to pass.
- Added pipeline tests at `backend/tests/orchestrator/test_pipeline.py` (6 tests, all mocked, no real DB/LLM).
- Evidence saved: `.sisyphus/evidence/task-17-pipeline-e2e.txt`, `.sisyphus/evidence/task-17-pipeline-error.txt`.

## [2026-03-31] Task 18 — Human-in-the-Loop Outline Approval Interrupt
- `ApprovalService` in `backend/services/approval_service.py`: reads rejection count from checkpoint `channel_values._rejection_count`, resumes graph with `Command(resume=True/False)`.
- `Command` imported locally inside method to avoid top-level dependency issues with `langgraph.types`.
- Graph compiled fresh each call with `build_document_graph(db=None, llm_client=None).compile(checkpointer=saver)` — no persistent compiled graph.
- `async with saver:` context required around both checkpoint read (`aget`) and graph invoke (`ainvoke`).
- Force-approval after `MAX_OUTLINE_REJECTIONS = 3` (G8): returns `approved=True` with message indicating force.
- AuditEntry records rejection details (feedback, rejection_count, force_approved flag) — best-effort write wrapped in try/except.
- SSE events published via `get_progress_service()` for both approve and reject paths.
- API endpoint `POST /{task_id}/approve-outline` validates task exists first (404 if missing), then delegates to `_approval_service.approve_outline()`.
- Schemas: `OutlineApprovalRequest(approved: bool, feedback: str | None)`, `OutlineApprovalResponse(message, task_id, approved)`.
- API test pattern: `patch("api.tasks._service")` + `patch("api.tasks._approval_service")` to mock both module-level instances.
- 15 tests total: 8 service-level (orchestrator) + 7 API-level — all passing in 1.15s.
- Docker unavailable — tests ran locally with pytest.
- Evidence saved: `.sisyphus/evidence/task-18-approve-resume.txt`, `.sisyphus/evidence/task-18-reject-replan.txt`.

## [2026-03-31] Task 27 — Review Service + Aggregation
- `AggregatedReview` added at `backend/models/review_aggregation.py` as pure Pydantic model with `from_results(...)` aggregation helper.
- Aggregation status contract implemented: any `critical` => `rejected`; else any `major` => `needs_revision`; else `approved`.
- `overall_score` normalized to float range 0.0–1.0; reviewer scores >1 are treated as 0–100 and divided by 100.
- New `ReviewService` (`backend/services/review_service.py`) runs 8 reviewers in fixed explicit order, sequentially, fail-fast on reviewer exception/failure.
- Review orchestration emits SSE events via `get_progress_service()`: `review_started`, `reviewer_1_complete` ... `reviewer_8_complete`, `review_aggregated`.
- Aggregated results persisted into `review_rounds.results` JSON and rehydrated through `get_review_round(...)` / `get_latest_review(...)`.
- New API router `backend/api/review.py` provides:
  - `POST /api/v1/tasks/{task_id}/reviews/run`
  - `GET /api/v1/tasks/{task_id}/reviews/{review_round}`
  - `GET /api/v1/tasks/{task_id}/reviews/latest`
- Route ordering matters in FastAPI: `/reviews/latest` must be declared before `/reviews/{review_round}` to avoid `422` path parsing conflict.
- `api/router.py` now includes `review_router`.
- Added tests:
  - `backend/tests/services/test_review_service.py` (5 tests)
  - `backend/tests/api/test_review_api.py` (5 tests)
- Evidence saved:
  - `.sisyphus/evidence/task-27-review-aggregation.txt`
  - `.sisyphus/evidence/task-27-critical-rejection.txt`

## [2026-03-31] Task 28 — Rewrite & Polish Skill
- RewriteSkill extends BaseSkill, registered at module load with name `rewrite_polish`
- Prompt template: `backend/skills/prompts/rewrite.txt` with SYSTEM:/USER: markers, split at import time
- Key pattern: filter issues into `auto_fixable` (requires_human=False) and human_required (requires_human=True) before building prompt
- Only auto-fixable issues reach the LLM prompt; human-required issue_ids returned in skipped_human_required list
- Uses context.llm_client.complete() (free-form text output), NOT complete_json()
- Output dict: `rewritten_content` (str), `addressed_issues` (int count), skipped_human_required (list of issue_ids)
- On LLM error: returns SkillResult(success=False, error=str(e), output={}) — differs from write_section which returns success=True
- 4 tests: basic rewrite, skip human-required issues, LLM error failure, registry registration
- Evidence: task-28-rewrite-basic.txt, task-28-skip-human.txt

## [2026-03-31] Task 29 — LangGraph Revision Loop Nodes
- Added real async revision-loop nodes in `backend/orchestrator/nodes.py`: `run_reviews_node(...)` and `revise_sections_node(...)`.
- Added factory wrappers `make_reviews_node(...)` and `make_revise_node(...)` to follow the existing dependency-injection node pattern.
- `run_reviews_node` now increments `review_round`, loads latest `ParsedDocument` by task, emits SSE `review_started`/`review_complete`, calls `ReviewService.run_all_reviews(...)`, and computes `revision_needed_section_ids` from non-human section issues.
- `revise_sections_node` now emits `revision_round_{N}_started/complete`, loads latest `ReviewRound.results`, filters auto-fixable issues per section, executes `rewrite_polish`, and writes best-effort new `SectionVersion` rows.
- `build_document_graph(...)` now wires real `run_reviews`/`revise_sections` nodes when `db` and `llm_client` are present; stubs remain in fallback mode.
- Added `backend/tests/orchestrator/test_revision_loop.py` with 5 async tests: approved, needs_revision, rejected, rewrite path persistence, and empty revision short-circuit.
- Verification: targeted revision-loop tests pass (5/5). Full suite command still stops at environment dependency (`ModuleNotFoundError: litellm` in `tests/core/test_llm.py`).

## [2026-03-31] Task 30 — Final Review Approval Gate
- Added Pydantic models in `backend/models/approval.py`: `ApprovalRequest` and `ApprovalState` with explicit literal statuses and `pending_human_issues` default_factory list.
- Implemented `FinalApprovalService` in `backend/services/final_approval_service.py`:
  - `get_approval_state(task_id, db)` reads latest aggregated review and returns `no_reviews` or `awaiting_approval` with summary and human-required issues.
  - `submit_approval(task_id, request, db)` blocks when no reviews exist (HTTP 400), emits SSE (`task_approved` / `changes_requested`), and writes `AuditEntry` best-effort.
- Added `backend/api/final_approval.py` router under `/tasks` with endpoints:
  - `GET /api/v1/tasks/{task_id}/approval`
  - `POST /api/v1/tasks/{task_id}/approval`
- Final approval API validates task existence via `TaskService` and returns 404 for unknown task IDs.
- Registered new router in `backend/api/router.py` via `final_approval_router` include.
- Added API tests in `backend/tests/orchestrator/test_final_approval.py` using established pattern (`patch("api.final_approval._service")`, dependency override for `get_db`) with 5 passing cases covering no-reviews, awaiting-approval summary, approve action, request-changes action, and 400 blocked approval.

## [2026-03-31] Task 31 — Frontend App Shell & Layout
- Root `frontend/app/layout.tsx` now uses App Shell pattern: left Sidebar + top Header + main content area, while keeping `lang="zh-CN"` and existing `QueryProvider` import path (`@/lib/query-provider`).
- New responsive sidebar component at `frontend/components/layout/sidebar.tsx` uses `usePathname()` for active-link highlighting and includes required Chinese nav labels/routes: 任务列表(`/`), 工作台(`/tasks`), 知识库(`/knowledge`).
- New header component at `frontend/components/layout/header.tsx` renders fixed platform title `文档智能平台`.
- Added shared frontend contracts in `frontend/lib/types.ts` (Task/TaskStatus, Section, ReviewIssue, ReviewResult, AggregatedReview, ApprovalState, SSEEvent) without modifying legacy `frontend/types/index.ts`.
- Added `frontend/lib/hooks/use-sse.ts` custom hook using native `EventSource` with 3s auto-reconnect, connection/error state management, event accumulation, and full unmount cleanup.
- Added `frontend/__tests__/layout.test.tsx` with Vitest + RTL checks for sidebar links, header title, and layout child rendering; test command `npm test -- --run` passes in `frontend/`.
- Build-system compatibility note: Next.js 14 in this repo rejected `next.config.ts`; switched to `next.config.mjs` with same `output: "standalone"` to restore `npm run build`.
- Type-checking note: `next build` picked up `vitest.config.ts` and hit Vite type mismatch from nested deps; excluding `vitest.config.ts` in `frontend/tsconfig.json` resolves production build checks without affecting Vitest execution.

## [2026-03-31] Task 32 — Task Home Page
- `frontend/app/page.tsx` switched from redirect to direct `<TaskList />` rendering, so home-page tests must mock task hooks instead of `redirect`.
- Added `frontend/lib/hooks/use-tasks.ts` with TanStack Query `useTasks` + `useCreateTask`; create flow posts task JSON first, then optional FormData upload to `/documents/upload` with field name `file`.
- `TaskList` uses explicit Chinese UX states (`加载中...`, `加载失败，请重试`, `暂无任务，点击'新建任务'开始`) and maps backend status values into grouped badge labels/colors for MVP readability.
- Create dialog implemented with plain HTML/Tailwind (no external UI libs), with required fields/options and file accept limited to `.docx,.pdf,.md`.
- Added `__tests__/task-list.test.tsx` (loading/empty/data cases) and updated `__tests__/home.test.tsx` to wrap page render with `QueryClientProvider`; full frontend suite now passes 7 tests.

## [2026-03-31] Task 33 — Workbench Left Panel
- TanStack Query hooks follow standard pattern with useQuery / useMutation
- Use queryClient.invalidateQueries({ queryKey: ['task', taskId] }) to trigger re-fetches after mutations
- Tests for components making multiple query calls must await waitFor for both queries to resolve before checking DOM
- When testing components using mutations, wrap action triggers (like clicks) and subsequent checks in waitFor
- CSS Grid grid-cols-[280px_1fr_320px] used for exactly sizing the three-panel layout
- App Router params params.id accessed directly in dynamic route page (app/tasks/[id]/page.tsx)
- All interaction logic uses Chinese UI text as required
- vi.mock('@/lib/api', () => ({ apiFetch: vi.fn() })) is the pattern to mock data fetching functions across custom hooks

## [2026-03-31] Task 34 — Workbench Center Panel

## [2026-04-01] Task 38 — RAG Service + pgvector Setup
- `RAGService.search()` can stay fully async while using pgvector cosine distance by combining `select(KnowledgeChunk).from_statement(text("... embedding <=> CAST(:query_embedding AS vector) ..."))`.
- Keep fixed-size chunking deterministic at 500/50 through a standalone `chunk_text()` utility so both ingestion path and unit tests share identical behavior.
- Knowledge ingestion scope accepts `.docx`, `.pdf`, `.md`, `.txt`; API validation message should explicitly include all four extensions.
- For unit tests, injecting an AsyncMock embedding client into `RAGService` avoids coupling tests to `litellm` import availability.
- Used `react-markdown` to render markdown section content with custom Tailwind styled `components` maps.
- Implemented purely CSS-based continuous `animate-pulse` progress bar for the "generating" status.
- Added `useSection` query hook with conditional `enabled: !!taskId && !!sectionId` to support "selected item" patterns without eager-fetching.
- Modified tests to reflect conditional rendering changes (e.g. placeholder updates in layout integration test).
- Ensured strict Chinese UI naming conventions across the UI layout ("待生成", "选择左侧章节查看内容").
Completed Task 36 - Review Dashboard Page successfully

## [2026-04-01] Task 39 — Retrieval Skill (RAG Integration)
- `RAGService` is imported lazily inside `execute()` body (`from services.rag_service import RAGService`), so tests CANNOT patch `skills.retrieval.RAGService`. Must patch `services.rag_service.RAGService.__init__` (return_value=None) and `services.rag_service.RAGService.search` (AsyncMock).
- `RAGService.__init__` calls `get_llm_client()` by default — patching `__init__` with `return_value=None` avoids that dependency in tests.
- `write_section.py` already had `knowledge_excerpts` support in `SectionContext` and `_build_prompt()` — retrieval integration injects `formatted_context` into this existing mechanism.
- `SkillRegistry.register()` takes a skill instance and uses `skill.name` as the key (not a separate name argument).
- `_try_retrieve_knowledge()` added as private method in WriteSectionSkill — checks db_session, checks registry for `retrieve_knowledge`, constructs query from title+description, only enriches if no existing `knowledge_excerpts`.
- All failures in retrieval silently caught — never blocks section generation (optional enhancement only).
- 6 retrieval tests + 5 existing write_section tests = 11/11 passing.
- Evidence saved: `.sisyphus/evidence/task-39-retrieval-basic.txt`.

## [2026-04-01] Task 40 — Template Service
- **CRITICAL**: ORM model `models/template.py` had column names (`outline_template`, `style_guide`, `is_default`) that didn't match the actual DB schema (`outline_structure`, `rules`, `is_active`). The migration `0001_initial_schema.py` uses `outline_structure`, `rules`, `is_active` — always verify ORM matches DB via `\d tablename` in psql.
- `BUILTIN_TEMPLATES` constant in `template_service.py` holds all 3 template definitions (投标书, 技术方案, 可行性报告).
- `seed_builtin_templates()` is called in `main.py` lifespan async context manager, wrapped in try/except for resilience.
- Template seeding is idempotent — checks by name before inserting.
- `apply_template()` creates Section rows from `outline_structure.sections` with `order_index` for ordering.
- `rules` DB column is a JSON array (default `[]`), not a dict — Pydantic schema must use `list[Any]`.
- `outline_structure` DB column is JSONB (default `[]`) but seeded data uses `{"sections": [...]}` dict format — Pydantic schema uses `dict[str, Any] | list[Any]` union type.
- basedpyright cannot resolve SQLAlchemy `Mapped` attributes — use `# pyright: ignore[reportAttributeAccessIssue]` to suppress false positives.
- No `curl` in the backend Docker image — use `urllib.request` in Python one-liners for QA.
- Evidence saved: `.sisyphus/evidence/task-40-seed-templates.txt`, `.sisyphus/evidence/task-40-apply-template.txt`.
- 10/10 unit tests passing. All 3 endpoints verified via Docker QA.
## [2026-04-01] Task 42 - Version Diff UI
- Implemented DiffViewer using conditional rendering and Tailwind styling for line-by-line diff display (green for additions, red+line-through for deletions)
- Maintained FROZEN type boundaries by keeping SectionVersion, DiffResult, and DiffHunk schemas inside the custom hook file use-versions.ts instead of the global types.ts.
- useDiff query triggers conditionally via enabled: !!versionAId && !!versionBId to prevent fetching incomplete diff comparisons.
- Designed VersionList with an intuitive chronological rollback process, confirming user intent before mutation.

## [2026-04-01] Task 41 — DOCX Export Service
- `ExportService.export_docx(db, task_id)` returns `tuple[bytes, str]` (docx_bytes, task_name) for easy response construction.
- Markdown-to-DOCX rendering uses regex-based line parser: `##` → Heading 3, `**text**` → bold run, `*text*` → italic run, `- item` → List Bullet paragraph.
- `_add_formatted_runs()` uses `re.compile(r"(\*\*(.+?)\*\*|\*(.+?)\*)")` to handle interleaved bold/italic/plain text in a single pass.
- python-docx `Document` class has poor type stubs — basedpyright reports `reportGeneralTypeIssues` on it; suppress with `# pyright: ignore[reportGeneralTypeIssues]` on import or use `Any` for function params.
- Docker test path: use `tests/services/test_export_service.py` (relative to `/app/backend`), NOT `backend/tests/...` prefix.
- API endpoint returns `Response(content=docx_bytes, media_type=DOCX_MEDIA_TYPE)` with `Content-Disposition` header for download.
- 5/5 tests passing: headings (H1/H2), latest version selection, markdown formatting (H3/bold/italic/bullet), 404 task not found, empty sections.
- Evidence saved: `.sisyphus/evidence/task-41-export-docx.txt`, `.sisyphus/evidence/task-41-markdown-format.txt`.
# 2026-04-01
- Export page can use a presentational checklist component plus direct TanStack Query data fetching in the route.
- In jsdom, spy on `HTMLAnchorElement.prototype.click` for download assertions; avoid mocking `document.createElement` unless necessary.

## [2026-04-01] Task 48 — Comparison Skill
- ComparisonSkill uses `complete_json()` (not `complete()`) for structured JSON output
- Prompt template uses `{{` and `}}` for literal braces in f-string-like .format() templates
- API endpoint pattern: lazy import `skills.comparison` module to trigger registration if not already done
- API fetches section content from latest SectionVersion via DocumentService
- 6 tests: requirements_match, reference_alignment, llm_error, prompt_content_verification, registry_registration, skill_name
- All LSP diagnostics on new files are clean (only warnings, no errors)

## [2026-04-01] Task 46 — Seed Data & Demo Flow
- Idempotent seed pattern: check-by-unique-key before every insert; safe to run from Docker entrypoint and manually.
- Built-in templates still seed through `TemplateService.seed_builtin_templates()`; demo seed adds exactly one fictional task plus 6 sections and 5 knowledge chunks.
- Demo task uses `status="approved"` + `TaskConfig.outline_approved=True` as the closest supported equivalent to outline approval.
- `KnowledgeChunk.document_id` maps to `source_document_id` in the database; seed/reference docs use valid UUIDs.
- `SectionVersion.created_at` needed a real `DateTime(timezone=True)` mapping to match the migration table shape.
- `KnowledgeChunk` in migration has `created_at` only (no `updated_at`), so the ORM must not inherit `TimestampMixin` there.
- `reset_db.py` is a dev-only utility that shells out to `alembic downgrade base` / `upgrade head` before reseeding.
- Seed verification passed inside Docker: `docker compose exec backend python -m pytest tests/scripts/test_seed.py -v`.
- Evidence saved to `.sisyphus/evidence/task-46-seed-data.txt` and `.sisyphus/evidence/task-46-seed-idempotent.txt`.


## [2026-04-01] Task 47 — Audit Log Service
- AuditEntry ORM model has vent_type column (NOT ction), and occurred_at (NOT 	imestamp). Migration has column named ction but ORM maps to vent_type — always use ORM field names in service code.
- udit_events table already exists in  001_initial_schema.py migration — no new migration needed.
- AuditService.log() maps ction param to vent_type ORM field; occurred_at stored as ISO 8601 UTC string.
- Service integration pattern: best-effort audit calls wrapped in 	ry/except Exception: pass to never break calling code.
- When adding audit calls to existing services, existing tests with strict ssert_called_once() assertions on db.add will break — need to loosen to ssert_called() or call_count >= 1.
- version_service rollback audit needed Section model import to look up 	ask_id from section_id.
- API endpoint returns {"items": [...], "limit": N, "offset": N} dict for paginated audit log.
- 5 unit tests: log creates entry, defaults empty dict, paginated retrieval, full timeline, empty result.
- Evidence saved: .sisyphus/evidence/task-47-audit-trail.txt, .sisyphus/evidence/task-47-audit-pagination.txt.

-  Task: T49 - Completed Quality Dashboard component implementation. Used existing useLatestReview hook and AggregatedReview type. Handled complex derived text stats for rounds to bypass the lack of direct round historical data inside the frontend review interface.
- 2026-04-01T04:05:18 Task: T49 - Completed Quality Dashboard page implementation in frontend without adding new chart libraries. Derived statistics using AggregatedReview hook.

## [2026-04-01] Task: T51 — Playwright Smoke Test
- Added 2e/playwright.config.ts scoped to Chromium, aseURL=http://localhost:3000, 	imeout=120000, ullyParallel=false, etries=0, reporter list.
- Added single happy-path test 2e/smoke.test.ts implementing 22-step flow across 首页/工作台/审核/导出/知识库/质量/版本页面.
- Added deterministic guard: test enforces LITELLM_MOCK=true and polls backend (http://localhost:8000) for task/section readiness during SSE-driven pipeline phases.
- Generated valid DOCX upload fixture at 2e/fixtures/test-doc.docx as an OOXML zip with minimal required entries ([Content_Types].xml, _rels/.rels, word/document.xml).
- Added 2e/package.json with @playwright/test dependency; verified test discovery from root via local CLI path and from 2e/ using --list.
