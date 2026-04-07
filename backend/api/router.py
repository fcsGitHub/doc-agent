"""Central API router that aggregates all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from api.audit import router as audit_router
from api.comparison import router as comparison_router
from api.documents import router as documents_router
from api.export import router as export_router
from api.final_approval import router as final_approval_router
from api.knowledge import router as knowledge_router  # pyright: ignore[reportMissingImports]
from api.review import router as review_router
from api.sse import router as sse_router
from api.tasks import router as tasks_router
from api.template import router as template_router
from api.chat import router as chat_router
from api.wiki import router as wiki_router
from api.settings import router as settings_router
from api.version import router as version_router

router = APIRouter(prefix="/api/v1")

router.include_router(tasks_router)
router.include_router(documents_router)
router.include_router(review_router)
router.include_router(final_approval_router, tags=["Final Approval"])
router.include_router(sse_router)
router.include_router(knowledge_router)
router.include_router(template_router)
router.include_router(version_router)
router.include_router(export_router)
router.include_router(audit_router)
router.include_router(comparison_router)
router.include_router(chat_router)
router.include_router(wiki_router)
router.include_router(settings_router)
