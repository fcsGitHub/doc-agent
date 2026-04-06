import pytest
from models.llm_config import LLMConfig

def test_llm_config_table_name():
    assert LLMConfig.__tablename__ == "llm_configs"

def test_llm_config_fields():
    cols = {c.name for c in LLMConfig.__table__.columns}
    assert {"id", "name", "api_key", "api_base", "default_model",
            "review_model", "embed_model", "is_active", "created_at", "updated_at"} <= cols
