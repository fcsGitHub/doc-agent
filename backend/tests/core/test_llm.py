"""Tests for LLM abstraction layer."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.llm import LLMClient, LLMResponse


def _make_litellm_response(content: str, total_tokens: int = 100) -> MagicMock:
    """Build a mock litellm response object."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock()
    response.usage.total_tokens = total_tokens
    return response


@pytest.mark.asyncio
async def test_complete_returns_llm_response():
    """complete() returns LLMResponse with content and token count."""
    mock_response = _make_litellm_response("Hello from LLM")

    with patch(
        "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
    ):
        with patch("litellm.completion_cost", return_value=0.001):
            client = LLMClient(default_model="gpt-4o-mini", api_key="test-key")
            result = await client.complete(messages=[{"role": "user", "content": "Hi"}])

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello from LLM"
    assert result.tokens_used == 100
    assert result.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_complete_json_parses_json():
    """complete_json() parses valid JSON content from LLM."""
    payload = {"key": "value", "number": 42}
    mock_response = _make_litellm_response(json.dumps(payload))

    with patch(
        "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
    ):
        with patch("litellm.completion_cost", return_value=0.0):
            client = LLMClient(default_model="gpt-4o-mini", api_key="test-key")
            result = await client.complete_json(
                messages=[{"role": "user", "content": "Return JSON"}]
            )

    assert result == payload


@pytest.mark.asyncio
async def test_retry_on_rate_limit():
    """complete() retries up to max_retries on RateLimitError, then raises."""
    import litellm as _litellm

    call_count = 0

    async def failing_completion(**kwargs):
        nonlocal call_count
        call_count += 1
        raise _litellm.RateLimitError(
            "rate limited", llm_provider="openai", model="gpt-4o-mini"
        )

    with patch("litellm.acompletion", side_effect=failing_completion):
        with patch("asyncio.sleep", new_callable=AsyncMock):  # skip actual wait
            client = LLMClient(
                default_model="gpt-4o-mini", max_retries=3, api_key="test-key"
            )
            with pytest.raises(RuntimeError, match="3 retries"):
                await client.complete(messages=[{"role": "user", "content": "Hi"}])

    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    """complete() retries and succeeds when second attempt works."""
    import litellm as _litellm

    attempt = 0

    async def flaky_completion(**kwargs):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise _litellm.RateLimitError(
                "rate limited", llm_provider="openai", model="gpt-4o-mini"
            )
        return _make_litellm_response("Success on retry")

    with patch("litellm.acompletion", side_effect=flaky_completion):
        with patch("litellm.completion_cost", return_value=0.0):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = LLMClient(
                    default_model="gpt-4o-mini", max_retries=3, api_key="test-key"
                )
                result = await client.complete(
                    messages=[{"role": "user", "content": "Hi"}]
                )

    assert result.content == "Success on retry"
    assert attempt == 2


@pytest.mark.asyncio
async def test_complete_json_raises_on_invalid_json():
    """complete_json() raises ValueError when LLM returns non-JSON content."""
    mock_response = _make_litellm_response("This is not JSON at all")

    with patch(
        "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
    ):
        with patch("litellm.completion_cost", return_value=0.0):
            client = LLMClient(default_model="gpt-4o-mini", api_key="test-key")
            with pytest.raises(ValueError, match="invalid JSON"):
                await client.complete_json(
                    messages=[{"role": "user", "content": "Return JSON"}]
                )


from core.llm import update_active_config, get_llm_client

def test_update_active_config_resets_singleton():
    update_active_config({
        "api_key": "test-key",
        "api_base": "http://localhost:11434",
        "default_model": "ollama/llama3",
        "review_model": "ollama/llama3",
        "embed_model": "ollama/nomic-embed-text",
    })
    client = get_llm_client()
    assert client.default_model == "ollama/llama3"
    assert client.api_base == "http://localhost:11434"
    # Reset to avoid polluting other tests
    update_active_config({})
