"""Skill registry for discovering and retrieving skill instances."""

from __future__ import annotations

from skills.base import BaseSkill, SkillInfo


class SkillRegistry:
    """Registry for skill instances. Supports register/get/list operations."""

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """Register a skill instance by its name."""
        if not skill.name:
            raise ValueError(f"Skill {type(skill).__name__} must have a non-empty name")
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill:
        """Retrieve a skill by name. Raises KeyError if not found."""
        if name not in self._skills:
            raise KeyError(
                f"Skill '{name}' not registered. Available: {list(self._skills)}"
            )
        return self._skills[name]

    def list_skills(self) -> list[SkillInfo]:
        """List metadata for all registered skills."""
        return [skill.get_info() for skill in self._skills.values()]

    def is_registered(self, name: str) -> bool:
        """Check if a skill is registered."""
        return name in self._skills


# Module-level singleton registry
_registry: SkillRegistry | None = None


def get_skill_registry() -> SkillRegistry:
    """Get or create the module-level skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
