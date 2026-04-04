"""API integration tests for document and section endpoints — mocked DB."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from core.database import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_section_dict(**overrides):
    """Return a section dict as returned by DocumentService.get_sections."""
    defaults = {
        "id": str(uuid.uuid4()),
        "task_id": str(uuid.uuid4()),
        "title": "Introduction",
        "level": 1,
        "description": None,
        "target_word_count": 500,
        "order_index": 0,
        "status": "draft",
        "current_content": None,
        "version_count": 0,
    }
    defaults.update(overrides)
    return defaults


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


async def _override_get_db():
    """Yield a mock async session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    yield db


@pytest.fixture(autouse=True)
def _override_db():
    """Override the DB dependency for every test in this module."""
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# GET /api/v1/tasks/{task_id}/documents
# ---------------------------------------------------------------------------


class TestListDocumentsAPI:
    @pytest.mark.asyncio
    async def test_list_documents_200(self):
        """GET /api/v1/tasks/{id}/documents returns 200 with empty list."""
        with patch("api.documents._service") as mock_svc:
            mock_svc.get_source_documents = AsyncMock(return_value=[])
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}/documents")

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/v1/tasks/{task_id}/documents/upload
# ---------------------------------------------------------------------------


class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_endpoint_201(self):
        """POST upload returns 201 with SourceDocumentResponse."""
        doc = _make_source_doc(filename="report.docx")

        with patch("api.documents._service") as mock_svc:
            mock_svc.upload_document = AsyncMock(return_value=doc)
            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{uuid.uuid4()}/documents/upload",
                    files={
                        "file": (
                            "report.docx",
                            b"fake content",
                            "application/octet-stream",
                        )
                    },
                )

        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "report.docx"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_upload_endpoint_reject_size(self):
        """POST upload returns 413 when file is too large."""
        from fastapi import HTTPException

        with patch("api.documents._service") as mock_svc:
            mock_svc.upload_document = AsyncMock(
                side_effect=HTTPException(
                    status_code=413, detail="文件过大，最大支持50MB"
                )
            )
            async with _client() as client:
                resp = await client.post(
                    f"/api/v1/tasks/{uuid.uuid4()}/documents/upload",
                    files={
                        "file": ("huge.docx", b"x" * 100, "application/octet-stream")
                    },
                )

        assert resp.status_code == 413


# ---------------------------------------------------------------------------
# GET /api/v1/tasks/{task_id}/sections
# ---------------------------------------------------------------------------


class TestListSectionsAPI:
    @pytest.mark.asyncio
    async def test_list_sections_200(self):
        """GET /api/v1/tasks/{id}/sections returns 200."""
        sections = [_make_section_dict(title="Chapter 1")]

        with patch("api.documents._service") as mock_svc:
            mock_svc.get_sections = AsyncMock(return_value=sections)
            async with _client() as client:
                resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}/sections")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Chapter 1"


# ---------------------------------------------------------------------------
# PUT /api/v1/tasks/{task_id}/sections/{section_id} — update
# ---------------------------------------------------------------------------


class TestUpdateSectionAPI:
    @pytest.mark.asyncio
    async def test_update_section_200(self):
        """PUT update section returns SectionVersionResponse."""
        version = _make_section_version(
            version_number=2,
            content="Updated text",
            word_count=2,
        )

        with patch("api.documents._service") as mock_svc:
            mock_svc.update_section_content = AsyncMock(return_value=version)
            async with _client() as client:
                resp = await client.put(
                    f"/api/v1/tasks/{uuid.uuid4()}/sections/{uuid.uuid4()}",
                    json={"content": "Updated text", "change_summary": "polish"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["version_number"] == 2
        assert data["content"] == "Updated text"
