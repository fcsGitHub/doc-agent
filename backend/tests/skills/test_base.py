"""Tests for BaseSkill ABC and retry logic."""

import asyncio

import pytest

from skills.base import BaseSkill, RetryPolicy, SkillContext, SkillResult


class RateLimitError(Exception):
    """Retryable error for tests."""


class SuccessSkill(BaseSkill):
    name = "success_skill"
    description = "Always succeeds"

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(success=True, output={"data": "ok"})


class FailSkill(BaseSkill):
    name = "fail_skill"
    description = "Always fails"
    call_count: int = 0

    def __init__(self) -> None:
        self.call_count = 0

    async def execute(self, context: SkillContext) -> SkillResult:
        self.call_count += 1
        raise RateLimitError("rate limited")


class FlakySkill(BaseSkill):
    name = "flaky_skill"
    description = "Fails once, then succeeds"
    attempts: int = 0

    def __init__(self) -> None:
        self.attempts = 0

    async def execute(self, context: SkillContext) -> SkillResult:
        self.attempts += 1
        if self.attempts < 2:
            raise RateLimitError("rate limited")
        return SkillResult(success=True, output={"attempt": self.attempts})


@pytest.mark.asyncio
async def test_execute_success():
    """Successful skill returns SkillResult with success=True."""
    skill = SuccessSkill()
    ctx = SkillContext(task_id="test-task-id")
    result = await skill.execute(ctx)
    assert result.success is True
    assert result.output == {"data": "ok"}


@pytest.mark.asyncio
async def test_execute_with_retry_max_retries():
    """execute_with_retry exhausts retries and returns failure SkillResult."""
    skill = FailSkill()
    skill.retry_policy = RetryPolicy(max_retries=3, backoff_factor=0)
    ctx = SkillContext(task_id="test-task-id")

    # Patch asyncio.sleep to avoid actual delays
    async def no_sleep(_: float) -> None:
        return None

    original_sleep = asyncio.sleep
    asyncio.sleep = no_sleep
    try:
        result = await skill.execute_with_retry(ctx)
    finally:
        asyncio.sleep = original_sleep

    assert result.success is False
    assert result.error is not None
    assert "retries" in result.error


@pytest.mark.asyncio
async def test_execute_with_retry_succeeds_on_second():
    """execute_with_retry retries and succeeds when second attempt works."""
    skill = FlakySkill()
    skill.retry_policy = RetryPolicy(max_retries=3, backoff_factor=0)
    ctx = SkillContext(task_id="test-task-id")

    async def no_sleep(_: float) -> None:
        return None

    original_sleep = asyncio.sleep
    asyncio.sleep = no_sleep
    try:
        result = await skill.execute_with_retry(ctx)
    finally:
        asyncio.sleep = original_sleep

    assert result.success is True
    assert skill.attempts == 2
