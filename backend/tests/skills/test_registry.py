"""Tests for SkillRegistry."""

import pytest

from skills.base import BaseSkill, SkillContext, SkillResult
from skills.registry import SkillRegistry


class MockSkill(BaseSkill):
    """Minimal skill for testing."""

    name = "mock_skill"
    description = "A mock skill for testing"

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output={"result": "mock"})


class AnotherMockSkill(BaseSkill):
    name = "another_skill"
    description = "Another mock skill"

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output={"other": True})


def test_register_and_get_skill():
    """Skills can be registered and retrieved by name."""
    registry = SkillRegistry()
    skill = MockSkill()
    registry.register(skill)
    retrieved = registry.get("mock_skill")
    assert retrieved is skill
    assert retrieved.name == "mock_skill"


def test_list_skills_returns_all():
    """list_skills() returns info for all registered skills."""
    registry = SkillRegistry()
    registry.register(MockSkill())
    registry.register(AnotherMockSkill())
    skills = registry.list_skills()
    names = [s.name for s in skills]
    assert "mock_skill" in names
    assert "another_skill" in names
    assert len(skills) == 2


def test_get_unknown_skill_raises():
    """get() raises KeyError for unregistered skill."""
    registry = SkillRegistry()
    with pytest.raises(KeyError, match="unknown_skill"):
        registry.get("unknown_skill")


def test_register_skill_without_name_raises():
    """register() raises ValueError if skill has no name."""

    class NamelessSkill(BaseSkill):
        name = ""
        description = "No name"

        async def execute(self, context: SkillContext) -> SkillResult:
            return SkillResult(success=True)

    registry = SkillRegistry()
    with pytest.raises(ValueError, match="non-empty name"):
        registry.register(NamelessSkill())


def test_is_registered():
    """is_registered() correctly reports registration status."""
    registry = SkillRegistry()
    registry.register(MockSkill())
    assert registry.is_registered("mock_skill")
    assert not registry.is_registered("nonexistent")
