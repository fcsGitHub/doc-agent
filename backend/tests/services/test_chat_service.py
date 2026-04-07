"""Tests for ChatService."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.chat_service import ChatService


@pytest.fixture
def service():
    return ChatService()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_session(service, mock_db):
    task_id = str(uuid.uuid4())
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())
    session = await service.create_session(mock_db, task_id=task_id, scope="task")
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert session.task_id == uuid.UUID(task_id)
    assert session.scope == "task"


@pytest.mark.asyncio
async def test_add_message(service, mock_db):
    session_id = str(uuid.uuid4())
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", uuid.uuid4())
    msg = await service.add_message(
        mock_db, session_id=session_id, role="user", content="Hello"
    )
    mock_db.add.assert_called_once()
    assert msg.content == "Hello"
    assert msg.role == "user"


@pytest.mark.asyncio
async def test_create_section_session(service, mock_db):
    task_id = str(uuid.uuid4())
    section_id = str(uuid.uuid4())
    mock_db.refresh.side_effect = lambda obj: None
    session = await service.create_session(
        mock_db, task_id=task_id, scope="section", section_id=section_id
    )
    assert session.scope == "section"
    assert session.section_id == uuid.UUID(section_id)
