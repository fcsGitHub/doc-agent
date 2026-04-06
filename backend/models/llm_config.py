"""LLMConfig ORM model — persists LLM provider configurations."""
from __future__ import annotations
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base, TimestampMixin, UUIDMixin

class LLMConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "llm_configs"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    api_base: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    default_model: Mapped[str] = mapped_column(String(200), nullable=False)
    review_model: Mapped[str] = mapped_column(String(200), nullable=False)
    embed_model: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
