# Issues — doc-agent-platform

## [2026-03-31] Known Gotchas
- Windows host (win32/pwsh) but Docker containers are Linux — all QA commands run inside containers
- pgvector requires special postgres image: `pgvector/pgvector:pg16`
- Frontend has NO `src/` directory — files go directly under `frontend/`
- Backend has NO `app/` directory — files go directly under `backend/`
- .txt files are FORBIDDEN for task document uploads but ALLOWED for knowledge base uploads
- SEED_DEMO_DATA env var controls whether demo task is seeded (default: true)

## [2026-03-31] Task 17 Notes
- basedpyright is strict in this repo; new orchestration/node integration files may need local `# pyright:` suppression directives for async DI patterns, Any-typed LLM clients, and mocked test objects.

## [2026-04-01] Task 38 Notes
- Local host test environment may not have `litellm` installed; avoid eager `core.llm` imports in service modules under unit test by lazy-resolving `get_llm_client()` only when no mock client is injected.
# 2026-04-01
- `URL.createObjectURL` is not available in the test environment by default; stub it explicitly when verifying blob downloads.
