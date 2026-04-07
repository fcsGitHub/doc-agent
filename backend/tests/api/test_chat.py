"""Tests for Chat API endpoints."""

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from models.chat import ChatMessage, ChatSession


@pytest.fixture
def mock_session():
    session = ChatSession()
    session.id = uuid.uuid4()
    session.task_id = uuid.uuid4()
    session.scope = "task"
    session.section_id = None
    session.review_criteria = []
    session.created_at = datetime.datetime.now()
    session.updated_at = datetime.datetime.now()
    return session


@pytest.fixture
def mock_chat_service(mock_session):
    from services.chat_service import ChatService
    svc = MagicMock(spec=ChatService)
    svc.create_session = AsyncMock(return_value=mock_session)
    svc.list_sessions = AsyncMock(return_value=[mock_session])
    svc.list_messages = AsyncMock(return_value=[])
    svc.get_session = AsyncMock(return_value=mock_session)
    return svc


@pytest.mark.asyncio
async def test_create_chat_session(mock_chat_service):
    task_id = str(uuid.uuid4())
    with patch("api.chat._service", mock_chat_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/tasks/{task_id}/chat/sessions", json={"scope": "task"}
            )
    assert resp.status_code == 201
    data = resp.json()
    assert data["scope"] == "task"


@pytest.mark.asyncio
async def test_list_chat_sessions(mock_chat_service):
    task_id = str(uuid.uuid4())
    with patch("api.chat._service", mock_chat_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/tasks/{task_id}/chat/sessions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_list_messages(mock_chat_service):
    session_id = str(uuid.uuid4())
    with patch("api.chat._service", mock_chat_service):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_session_not_found():
    from services.chat_service import ChatService
    svc = MagicMock(spec=ChatService)
    svc.get_session = AsyncMock(return_value=None)
    with patch("api.chat._service", svc):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/v1/chat/sessions/{uuid.uuid4()}/messages",
                json={"content": "Hello"},
            )
    assert resp.status_code == 404
