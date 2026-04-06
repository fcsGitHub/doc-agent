"""FastAPI router for LLM configuration management."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from schemas.llm_config import LLMConfigCreate, LLMConfigResponse, LLMConfigUpdate
from services.llm_config_service import LLMConfigService

router = APIRouter(prefix="/settings", tags=["settings"])
_service = LLMConfigService()


def _to_response(config: object) -> LLMConfigResponse:
    api_key = str(getattr(config, "api_key", "") or "")
    masked = f"...{api_key[-4:]}" if len(api_key) >= 4 else "****"
    return LLMConfigResponse(
        id=str(getattr(config, "id")),
        name=str(getattr(config, "name")),
        api_key_masked=masked,
        api_base=str(getattr(config, "api_base")),
        default_model=str(getattr(config, "default_model")),
        review_model=str(getattr(config, "review_model")),
        embed_model=str(getattr(config, "embed_model")),
        is_active=bool(getattr(config, "is_active")),
        created_at=getattr(config, "created_at"),
        updated_at=getattr(config, "updated_at"),
    )


@router.get("/llm", response_model=list[LLMConfigResponse])
async def list_configs(db: AsyncSession = Depends(get_db)) -> list[LLMConfigResponse]:
    configs = await _service.list_all(db)
    return [_to_response(c) for c in configs]


@router.post("/llm", status_code=201, response_model=LLMConfigResponse)
async def create_config(body: LLMConfigCreate, db: AsyncSession = Depends(get_db)) -> LLMConfigResponse:
    config = await _service.create(db, name=body.name, api_key=body.api_key,
                                    api_base=body.api_base, default_model=body.default_model,
                                    review_model=body.review_model, embed_model=body.embed_model)
    return _to_response(config)


@router.put("/llm/{config_id}", response_model=LLMConfigResponse)
async def update_config(config_id: str, body: LLMConfigUpdate,
                        db: AsyncSession = Depends(get_db)) -> LLMConfigResponse:
    config = await _service.update(db, config_id, name=body.name, api_key=body.api_key,
                                    api_base=body.api_base, default_model=body.default_model,
                                    review_model=body.review_model, embed_model=body.embed_model)
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    return _to_response(config)


@router.delete("/llm/{config_id}", status_code=204)
async def delete_config(config_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    deleted = await _service.delete(db, config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    return Response(status_code=204)


@router.post("/llm/{config_id}/activate", response_model=LLMConfigResponse)
async def activate_config(config_id: str, db: AsyncSession = Depends(get_db)) -> LLMConfigResponse:
    config = await _service.activate(db, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    return _to_response(config)
