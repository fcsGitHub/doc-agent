"""BaseSkill ABC and supporting models for the skill system."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class RetryPolicy(BaseModel):
    """Retry configuration for skill execution."""

    max_retries: int = 3
    backoff_factor: float = 2.0
    retryable_exceptions: list[str] = [
        "RateLimitError",
        "Timeout",
        "ServiceUnavailableError",
    ]


class SkillContext(BaseModel):
    """Input context passed to every skill execution."""

    model_config = {"arbitrary_types_allowed": True}

    task_id: str
    section_id: str | None = None
    input_data: dict[str, Any] = {}
    # llm_client and db_session passed as Any to avoid circular imports
    llm_client: Any = None
    db_session: Any = None


class SkillResult(BaseModel):
    """Output from a skill execution."""

    success: bool
    output: dict[str, Any] = {}
    error: str | None = None
    tokens_used: int = 0
    execution_time_ms: int = 0


class SkillInfo(BaseModel):
    """Metadata about a registered skill."""

    name: str
    description: str
    prerequisites: list[str] = []


class BaseSkill(ABC):
    """Abstract base class for all skills. All 9+ skills implement this interface."""

    name: str = ""
    description: str = ""
    prerequisites: list[str] = []
    retry_policy: RetryPolicy = RetryPolicy()

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill. Must be implemented by all concrete skills."""
        ...

    async def validate_output(self, result: SkillResult) -> bool:
        """Validate the skill's output. Override for custom validation."""
        return result.success

    async def execute_with_retry(self, context: SkillContext) -> SkillResult:
        """Execute with retry logic based on retry_policy."""
        last_exc: Exception | None = None
        start_ms = int(time.time() * 1000)

        for attempt in range(self.retry_policy.max_retries):
            try:
                result = await self.execute(context)
                result.execution_time_ms = int(time.time() * 1000) - start_ms
                return result
            except Exception as exc:  # pragma: no cover - exercised by tests
                # Only retry if exception name is in retryable list
                if type(exc).__name__ in self.retry_policy.retryable_exceptions:
                    last_exc = exc
                    if attempt < self.retry_policy.max_retries - 1:
                        wait = self.retry_policy.backoff_factor**attempt
                        await asyncio.sleep(wait)
                else:
                    # Non-retryable — wrap and return failure
                    return SkillResult(
                        success=False,
                        error=str(exc),
                        execution_time_ms=int(time.time() * 1000) - start_ms,
                    )

        return SkillResult(
            success=False,
            error=f"Skill failed after {self.retry_policy.max_retries} retries: {last_exc}",
            execution_time_ms=int(time.time() * 1000) - start_ms,
        )

    def get_info(self) -> SkillInfo:
        """Return metadata about this skill."""
        return SkillInfo(
            name=self.name,
            description=self.description,
            prerequisites=self.prerequisites,
        )
