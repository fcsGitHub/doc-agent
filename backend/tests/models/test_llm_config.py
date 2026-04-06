import pytest
from models.llm_config import LLMConfig

def test_llm_config_table_name():
    assert LLMConfig.__tablename__ == "llm_configs"

def test_llm_config_fields():
    cols = {c.name for c in LLMConfig.__table__.columns}
    assert {"id", "name", "api_key", "api_base", "default_model",
            "review_model", "embed_model", "is_active", "created_at", "updated_at"} <= cols

def test_llm_config_instantiation():
    config = LLMConfig(
        name="Azure GPT-4",
        default_model="gpt-4o-mini",
        review_model="gpt-4o",
        embed_model="text-embedding-3-small",
    )
    assert config.name == "Azure GPT-4"
    assert config.default_model == "gpt-4o-mini"
