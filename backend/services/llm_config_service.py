"""Service for managing LLM provider configurations."""
from __future__ import annotations
import uuid
from typing import Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from core.llm import update_active_config
from models.llm_config import LLMConfig

class LLMConfigService:
    async def list_all(self, db: AsyncSession) -> Sequence[LLMConfig]:
        result = await db.execute(select(LLMConfig).order_by(LLMConfig.created_at.desc()))
        return result.scalars().all()

    async def get(self, db: AsyncSession, config_id: str) -> LLMConfig | None:
        result = await db.execute(select(LLMConfig).where(LLMConfig.id == uuid.UUID(config_id)))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, name: str, api_key: str = "",
                     api_base: str = "https://api.openai.com/v1",
                     default_model: str = "gpt-4o-mini", review_model: str = "gpt-4o",
                     embed_model: str = "text-embedding-3-small") -> LLMConfig:
        config = LLMConfig(name=name, api_key=api_key, api_base=api_base,
                           default_model=default_model, review_model=review_model,
                           embed_model=embed_model, is_active=False)
        db.add(config)
        await db.commit()
        await db.refresh(config)
        return config

    async def update(self, db: AsyncSession, config_id: str, **fields: str | None) -> LLMConfig | None:
        config = await self.get(db, config_id)
        if config is None:
            return None
        for key, value in fields.items():
            if value is not None:
                setattr(config, key, value)
        await db.commit()
        await db.refresh(config)
        if config.is_active:
            update_active_config({"api_key": config.api_key, "api_base": config.api_base,
                                   "default_model": config.default_model,
                                   "review_model": config.review_model,
                                   "embed_model": config.embed_model})
        return config

    async def delete(self, db: AsyncSession, config_id: str) -> bool:
        config = await self.get(db, config_id)
        if config is None:
            return False
        await db.delete(config)
        await db.commit()
        return True

    async def activate(self, db: AsyncSession, config_id: str) -> LLMConfig | None:
        config = await self.get(db, config_id)
        if config is None:
            return None
        await db.execute(update(LLMConfig).values(is_active=False))
        config.is_active = True
        await db.commit()
        await db.refresh(config)
        update_active_config({"api_key": config.api_key, "api_base": config.api_base,
                               "default_model": config.default_model,
                               "review_model": config.review_model,
                               "embed_model": config.embed_model})
        return config
