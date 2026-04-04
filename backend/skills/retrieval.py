"""Retrieval Skill — RAG knowledge base search for document generation context."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportImplicitOverride=false, reportUnannotatedClassAttribute=false

from __future__ import annotations

import time

from skills.base import BaseSkill, SkillContext, SkillResult


class RetrievalSkill(BaseSkill):
    """Search the knowledge base via RAG and return relevant chunks as context."""

    name = "retrieve_knowledge"
    description = "Retrieve relevant knowledge chunks from the RAG knowledge base"

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute knowledge retrieval against the vector store.

        Input (from context.input_data):
            query (str): Search query text.
            top_k (int, optional): Number of results to return. Defaults to 5.

        Returns:
            SkillResult with output containing:
                chunks: list of dicts with 'content' and 'chunk_index'
                formatted_context: numbered string of excerpts or fallback message
        """
        start = time.time()
        try:
            data = context.input_data or {}
            query: str = str(data.get("query", ""))
            top_k: int = int(data.get("top_k", 5))

            # Graceful degradation: no db_session means no vector search possible
            if context.db_session is None:
                return SkillResult(
                    success=True,
                    output={
                        "chunks": [],
                        "formatted_context": "暂无相关知识库内容",
                    },
                    execution_time_ms=int((time.time() - start) * 1000),
                )

            # Instantiate RAGService and perform search
            from services.rag_service import RAGService

            rag_service = RAGService()
            results = await rag_service.search(
                db=context.db_session, query=query, top_k=top_k
            )

            # Empty knowledge base — return success with informative message
            if not results:
                return SkillResult(
                    success=True,
                    output={
                        "chunks": [],
                        "formatted_context": "暂无相关知识库内容",
                    },
                    execution_time_ms=int((time.time() - start) * 1000),
                )

            # Build output from search results
            chunks = [
                {"content": chunk.content, "chunk_index": chunk.chunk_index}
                for chunk in results
            ]
            formatted_lines = [
                f"{idx}. {chunk.content}" for idx, chunk in enumerate(results, 1)
            ]
            formatted_context = "\n".join(formatted_lines)

            return SkillResult(
                success=True,
                output={
                    "chunks": chunks,
                    "formatted_context": formatted_context,
                },
                execution_time_ms=int((time.time() - start) * 1000),
            )

        except Exception as exc:
            # Graceful degradation: retrieval failure should not crash callers
            return SkillResult(
                success=True,
                output={
                    "chunks": [],
                    "formatted_context": "暂无相关知识库内容",
                },
                error=str(exc),
                execution_time_ms=int((time.time() - start) * 1000),
            )


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------
from skills.registry import get_skill_registry  # noqa: E402

get_skill_registry().register(RetrievalSkill())
