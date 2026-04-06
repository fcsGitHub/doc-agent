import pytest
from unittest.mock import AsyncMock, MagicMock
from services.llm_config_service import LLMConfigService
from models.llm_config import LLMConfig
import uuid

@pytest.fixture
def service():
    return LLMConfigService()

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    return db

@pytest.mark.asyncio
async def test_create_config(service, mock_db):
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())
    result = await service.create(mock_db, name="Test", api_key="sk-test",
                                   api_base="https://api.openai.com/v1",
                                   default_model="gpt-4o-mini", review_model="gpt-4o",
                                   embed_model="text-embedding-3-small")
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert isinstance(result, LLMConfig)
    assert result.name == "Test"

@pytest.mark.asyncio
async def test_activate_sets_is_active(service, mock_db):
    config_id = uuid.uuid4()
    mock_config = LLMConfig(id=config_id, name="Test", api_key="k", api_base="b",
                             default_model="m", review_model="m", embed_model="e", is_active=False)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_config
    mock_db.execute.return_value = mock_result
    result = await service.activate(mock_db, str(config_id))
    assert result.is_active is True
    mock_db.commit.assert_called()

@pytest.mark.asyncio
async def test_delete_returns_false_if_not_found(service, mock_db):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    result = await service.delete(mock_db, str(uuid.uuid4()))
    assert result is False
