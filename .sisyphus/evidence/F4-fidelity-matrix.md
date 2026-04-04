# F4 Fidelity Matrix — Document Intelligence Platform

Plan reference: `.sisyphus/plans/doc-agent-platform.md` (Must Have + concrete deliverables)

## Deliverable Spot Check

| Category | Expected | Evidence | Status |
|---|---:|---|---|
| Backend skills (key files) | 7+ key skills | `backend/skills/parse.py`, `extract_requirements.py`, `outline.py`, `write_section.py`, `rewrite.py`, `retrieval.py`, `comparison.py` all present | FOUND |
| Backend concrete skill classes | 7+ | `class \w+Skill(BaseSkill)` count = **7** across `backend/skills/*.py` | FOUND |
| Reviewers | 8 | `structure_reviewer.py`, `compliance_reviewer.py`, `technical_reviewer.py`, `evidence_reviewer.py`, `consistency_reviewer.py`, `style_reviewer.py`, `coverage_reviewer.py`, `risk_reviewer.py` all present | FOUND |
| Frontend pages (required list) | 6+ | `frontend/app/page.tsx`, `frontend/app/tasks/[id]/page.tsx`, `frontend/app/tasks/[id]/reviews/page.tsx`, `frontend/app/tasks/[id]/versions/page.tsx`, `frontend/app/tasks/[id]/export/page.tsx`, `frontend/app/tasks/[id]/quality/page.tsx`, `frontend/app/knowledge/page.tsx` all present | FOUND |
| E2E smoke flow | 22 steps | `e2e/smoke.test.ts` `test.step("\d+")` count = **22** | FOUND |
| Docker compose services | 3 | `docker-compose.yml` has service keys: `postgres`, `backend`, `frontend` (count = **3**) | FOUND |

## File-by-File Checks

### Backend Skills (required key files)
- FOUND — `backend/skills/parse.py`
- FOUND — `backend/skills/extract_requirements.py`
- FOUND — `backend/skills/outline.py`
- FOUND — `backend/skills/write_section.py`
- FOUND — `backend/skills/rewrite.py`
- FOUND — `backend/skills/retrieval.py`
- FOUND — `backend/skills/comparison.py`

### Reviewers (required key files)
- FOUND — `backend/review/structure_reviewer.py`
- FOUND — `backend/review/compliance_reviewer.py`
- FOUND — `backend/review/technical_reviewer.py`
- FOUND — `backend/review/evidence_reviewer.py`
- FOUND — `backend/review/consistency_reviewer.py`
- FOUND — `backend/review/style_reviewer.py`
- FOUND — `backend/review/coverage_reviewer.py`
- FOUND — `backend/review/risk_reviewer.py`

### Frontend Pages (required key files)
- FOUND — `frontend/app/page.tsx`
- FOUND — `frontend/app/tasks/[id]/page.tsx`
- FOUND — `frontend/app/tasks/[id]/reviews/page.tsx`
- FOUND — `frontend/app/tasks/[id]/versions/page.tsx`
- FOUND — `frontend/app/tasks/[id]/export/page.tsx`
- FOUND — `frontend/app/tasks/[id]/quality/page.tsx`
- FOUND — `frontend/app/knowledge/page.tsx`

## Fidelity Summary

- Deliverables checked: **24**
- Compliant: **24**
- Missing: **0**
