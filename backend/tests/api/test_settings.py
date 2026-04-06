import pytest, uuid, datetime
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from models.llm_config import LLMConfig

def _make_config(**kwargs):
    c = LLMConfig()
    c.id = uuid.uuid4()
    c.name = kwargs.get("name", "Test")
    c.api_key = kwargs.get("api_key", "sk-testkey1234")
    c.api_base = kwargs.get("api_base", "https://api.openai.com/v1")
    c.default_model = kwargs.get("default_model", "gpt-4o-mini")
    c.review_model = kwargs.get("review_model", "gpt-4o")
    c.embed_model = kwargs.get("embed_model", "text-embedding-3-small")
    c.is_active = kwargs.get("is_active", False)
    c.created_at = datetime.datetime.now()
    c.updated_at = datetime.datetime.now()
    return c

@pytest.fixture
def mock_service():
    from services.llm_config_service import LLMConfigService
    svc = MagicMock(spec=LLMConfigService)
    svc.list_all = AsyncMock(return_value=[])
    svc.create = AsyncMock(return_value=_make_config())
    svc.activate = AsyncMock(return_value=_make_config(is_active=True))
    svc.delete = AsyncMock(return_value=True)
    return svc

@pytest.mark.asyncio
async def test_list_configs_empty(mock_service):
    with patch("api.settings._service", mock_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/settings/llm")
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_create_config(mock_service):
    with patch("api.settings._service", mock_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/v1/settings/llm", json={
                "name": "Test", "api_key": "sk-testkey1234",
                "api_base": "https://api.openai.com/v1",
                "default_model": "gpt-4o-mini", "review_model": "gpt-4o",
                "embed_model": "text-embedding-3-small",
            })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test"
    assert "api_key" not in data  # key must NOT be in response
    assert "api_key_masked" in data

@pytest.mark.asyncio
async def test_activate_config(mock_service):
    config_id = str(uuid.uuid4())
    with patch("api.settings._service", mock_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(f"/api/v1/settings/llm/{config_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

@pytest.mark.asyncio
async def test_delete_config_not_found(mock_service):
    mock_service.delete = AsyncMock(return_value=False)
    config_id = str(uuid.uuid4())
    with patch("api.settings._service", mock_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.delete(f"/api/v1/settings/llm/{config_id}")
    assert resp.status_code == 404
