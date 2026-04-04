"""Unit tests for TemplateService — mocked async DB session."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.template_service import BUILTIN_TEMPLATES, TemplateService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_template(**overrides: Any) -> MagicMock:
    """Return a mock DocumentTemplate ORM object with sensible defaults."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "name": "投标书",
        "doc_type": "投标书",
        "description": "标准投标书模板",
        "outline_structure": {
            "sections": [
                {"title": "公司概况", "level": 1},
                {"title": "项目理解", "level": 1},
            ]
        },
        "rules": [],
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    template = MagicMock(**defaults)
    for k, v in defaults.items():
        setattr(template, k, v)
    return template


def _make_task(**overrides: Any) -> MagicMock:
    """Return a mock Task ORM object."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "name": "Test Task",
        "doc_type": "report",
        "status": "created",
    }
    defaults.update(overrides)
    task = MagicMock(**defaults)
    for k, v in defaults.items():
        setattr(task, k, v)
    return task


def _mock_db() -> AsyncMock:
    """Create a fully mocked AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


def _scalar_result(value: Any) -> MagicMock:
    """Mock db.execute() result with scalar_one_or_none returning value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list[Any]) -> MagicMock:
    """Mock db.execute() result with scalars().all() returning values."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetTemplates:
    """Tests for get_templates (list all / filter by doc_type)."""

    @pytest.mark.asyncio
    async def test_list_all_templates(self) -> None:
        """get_templates with no filter returns all templates."""
        db = _mock_db()
        t1 = _make_template(name="投标书")
        t2 = _make_template(name="技术方案", doc_type="技术方案")
        t3 = _make_template(name="可行性报告", doc_type="可行性报告")
        db.execute.return_value = _scalars_result([t1, t2, t3])

        svc = TemplateService()
        result = await svc.get_templates(db)

        assert len(result) == 3
        db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_templates_by_doc_type(self) -> None:
        """get_templates with doc_type filter returns only matching templates."""
        db = _mock_db()
        t1 = _make_template(name="投标书", doc_type="投标书")
        db.execute.return_value = _scalars_result([t1])

        svc = TemplateService()
        result = await svc.get_templates(db, doc_type="投标书")

        assert len(result) == 1
        assert result[0].name == "投标书"


class TestGetTemplate:
    """Tests for get_template (single by ID)."""

    @pytest.mark.asyncio
    async def test_get_existing_template(self) -> None:
        """get_template returns a template when found."""
        db = _mock_db()
        tid = uuid.uuid4()
        tpl = _make_template(id=tid, name="技术方案")
        db.execute.return_value = _scalar_result(tpl)

        svc = TemplateService()
        result = await svc.get_template(db, str(tid))

        assert result is not None
        assert result.name == "技术方案"

    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self) -> None:
        """get_template returns None when not found."""
        db = _mock_db()
        db.execute.return_value = _scalar_result(None)

        svc = TemplateService()
        result = await svc.get_template(db, str(uuid.uuid4()))

        assert result is None


class TestApplyTemplate:
    """Tests for apply_template (creates Section rows)."""

    @pytest.mark.asyncio
    async def test_apply_template_creates_sections(self) -> None:
        """apply_template creates one Section per outline_structure section."""
        db = _mock_db()
        task_id = uuid.uuid4()
        template_id = uuid.uuid4()

        task_mock = _make_task(id=task_id)
        template_mock = _make_template(
            id=template_id,
            outline_structure={
                "sections": [
                    {"title": "公司概况", "level": 1},
                    {"title": "项目理解", "level": 1},
                    {"title": "技术方案", "level": 1},
                ]
            },
        )

        # First call: task lookup. Second call: template lookup.
        db.execute.side_effect = [
            _scalar_result(task_mock),
            _scalar_result(template_mock),
        ]

        svc = TemplateService()
        sections = await svc.apply_template(db, str(task_id), str(template_id))

        assert len(sections) == 3
        # Verify db.add was called 3 times (once per section)
        assert db.add.call_count == 3
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_apply_template_task_not_found(self) -> None:
        """apply_template raises 404 when task doesn't exist."""
        db = _mock_db()
        db.execute.return_value = _scalar_result(None)

        svc = TemplateService()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await svc.apply_template(db, str(uuid.uuid4()), str(uuid.uuid4()))

        assert exc_info.value.status_code == 404
        assert "Task not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_apply_template_template_not_found(self) -> None:
        """apply_template raises 404 when template doesn't exist."""
        db = _mock_db()
        task_mock = _make_task()

        # First call: task found. Second call: template not found.
        db.execute.side_effect = [
            _scalar_result(task_mock),
            _scalar_result(None),
        ]

        svc = TemplateService()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await svc.apply_template(db, str(uuid.uuid4()), str(uuid.uuid4()))

        assert exc_info.value.status_code == 404
        assert "Template not found" in str(exc_info.value.detail)


class TestSeedBuiltinTemplates:
    """Tests for seed_builtin_templates (idempotent insert)."""

    @pytest.mark.asyncio
    async def test_seed_inserts_when_empty(self) -> None:
        """seed_builtin_templates inserts all 3 templates when DB is empty."""
        db = _mock_db()
        # All 3 check-before-insert calls return None (not found)
        db.execute.side_effect = [
            _scalar_result(None),
            _scalar_result(None),
            _scalar_result(None),
        ]

        svc = TemplateService()
        count = await svc.seed_builtin_templates(db)

        assert count == 3
        assert db.add.call_count == 3
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_seed_skips_when_already_exists(self) -> None:
        """seed_builtin_templates inserts nothing when all templates exist."""
        db = _mock_db()
        # All 3 check-before-insert calls find existing templates
        db.execute.side_effect = [
            _scalar_result(_make_template(name="投标书")),
            _scalar_result(_make_template(name="技术方案")),
            _scalar_result(_make_template(name="可行性报告")),
        ]

        svc = TemplateService()
        count = await svc.seed_builtin_templates(db)

        assert count == 0
        assert db.add.call_count == 0

    def test_builtin_templates_data(self) -> None:
        """BUILTIN_TEMPLATES contains exactly 3 templates with expected names."""
        assert len(BUILTIN_TEMPLATES) == 3
        names = {t["name"] for t in BUILTIN_TEMPLATES}
        assert names == {"投标书", "技术方案", "可行性报告"}

        # Each template has sections in outline_structure
        for tpl in BUILTIN_TEMPLATES:
            sections = tpl["outline_structure"]["sections"]
            assert len(sections) >= 4
            for sec in sections:
                assert "title" in sec
                assert "level" in sec
