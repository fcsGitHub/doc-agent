# Decisions — doc-agent-platform

## [2026-03-31] Architectural Decisions
- Single Document Orchestrator, no agent zoo
- MVP-first: real runnable system, no over-engineering
- LangGraph for orchestration state machine (control plane only)
- PostgreSQL + pgvector for all content + embeddings
- Alembic for migrations
- litellm for all LLM calls
- sse-starlette for SSE endpoints
- TanStack Query (no Zustand/Redux/etc)
- python-docx for DOCX export (basic headings + paragraphs only)
- Fixed-size chunks for RAG (500 chars, 50 overlap)

## [2026-04-01] Task 38 Decisions
- Added `LLMClient.embed(texts)` in `core/llm.py` as the single embedding entrypoint, preserving G2 (all model calls through litellm wrapper).
- Implemented MVP retrieval strictly as pgvector cosine similarity (`<=>`) with no hybrid keyword layer and no reranking (G10).
- Knowledge API extraction implemented inline in `api/knowledge.py` for `.docx/.pdf/.md/.txt` to keep Task 38 self-contained and avoid adding new migration/model dependencies.
# 2026-04-01
- Kept export UI logic in the page: task query via `useQuery`, checklist rendering in a dedicated component, and download behavior in the page handler.
