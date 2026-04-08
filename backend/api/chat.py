"""FastAPI router for chat session management and message handling."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.llm import get_llm_client
from models.section import Section
from schemas.chat import (
    ChatMessageResponse,
    ChatMessageSend,
    ChatSessionCreate,
    ChatSessionResponse,
)
from services.chat_service import ChatService
from skills.chat import INTENT_EDIT, INTENT_STANDARD, ChatSkill

router = APIRouter(tags=["chat"])
_service = ChatService()
_skill = ChatSkill()


def _session_to_response(s: object) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=str(getattr(s, "id")),
        task_id=str(getattr(s, "task_id")),
        scope=str(getattr(s, "scope")),
        section_id=str(getattr(s, "section_id")) if getattr(s, "section_id") else None,
        review_criteria=list(getattr(s, "review_criteria") or []),
        created_at=getattr(s, "created_at"),
    )


def _msg_to_response(m: object) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=str(getattr(m, "id")),
        session_id=str(getattr(m, "session_id")),
        role=str(getattr(m, "role")),
        content=str(getattr(m, "content")),
        action=getattr(m, "action"),
        created_at=getattr(m, "created_at"),
    )


@router.post("/tasks/{task_id}/chat/sessions", status_code=201, response_model=ChatSessionResponse)
async def create_session(
    task_id: str,
    body: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    session = await _service.create_session(
        db, task_id=task_id, scope=body.scope, section_id=body.section_id
    )
    return _session_to_response(session)


@router.get("/tasks/{task_id}/chat/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    task_id: str, db: AsyncSession = Depends(get_db)
) -> list[ChatSessionResponse]:
    sessions = await _service.list_sessions(db, task_id)
    return [_session_to_response(s) for s in sessions]


@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    session_id: str, db: AsyncSession = Depends(get_db)
) -> list[ChatMessageResponse]:
    msgs = await _service.list_messages(db, session_id)
    return [_msg_to_response(m) for m in msgs]


@router.post("/chat/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    body: ChatMessageSend,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Send a chat message and stream the assistant reply via SSE."""
    session = await _service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await _service.add_message(db, session_id=session_id, role="user", content=body.content)

    history_msgs = await _service.list_messages(db, session_id)
    history = [{"role": m.role, "content": m.content} for m in history_msgs[:-1]]

    sections_result = await db.execute(
        select(Section).where(Section.task_id == session.task_id).order_by(Section.order_index)
    )
    sections = [
        {"id": str(s.id), "title": s.title, "content": s.content or ""}
        for s in sections_result.scalars().all()
    ]

    llm_client = get_llm_client()

    async def event_stream() -> AsyncGenerator[str, None]:
        from skills.base import SkillContext
        context = SkillContext(
            task_id=str(session.task_id),
            input_data={
                "session_id": session_id,
                "user_message": body.content,
                "history": history,
                "sections": sections,
            },
            llm_client=llm_client,
            db_session=db,
        )
        result = await _skill.execute(context)

        if not result.success:
            yield f"data: {json.dumps({'error': result.error})}\n\n"
            return

        intent = result.output.get("intent")
        reply = result.output.get("reply", "")

        if intent == INTENT_STANDARD:
            label = result.output.get("standard_label", "")
            description = result.output.get("standard_description", "")
            if label and description:
                await _service.append_review_criterion(db, session_id, label, description)

        action: dict[str, Any] | None = None
        if intent == INTENT_EDIT:
            section_id = result.output.get("section_id")
            rewrite_instruction = result.output.get("rewrite_instruction")
            if section_id and rewrite_instruction:
                action = {
                    "type": "edit",
                    "section_id": section_id,
                    "instruction": rewrite_instruction,
                    "status": "pending_confirmation",
                }

        await _service.add_message(
            db, session_id=session_id, role="assistant", content=reply, action=action
        )

        yield f"data: {json.dumps({'reply': reply, 'intent': intent, 'action': action})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
