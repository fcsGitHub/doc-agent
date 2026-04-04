# F3 — API Smoke Test Evidence

**Date**: 2026-04-01
**Reviewer**: Sisyphus-Junior (F3 QA Agent)

## Container Status

| Container | Image | Status | Ports |
|-----------|-------|--------|-------|
| docagent-backend | doc-agent-backend | Up 4h (unhealthy*) | 0.0.0.0:8000->8000/tcp |
| docagent-postgres | pgvector/pgvector:pg16 | Up 4h (healthy) | 0.0.0.0:5432->5432/tcp |
| docagent-frontend | — | Not running | — |

*Note: Backend shows "unhealthy" because Docker healthcheck uses `curl` which is not installed in the slim Python image. The backend IS responding correctly to HTTP requests.

## Health Endpoint

- **URL**: `GET http://localhost:8000/health`
- **Status**: 200 OK
- **Response**: `{"status":"ok"}`
- **Result**: PASS

## Core API Endpoints

| # | Endpoint | Method | Status | Response | Result |
|---|----------|--------|--------|----------|--------|
| 1 | `/health` | GET | 200 | `{"status":"ok"}` | PASS |
| 2 | `/api/v1/tasks` | GET | 200 | `{"tasks":[], "total":0, "skip":0, "limit":20}` | PASS |
| 3 | `/api/v1/templates` | GET | 200 | JSON with template data (投标书 template found) | PASS |
| 4 | `/api/v1/knowledge/documents` | GET | 200 | `[]` (empty, no docs ingested) | PASS |
| 5 | `/api/v1/knowledge/stats` | GET | 200 | `{"total_documents":0, "total_chunks":0, "last_updated":null}` | PASS |

**Note**: `/api/v1/knowledge` (bare path) returns 404. The actual knowledge endpoints are at `/api/v1/knowledge/documents`, `/api/v1/knowledge/search`, `/api/v1/knowledge/stats`, `/api/v1/knowledge/ingest`. This is correct per the OpenAPI spec.

## OpenAPI Spec — All Registered Routes (30 total)

```
/api/v1/health
/api/v1/knowledge/documents
/api/v1/knowledge/documents/{document_id}
/api/v1/knowledge/ingest
/api/v1/knowledge/search
/api/v1/knowledge/stats
/api/v1/sections/{section_id}/rollback
/api/v1/sections/{section_id}/versions
/api/v1/sections/{section_id}/versions/{version_id}/diff
/api/v1/tasks
/api/v1/tasks/{task_id}
/api/v1/tasks/{task_id}/apply-template
/api/v1/tasks/{task_id}/approval
/api/v1/tasks/{task_id}/approve-outline
/api/v1/tasks/{task_id}/audit
/api/v1/tasks/{task_id}/documents
/api/v1/tasks/{task_id}/documents/upload
/api/v1/tasks/{task_id}/export/docx
/api/v1/tasks/{task_id}/progress
/api/v1/tasks/{task_id}/reviews/latest
/api/v1/tasks/{task_id}/reviews/run
/api/v1/tasks/{task_id}/reviews/{review_round}
/api/v1/tasks/{task_id}/sections
/api/v1/tasks/{task_id}/sections/{section_id}
/api/v1/tasks/{task_id}/sections/{section_id}/compare
/api/v1/tasks/{task_id}/start
/api/v1/tasks/{task_id}/status
/api/v1/templates
/api/v1/templates/{template_id}
/health
```

## Summary

- **API Health**: PASS
- **Core APIs**: 5/5 responding (health + tasks + templates + knowledge/documents + knowledge/stats)
- **Total registered routes**: 30
- **Backend unhealthy flag**: Cosmetic issue (curl not in container), not functional
