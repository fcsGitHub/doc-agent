"""Unit tests for DocumentService — mocked async DB session."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from services.document_service import DocumentService, MAX_FILE_SIZE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_db() -> AsyncMock:
    """Create a fully mocked AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_upload_file(
    filename: str = "test.docx",
    content: bytes = b"fake docx content",
) -> UploadFile:
    """Create a mock UploadFile."""
    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.read = AsyncMock(return_value=content)
    return file


def _make_source_doc(**overrides):
    """Return a mock SourceDocument ORM object."""
    defaults = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "filename": "test.docx",
        "file_type": "docx",
        "file_path": "uploads/test-task/test.docx",
        "file_size": 1024,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    doc = MagicMock(**defaults)
    for k, v in defaults.items():
        setattr(doc, k, v)
    return doc


def _make_section(**overrides):
    """Return a mock Section ORM object."""
    defaults = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "parent_id": None,
        "title": "Introduction",
        "level": 1,
        "description": None,
        "target_word_count": 500,
        "order_index": 0,
        "status": "draft",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    sec = MagicMock(**defaults)
    for k, v in defaults.items():
        setattr(sec, k, v)
    return sec


def _make_section_version(**overrides):
    """Return a mock SectionVersion ORM object."""
    defaults = {
        "id": uuid.uuid4(),
        "section_id": uuid.uuid4(),
        "version_number": 1,
        "content": "Some content",
        "word_count": 2,
        "change_source": "manual",
        "change_summary": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    ver = MagicMock(**defaults)
    for k, v in defaults.items():
        setattr(ver, k, v)
    return ver


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUploadDocument:
    @pytest.mark.asyncio
    async def test_upload_document_success(self):
        """upload_document saves file and creates SourceDocument record."""
        db = _mock_db()
        service = DocumentService()
        task_id = str(uuid.uuid4())
        file = _make_upload_file(filename="report.docx", content=b"x" * 100)

        created_doc = _make_source_doc(filename="report.docx", file_type="docx")

        async def fake_refresh(obj):
            for attr in (
                "id",
                "task_id",
                "filename",
                "file_type",
                "file_path",
                "file_size",
                "created_at",
                "updated_at",
            ):
                setattr(obj, attr, getattr(created_doc, attr))

        db.refresh.side_effect = fake_refresh

        with (
            patch("services.document_service.open", create=True) as mock_open,
            patch("services.document_service.os.makedirs"),
        ):
            mock_open.return_value.__enter__ = MagicMock()
            mock_open.return_value.__exit__ = MagicMock(return_value=False)
            result = await service.upload_document(db, task_id, file)

        db.add.assert_called()
        assert db.add.call_count >= 1  # doc + optional audit entry
        db.commit.assert_awaited()
        assert result.filename == "report.docx"

    @pytest.mark.asyncio
    async def test_upload_document_too_large(self):
        """upload_document rejects files exceeding 50MB."""
        db = _mock_db()
        service = DocumentService()
        task_id = str(uuid.uuid4())
        # 60MB content
        large_content = b"x" * (60 * 1024 * 1024)
        file = _make_upload_file(filename="huge.docx", content=large_content)

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(db, task_id, file)

        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_upload_document_invalid_type(self):
        """upload_document rejects unsupported file types."""
        db = _mock_db()
        service = DocumentService()
        task_id = str(uuid.uuid4())
        file = _make_upload_file(filename="malware.exe", content=b"evil")

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_document(db, task_id, file)

        assert exc_info.value.status_code == 400


class TestGetSections:
    @pytest.mark.asyncio
    async def test_get_sections_empty(self):
        """get_sections returns empty list when no sections exist."""
        db = _mock_db()
        service = DocumentService()

        # Mock: sections query returns empty
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        db.execute.return_value = mock_result

        result = await service.get_sections(db, str(uuid.uuid4()))
        assert result == []


class TestUpdateSectionContent:
    @pytest.mark.asyncio
    async def test_update_section_content_creates_version(self):
        """update_section_content creates new SectionVersion with correct version_number."""
        db = _mock_db()
        service = DocumentService()

        section = _make_section()
        section_id = str(section.id)

        # First execute: get_section query
        mock_section_result = MagicMock()
        mock_section_result.scalar_one_or_none.return_value = section

        # Second execute: max version_number query — returns 1 (existing version)
        mock_max_result = MagicMock()
        mock_max_result.scalar_one_or_none.return_value = 1

        db.execute.side_effect = [mock_section_result, mock_max_result]

        created_version = _make_section_version(
            section_id=section.id,
            version_number=2,
            content="Updated content here",
            word_count=3,
        )

        async def fake_refresh(obj):
            for attr in (
                "id",
                "section_id",
                "version_number",
                "content",
                "word_count",
                "change_source",
                "change_summary",
                "created_at",
            ):
                setattr(obj, attr, getattr(created_version, attr))

        db.refresh.side_effect = fake_refresh

        result = await service.update_section_content(
            db, section_id, "Updated content here", "Fixed typos"
        )

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        assert result.version_number == 2
        assert result.content == "Updated content here"
