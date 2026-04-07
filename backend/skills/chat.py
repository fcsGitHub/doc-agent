"""ChatSkill — resolves user chat messages into document actions or standard specs."""

from __future__ import annotations

import time
from typing import Any

from skills.base import BaseSkill, SkillContext, SkillResult

INTENT_EDIT = "edit"
INTENT_STANDARD = "standard"
INTENT_QUERY = "query"

_SYSTEM_PROMPT = """\
You are an AI assistant helping a user manage a document generation task.
You have access to the document sections listed below.

Your job: analyze the user's message and return JSON with:
{
  "intent": "edit" | "standard" | "query",
  "reply": "<friendly reply to show the user>",
  "section_id": "<section id if editing a specific section, else null>",
  "rewrite_instruction": "<instruction for the rewrite skill if intent=edit, else null>",
  "standard_label": "<short label if intent=standard, e.g. 'ISO 9001', else null>",
  "standard_description": "<full description of the standard if intent=standard, else null>"
}

Intent meanings:
- edit: user wants to modify one or more document sections
- standard: user is specifying a review standard or criterion to follow
- query: user is asking a question (answer in 'reply', no document changes)
"""


class ChatSkill(BaseSkill):
    """Resolves chat intent and returns structured action for the API layer to execute."""

    name = "chat"
    description = "Resolve user chat message into document action or standard specification"
    prerequisites: list[str] = []

    async def execute(self, context: SkillContext) -> SkillResult:
        start_ms = int(time.time() * 1000)
        llm = context.llm_client
        if llm is None:
            return SkillResult(
                success=False,
                error="llm_client is required for ChatSkill",
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

        user_message: str = context.input_data.get("user_message", "")
        history: list[dict[str, str]] = context.input_data.get("history", [])
        sections: list[dict[str, Any]] = context.input_data.get("sections", [])

        sections_text = "\n".join(
            f"- [{s.get('id', '?')}] {s.get('title', '')}: {str(s.get('content', ''))[:200]}"
            for s in sections
        )

        messages = [{"role": "system", "content": _SYSTEM_PROMPT + f"\n\nDocument sections:\n{sections_text}"}]
        for h in history[-10:]:  # last 10 messages for context
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            result = await llm.complete_json(messages=messages)
        except Exception as exc:
            return SkillResult(
                success=False,
                error=str(exc),
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

        return SkillResult(
            success=True,
            output=result,
            execution_time_ms=int(time.time() * 1000) - start_ms,
        )


from skills.registry import get_skill_registry  # noqa: E402
get_skill_registry().register(ChatSkill())
