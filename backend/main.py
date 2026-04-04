from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import router as api_router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: seed built-in templates on startup."""
    # Seed built-in templates (idempotent)
    try:
        from core.database import async_session_maker
        from services.template_service import TemplateService

        async with async_session_maker() as db:
            svc = TemplateService()
            count = await svc.seed_builtin_templates(db)
            if count > 0:
                print(f"[seed] Inserted {count} built-in template(s).")
            else:
                print("[seed] Built-in templates already exist, skipping.")
    except Exception as exc:
        # Don't block startup if seeding fails (e.g. DB not ready yet)
        print(f"[seed] Template seeding skipped: {exc}")

    yield


app = FastAPI(title="文档智能平台 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Root health check endpoint."""
    return {"status": "ok"}


@app.get("/api/v1/health")
async def api_health():
    """API v1 health check endpoint."""
    return {"status": "ok"}


# Include versioned API router (tasks, documents, etc.)
app.include_router(api_router)
