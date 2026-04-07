"""WikiCompilerSkill — compile raw sources into wiki articles, query, and lint."""

from __future__ import annotations

import time
from typing import Any

from skills.base import BaseSkill, SkillContext, SkillResult

_COMPILE_SYSTEM = """\
You are a knowledge compiler. Given raw source documents, extract key concepts and
generate structured wiki articles in Markdown. Each article should cover one concept
or topic clearly and concisely.

Return JSON with structure:
{
  "articles": [
    {
      "title": "Concept Name",
      "category": "standards|terms|cases|general",
      "content": "## Title\\nMarkdown content...",
      "summary": "One-sentence summary under 200 chars",
      "backlinks": ["Other Article Title", ...]
    }
  ]
}

Guidelines:
- One article per distinct concept (merge related minor points)
- category must be one of: standards, terms, cases, general
- backlinks should reference other article titles found in the same compilation
- content should be self-contained Markdown (use ## for sections within the article)
"""

_QUERY_SYSTEM = """\
You are a knowledge base assistant. Answer the user's question using ONLY the
provided wiki articles. Cite which articles you used.

Return JSON:
{
  "answer": "Detailed answer in Markdown format",
  "source_article_ids": ["<article id>", ...]
}

If the answer cannot be found in the provided articles, say so clearly.
"""

_LINT_SYSTEM = """\
You are a wiki quality reviewer. Analyze the provided wiki articles and identify:
1. Contradictions between articles
2. Orphaned articles (no backlinks, isolated topics)
3. Missing or incomplete articles referenced by backlinks
4. Stale or low-quality content

Return JSON:
{
  "issues": [
    {
      "type": "contradiction|orphan|missing_reference|low_quality",
      "article_id": "<id or null>",
      "article_title": "<title>",
      "description": "Issue description",
      "suggestion": "How to fix"
    }
  ],
  "scores": {
    "<article_id>": <float 0.0-1.0>
  }
}
"""


class WikiCompilerSkill(BaseSkill):
    """Performs wiki compile, query, lint, and index operations."""

    name = "wiki_compiler"
    description = "Compile raw documents into wiki articles; query and lint the wiki"
    prerequisites: list[str] = []

    async def execute(self, context: SkillContext) -> SkillResult:
        start_ms = int(time.time() * 1000)
        operation = context.input_data.get("operation")

        dispatch = {
            "compile": self._compile,
            "query": self._query,
            "lint": self._lint,
        }

        handler = dispatch.get(operation)  # type: ignore[arg-type]
        if handler is None:
            return SkillResult(
                success=False,
                error=f"Unknown wiki operation: {operation!r}. Must be one of: {list(dispatch)}",
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

        try:
            output = await handler(context)
            return SkillResult(
                success=True,
                output=output,
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )
        except Exception as exc:
            return SkillResult(
                success=False,
                error=str(exc),
                execution_time_ms=int(time.time() * 1000) - start_ms,
            )

    async def _compile(self, context: SkillContext) -> dict[str, Any]:
        llm = context.llm_client
        if llm is None:
            raise ValueError("llm_client required for compile operation")

        sources: list[dict[str, Any]] = context.input_data.get("sources", [])
        if not sources:
            return {"articles": []}

        combined_text = "\n\n---\n\n".join(
            f"Source: {s.get('filename', 'unknown')}\n{s.get('content', '')}"
            for s in sources
        )

        messages = [
            {"role": "system", "content": _COMPILE_SYSTEM},
            {"role": "user", "content": f"Compile the following documents into wiki articles:\n\n{combined_text}"},
        ]
        result = await llm.complete_json(messages=messages)
        source_ids = [str(s.get("id", "")) for s in sources]
        for article in result.get("articles", []):
            article["source_doc_ids"] = source_ids
        return result

    async def _query(self, context: SkillContext) -> dict[str, Any]:
        llm = context.llm_client
        if llm is None:
            raise ValueError("llm_client required for query operation")

        question: str = context.input_data.get("question", "")
        articles: list[dict[str, Any]] = context.input_data.get("articles", [])

        articles_text = "\n\n---\n\n".join(
            f"[{a.get('id', '?')}] ## {a.get('title', '')}\n{a.get('content', '')}"
            for a in articles
        )

        messages = [
            {"role": "system", "content": _QUERY_SYSTEM},
            {"role": "user", "content": f"Wiki articles:\n{articles_text}\n\nQuestion: {question}"},
        ]
        return await llm.complete_json(messages=messages)

    async def _lint(self, context: SkillContext) -> dict[str, Any]:
        llm = context.llm_client
        if llm is None:
            raise ValueError("llm_client required for lint operation")

        articles: list[dict[str, Any]] = context.input_data.get("articles", [])
        if not articles:
            return {"issues": [], "scores": {}}

        articles_text = "\n\n---\n\n".join(
            f"[{a.get('id', '?')}] {a.get('title', '')}\nCategory: {a.get('category', '')}\n"
            f"Summary: {a.get('summary', '')}\nBacklinks: {a.get('backlinks', [])}"
            for a in articles
        )

        messages = [
            {"role": "system", "content": _LINT_SYSTEM},
            {"role": "user", "content": f"Review these wiki articles:\n{articles_text}"},
        ]
        return await llm.complete_json(messages=messages)


from skills.registry import get_skill_registry  # noqa: E402
get_skill_registry().register(WikiCompilerSkill())
