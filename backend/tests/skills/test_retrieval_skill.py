"""Tests for RetrievalSkill — RAG knowledge base search."""
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skills.base import SkillContext
from skills.retrieval import RetrievalSkill


@pytest.fixture
def skill() -> RetrievalSkill:
    """Fresh RetrievalSkill instance."""
    return RetrievalSkill()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock async DB session."""
    return AsyncMock()


def _make_chunk(content: str, chunk_index: int) -> MagicMock:
    """Create a mock KnowledgeChunk with content and chunk_index attributes."""
    chunk = MagicMock()
    chunk.content = content
    chunk.chunk_index = chunk_index
    return chunk


@pytest.mark.asyncio
async def test_retrieval_basic_with_results(
    skill: RetrievalSkill,
    mock_db: AsyncMock,
) -> None:
    """RAG search returns chunks; output contains chunks list and formatted_context."""
    mock_chunks = [
        _make_chunk("知识片段一：关于项目管理的最佳实践。", 0),
        _make_chunk("知识片段二：敏捷开发流程概述。", 1),
        _make_chunk("知识片段三：文档撰写规范与标准。", 2),
    ]

    with (
        patch("services.rag_service.RAGService.__init__", return_value=None),
        patch(
            "services.rag_service.RAGService.search",
            new_callable=AsyncMock,
            return_value=mock_chunks,
        ) as mock_search,
    ):
        ctx = SkillContext(
            task_id="task-39",
            section_id="sec-001",
            input_data={"query": "项目管理方法论", "top_k": 3},
            db_session=mock_db,
        )

        result = await skill.execute(ctx)

    assert result.success is True
    assert len(result.output["chunks"]) == 3
    assert (
        result.output["chunks"][0]["content"] == "知识片段一：关于项目管理的最佳实践。"
    )
    assert result.output["chunks"][0]["chunk_index"] == 0
    assert result.output["chunks"][2]["chunk_index"] == 2

    # formatted_context is a numbered list
    formatted = result.output["formatted_context"]
    assert "1. 知识片段一" in formatted
    assert "2. 知识片段二" in formatted
    assert "3. 知识片段三" in formatted

    # Verify RAGService.search was called correctly
    mock_search.assert_called_once_with(db=mock_db, query="项目管理方法论", top_k=3)


@pytest.mark.asyncio
async def test_retrieval_empty_knowledge_base(
    skill: RetrievalSkill,
    mock_db: AsyncMock,
) -> None:
    """Empty knowledge base returns success with empty chunks and fallback message."""
    with (
        patch("services.rag_service.RAGService.__init__", return_value=None),
        patch(
            "services.rag_service.RAGService.search",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        ctx = SkillContext(
            task_id="task-39",
            section_id="sec-002",
            input_data={"query": "不存在的主题"},
            db_session=mock_db,
        )

        result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["chunks"] == []
    assert result.output["formatted_context"] == "暂无相关知识库内容"
    assert result.error is None


@pytest.mark.asyncio
async def test_retrieval_no_db_session(skill: RetrievalSkill) -> None:
    """No db_session returns success with empty results (graceful degradation)."""
    ctx = SkillContext(
        task_id="task-39",
        section_id="sec-003",
        input_data={"query": "任意查询"},
        db_session=None,
    )

    result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["chunks"] == []
    assert result.output["formatted_context"] == "暂无相关知识库内容"
    assert result.error is None


@pytest.mark.asyncio
async def test_retrieval_rag_exception_graceful(
    skill: RetrievalSkill,
    mock_db: AsyncMock,
) -> None:
    """RAGService exception is caught; returns success with empty results."""
    with (
        patch("services.rag_service.RAGService.__init__", return_value=None),
        patch(
            "services.rag_service.RAGService.search",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Embedding service down"),
        ),
    ):
        ctx = SkillContext(
            task_id="task-39",
            section_id="sec-004",
            input_data={"query": "测试异常"},
            db_session=mock_db,
        )

        result = await skill.execute(ctx)

    assert result.success is True
    assert result.output["chunks"] == []
    assert result.output["formatted_context"] == "暂无相关知识库内容"
    assert "Embedding service down" in (result.error or "")


def test_registered_in_registry() -> None:
    """RetrievalSkill is registered in global registry as 'retrieve_knowledge'."""
    from skills.registry import get_skill_registry

    registry = get_skill_registry()
    assert registry.is_registered("retrieve_knowledge")
    registered = registry.get("retrieve_knowledge")
    assert isinstance(registered, RetrievalSkill)


@pytest.mark.asyncio
async def test_retrieval_default_top_k(
    skill: RetrievalSkill,
    mock_db: AsyncMock,
) -> None:
    """top_k defaults to 5 when not provided in input_data."""
    mock_chunks = [_make_chunk(f"chunk-{i}", i) for i in range(5)]

    with (
        patch("services.rag_service.RAGService.__init__", return_value=None),
        patch(
            "services.rag_service.RAGService.search",
            new_callable=AsyncMock,
            return_value=mock_chunks,
        ) as mock_search,
    ):
        ctx = SkillContext(
            task_id="task-39",
            input_data={"query": "默认top_k测试"},
            db_session=mock_db,
        )

        result = await skill.execute(ctx)

    assert result.success is True
    assert len(result.output["chunks"]) == 5
    # Verify default top_k=5 was passed
    mock_search.assert_called_once_with(db=mock_db, query="默认top_k测试", top_k=5)
