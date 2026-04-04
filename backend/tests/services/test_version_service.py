"""Unit tests for VersionService — create, list, diff, rollback."""
# pyright: reportAny=false, reportExplicitAny=false, reportUnusedCallResult=false

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.version_service import VersionService


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_version(
    section_id: uuid.UUID,
    version_number: int,
    content: str,
    version_id: uuid.UUID | None = None,
    change_source: str = "generation",
    change_summary: str | None = None,
) -> MagicMock:
    """Create a mock SectionVersion object."""
    v = MagicMock()
    v.id = version_id or uuid.uuid4()
    v.section_id = section_id
    v.version_number = version_number
    v.content = content
    v.word_count = len(content.split())
    v.change_source = change_source
    v.change_summary = change_summary
    v.created_at = None
    return v


class TestVersionService:
    @pytest.mark.asyncio
    async def test_create_version_increments_number(self) -> None:
        """create_version should set version_number = max(existing) + 1."""
        service = VersionService()
        db = _mock_db()
        section_id = str(uuid.uuid4())

        # Mock: max version_number is 3
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = 3
        db.execute.return_value = scalar_mock

        # Capture the SectionVersion object passed to db.add
        added_objects: list[MagicMock] = []
        db.add = lambda obj: added_objects.append(obj)

        result = await service.create_version(
            db=db,
            section_id=section_id,
            content="Hello world test content",
            source="generation",
            summary="Test version",
        )

        # db.refresh is called with the version object
        assert db.commit.await_count == 1
        assert db.refresh.await_count == 1

        # Check the object passed to db.add
        assert len(added_objects) == 1
        created = added_objects[0]
        assert created.version_number == 4
        assert created.word_count == 4
        assert created.change_source == "generation"
        assert created.change_summary == "Test version"

    @pytest.mark.asyncio
    async def test_create_version_starts_at_one(self) -> None:
        """First version for a section should be version_number 1."""
        service = VersionService()
        db = _mock_db()
        section_id = str(uuid.uuid4())

        # Mock: no existing versions (max returns None)
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = scalar_mock

        added_objects: list[MagicMock] = []
        db.add = lambda obj: added_objects.append(obj)

        await service.create_version(
            db=db,
            section_id=section_id,
            content="First version",
            source="generation",
        )

        assert len(added_objects) == 1
        assert added_objects[0].version_number == 1

    @pytest.mark.asyncio
    async def test_get_versions_ordered(self) -> None:
        """get_versions should return versions ordered by version_number ASC."""
        service = VersionService()
        db = _mock_db()
        section_id = uuid.uuid4()

        v1 = _make_version(section_id, 1, "First")
        v2 = _make_version(section_id, 2, "Second")
        v3 = _make_version(section_id, 3, "Third")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [v1, v2, v3]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        versions = await service.get_versions(db, str(section_id))

        assert len(versions) == 3
        assert versions[0].version_number == 1
        assert versions[1].version_number == 2
        assert versions[2].version_number == 3

    @pytest.mark.asyncio
    async def test_get_diff_shows_additions_and_deletions(self) -> None:
        """get_diff should correctly detect additions and deletions."""
        service = VersionService()
        db = _mock_db()
        section_id = uuid.uuid4()

        va_id = uuid.uuid4()
        vb_id = uuid.uuid4()

        va = _make_version(section_id, 1, "Hello world\nLine two\n", version_id=va_id)
        vb = _make_version(
            section_id,
            2,
            "Hello world\nLine two modified\nLine three\n",
            version_id=vb_id,
        )

        # get_version is called twice (once per version_id)
        async def mock_get_version(
            db_session: AsyncMock, version_id: str
        ) -> MagicMock | None:
            if version_id == str(va_id):
                return va
            if version_id == str(vb_id):
                return vb
            return None

        with patch.object(service, "get_version", side_effect=mock_get_version):
            diff = await service.get_diff(db, str(va_id), str(vb_id))

        assert diff["additions"] > 0
        assert diff["deletions"] > 0
        assert isinstance(diff["hunks"], list)
        assert len(diff["hunks"]) > 0

        # Verify hunk structure
        hunk = diff["hunks"][0]
        assert "old_start" in hunk
        assert "new_start" in hunk
        assert "lines" in hunk

        # Check line types
        line_types = {line["type"] for line in hunk["lines"]}
        assert "added" in line_types or "removed" in line_types

    @pytest.mark.asyncio
    async def test_get_diff_version_not_found(self) -> None:
        """get_diff should raise 404 if version not found."""
        service = VersionService()
        db = _mock_db()

        async def mock_get_version(db_session: AsyncMock, version_id: str) -> None:
            return None

        with patch.object(service, "get_version", side_effect=mock_get_version):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await service.get_diff(db, str(uuid.uuid4()), str(uuid.uuid4()))
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rollback_creates_new_version(self) -> None:
        """rollback_section should create a NEW version (not delete existing)."""
        service = VersionService()
        db = _mock_db()
        section_id = uuid.uuid4()
        target_id = uuid.uuid4()

        target = _make_version(
            section_id, 2, "Target content here", version_id=target_id
        )

        # Mock get_version to return target
        async def mock_get_version(
            db_session: AsyncMock, version_id: str
        ) -> MagicMock | None:
            if version_id == str(target_id):
                return target
            return None

        # Mock create_version to track the call
        created_version = _make_version(
            section_id,
            5,
            "Target content here",
            change_source="manual",
            change_summary="回滚到版本 2",
        )

        with (
            patch.object(service, "get_version", side_effect=mock_get_version),
            patch.object(
                service, "create_version", AsyncMock(return_value=created_version)
            ) as mock_create,
        ):
            result = await service.rollback_section(db, str(section_id), str(target_id))

        # Verify create_version was called with correct params
        mock_create.assert_awaited_once_with(
            db=db,
            section_id=str(section_id),
            content="Target content here",
            source="manual",
            summary="回滚到版本 2",
        )
        assert result.change_source == "manual"

    @pytest.mark.asyncio
    async def test_rollback_content_matches_target(self) -> None:
        """Rollback version content must exactly match target version content."""
        service = VersionService()
        db = _mock_db()
        section_id = uuid.uuid4()
        target_id = uuid.uuid4()

        target_content = "This is the exact target content\nwith multiple lines"
        target = _make_version(section_id, 1, target_content, version_id=target_id)

        async def mock_get_version(
            db_session: AsyncMock, version_id: str
        ) -> MagicMock | None:
            if version_id == str(target_id):
                return target
            return None

        # Let create_version pass through to verify content
        rollback_version = _make_version(
            section_id,
            4,
            target_content,
            change_source="manual",
            change_summary="回滚到版本 1",
        )

        with (
            patch.object(service, "get_version", side_effect=mock_get_version),
            patch.object(
                service, "create_version", AsyncMock(return_value=rollback_version)
            ) as mock_create,
        ):
            result = await service.rollback_section(db, str(section_id), str(target_id))

        # Verify create_version received the exact target content
        call_kwargs = mock_create.await_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs["content"] == target_content
        assert result.content == target_content

    @pytest.mark.asyncio
    async def test_rollback_wrong_section_raises_400(self) -> None:
        """rollback_section should raise 400 if target belongs to different section."""
        service = VersionService()
        db = _mock_db()
        section_id = uuid.uuid4()
        other_section_id = uuid.uuid4()
        target_id = uuid.uuid4()

        # Target belongs to a different section
        target = _make_version(other_section_id, 1, "Content", version_id=target_id)

        async def mock_get_version(
            db_session: AsyncMock, version_id: str
        ) -> MagicMock | None:
            if version_id == str(target_id):
                return target
            return None

        with patch.object(service, "get_version", side_effect=mock_get_version):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await service.rollback_section(db, str(section_id), str(target_id))
            assert exc_info.value.status_code == 400
