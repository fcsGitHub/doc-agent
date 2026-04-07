"""Tests for ChatSession and ChatMessage ORM models."""

import pytest
from models.chat import ChatSession, ChatMessage


def test_chat_session_table():
    assert ChatSession.__tablename__ == "chat_sessions"
    cols = {c.name for c in ChatSession.__table__.columns}
    assert {"id", "task_id", "scope", "section_id", "review_criteria", "created_at"} <= cols


def test_chat_message_table():
    assert ChatMessage.__tablename__ == "chat_messages"
    cols = {c.name for c in ChatMessage.__table__.columns}
    assert {"id", "session_id", "role", "content", "action", "created_at"} <= cols


def test_chat_session_instantiation():
    import uuid
    session = ChatSession(
        task_id=uuid.uuid4(),
        scope="task",
        section_id=None,
        review_criteria=[],
    )
    assert session.scope == "task"
    assert session.review_criteria == []


def test_chat_message_instantiation():
    import uuid
    msg = ChatMessage(
        session_id=uuid.uuid4(),
        role="user",
        content="Hello",
        action=None,
    )
    assert msg.role == "user"
    assert msg.content == "Hello"
