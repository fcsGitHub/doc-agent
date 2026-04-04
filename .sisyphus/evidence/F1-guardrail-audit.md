# F1 Guardrail Audit (G1-G12)

Date: 2026-04-01

## Method
- Followed required checks from task brief.
- Environment note: host shell lacks GNU `grep`; equivalent searches were executed using repository grep/read tooling and PowerShell regex filtering where needed.

## Results

1. **G1 — No content in LangGraph state**: ✅ PASS
   - File: `backend/orchestrator/state.py`
   - `DocumentState` contains IDs/status/flags/progress only (`task_id`, `section_ids`, approval flags, phase, progress, error).
   - No full document content fields.

2. **G2 — No direct OpenAI imports**: ✅ PASS
   - Pattern: `from openai|import openai`
   - Scope: `backend/**/*.py`
   - Result: no matches.

3. **G3 — No premature template abstraction**: ✅ PASS
   - Pattern: `TemplateFactory|AbstractTemplate|BaseTemplate`
   - Scope: `backend/**/*.py`
   - Result: no matches.

4. **G4 — No synchronous DB calls**: ✅ PASS
   - Check pattern equivalent: `^def.*db|session.execute|session.query` excluding `async def`.
   - Findings:
     - `def ... (db: AsyncSession, ...)` factory/helper signatures in orchestrator (not sync DB usage).
     - DB execution found as `await session.execute(...)` (`backend/scripts/seed.py`).
     - No `session.query` found.

5. **G5 — No WebSocket**: ✅ PASS
   - Pattern: `websocket|WebSocket`
   - Scope: backend + frontend (`*.py`, `*.ts`, `*.tsx`)
   - Result: no matches.

6. **G6 — No auth logic**: ✅ PASS
   - Pattern: `authenticate|authorization|@login_required|JWT|password`
   - Scope: `backend/api/**/*.py`
   - Result: no matches.

7. **G7 — No forbidden frontend state libs**: ✅ PASS
   - Pattern: `zustand|redux|jotai|recoil`
   - Scope: `frontend/**/*.{ts,tsx}`
   - Result: no matches.

8. **G8 — Revision limit <= 3**: ✅ PASS
   - File: `backend/orchestrator/graph.py`
   - Evidence: review routing logic uses `if state["review_round"] < 3: return "revise_sections"`, else exits revision loop.
   - `backend/orchestrator/state.py` also documents max 3 in comment.

9. **G9 — Single-prompt reviewers**: ✅ PASS
   - Spot-check file: `backend/review/style_reviewer.py`
   - Evidence: one prompt build + single `await self.llm_client.complete_json(messages=messages)` per review call.
   - `backend/review/base.py` comments also enforce single-pass parse/no multi-turn.

10. **G10 — No hybrid search/reranking**: ✅ PASS
    - Pattern: `rerank|hybrid_search|RRF`
    - Scope: `backend/**/*.py`
    - Result: no matches.

11. **G11 — No custom DOCX styles/headers/footers**: ✅ PASS
    - Pattern: `add_header|add_footer|add_style|custom_style`
    - Scope: `backend/**/*.py`
    - Result: no matches.

12. **G12 — No chart library in frontend quality dashboard**: ✅ PASS
    - Pattern: `recharts|d3|plotly|Chart|canvas` (non-test frontend files)
    - Scope: `frontend/**/*.{ts,tsx}`
    - Result: no matches.

## Summary

- Guardrails passed: **12/12**
- Guardrail violations detected: **0**
