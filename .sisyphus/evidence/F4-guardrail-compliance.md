# F4 Guardrail Compliance — G1 to G12

Scope: `D:\project\doc-agent`

> Note: Host shell is PowerShell; direct `grep` binary is unavailable in this environment (`grep: term not recognized`). Equivalent regex scans were executed with the workspace grep tool using the same patterns.

## Compliance Table

| Guardrail | Check | Evidence | Result |
|---|---|---|---|
| **G1** No document content in LangGraph state | Read `backend/orchestrator/state.py` | `DocumentState` contains IDs/flags/progress only (`task_id`, `section_ids`, `review_round`, etc.); no `content`/`body` fields | PASS |
| **G2** No direct OpenAI import | `import openai\|from openai` in `backend/**/*.py` | No matches found | PASS |
| **G3** No premature template abstraction | `TemplateFactory\|AbstractTemplate\|BaseTemplate` in `backend/**/*.py` | No matches found | PASS |
| **G4** No synchronous DB calls | sync engine/session scan | `create_engine(` no matches in backend; async evidence in `backend/core/database.py` (`create_async_engine`, `async_sessionmaker`) | PASS |
| **G5** No WebSocket | `WebSocket\|websocket` in backend/frontend code | No matches found | PASS |
| **G6** No auth/login/JWT | `@login_required\|authenticate\|JWT\|Bearer` in `backend/api/**/*.py` | No matches found | PASS |
| **G7** No zustand/redux/recoil/jotai | `zustand\|redux\|recoil\|jotai` in frontend ts/tsx | No matches found | PASS |
| **G8** Max 3 revision loops | orchestrator loop limit scan | `backend/orchestrator/graph.py:83` → `if state["review_round"] < 3:` | PASS |
| **G9** Reviewer single-turn prompt | reviewer LLM call pattern | `complete_json(` count = 8 across 8 reviewer files (1 per reviewer); `backend/review/base.py` docstring states single prompt structured output | PASS |
| **G10** No hybrid search/reranking | `rerank\|hybrid_search\|RRF` in backend | No matches found | PASS |
| **G11** No custom DOCX style/header/footer | `add_header\|add_footer\|add_style` in backend | No matches found | PASS |
| **G12** No chart libs in frontend | `recharts\|d3\.\|plotly\|chartjs\|Chart\b` in `frontend/app`, `frontend/components` | No matches found | PASS |

## Command Evidence (pattern + outcome)

1. `import openai\|from openai` → **0**
2. `TemplateFactory\|AbstractTemplate\|BaseTemplate` → **0**
3. `WebSocket\|websocket` → **0**
4. `@login_required\|authenticate\|JWT\|Bearer` → **0**
5. `zustand\|redux\|recoil\|jotai` → **0**
6. `MAX_OUTLINE_REJECTIONS\|max.*revision\|MAX.*LOOP` → no direct constant match; enforcement confirmed via `review_round"] < 3` at `backend/orchestrator/graph.py:83`
7. `rerank\|hybrid_search\|RRF` → **0**
8. `add_header\|add_footer\|add_style` → **0**
9. `recharts\|d3\.\|plotly\|chartjs\|Chart\b` → **0**

## Guardrail Summary

- Pass: **12/12**
- Fail: **0/12**
