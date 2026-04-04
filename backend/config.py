from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "postgresql+asyncpg://docagent:docagent@localhost:5432/docagent"
    llm_api_key: str = ""
    llm_api_base: str = "https://api.openai.com/v1"
    llm_default_model: str = "gpt-4o-mini"
    llm_review_model: str = "gpt-4o"
    llm_embed_model: str = "text-embedding-3-small"
    litellm_mock: bool = False
    seed_demo_data: bool = True
    backend_cors_origins: List[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
