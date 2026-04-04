"""Unified LLM client wrapping litellm with retry logic and token tracking."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import litellm  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel

from config import settings


class LLMResponse(BaseModel):
    content: str
    tokens_used: int
    cost: float
    model: str


class LLMClient:
    """Async LLM client with retry logic and cost tracking. All calls go through litellm."""

    def __init__(
        self,
        default_model: str | None = None,
        review_model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
    ) -> None:
        self.default_model = default_model or settings.llm_default_model
        self.review_model = review_model or settings.llm_review_model
        self.api_key = api_key or settings.llm_api_key
        self.api_base = api_base or settings.llm_api_base
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Call LLM with retry on rate limit / transient errors."""
        chosen_model = model or self.default_model
        kwargs: dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if response_format:
            kwargs["response_format"] = response_format

        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = await litellm.acompletion(**kwargs)
                content = response.choices[0].message.content or ""
                tokens = (
                    getattr(response.usage, "total_tokens", 0) if response.usage else 0
                )
                cost = (
                    litellm.completion_cost(completion_response=response)
                    if response.usage
                    else 0.0
                )
                return LLMResponse(
                    content=content,
                    tokens_used=tokens,
                    cost=cost,
                    model=chosen_model,
                )
            except (
                litellm.RateLimitError,
                litellm.Timeout,
                litellm.ServiceUnavailableError,
            ) as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    wait = self.backoff_factor**attempt
                    await asyncio.sleep(wait)
            except Exception as exc:
                raise exc  # non-retryable — propagate immediately

        raise RuntimeError(
            f"LLM call failed after {self.max_retries} retries"
        ) from last_exc

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Call LLM requesting JSON output. Parses and returns dict."""
        response = await self.complete(
            messages=messages,
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON: {response.content[:200]}"
            ) from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts via litellm."""
        response = await litellm.aembedding(
            model=settings.llm_embed_model,
            input=texts,
            api_key=self.api_key,
            api_base=self.api_base,
        )
        return [item["embedding"] for item in response.data]


# Module-level singleton — used by skills
_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create module-level LLMClient instance."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
