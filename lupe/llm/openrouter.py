"""OpenRouter LLM provider — OpenAI-compatible gateway to many models."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx

from lupe.llm.base import LLMProvider, ModelInfo
from lupe.llm.registry import register_provider
from lupe.security.https_only import enforce_safe_url

if TYPE_CHECKING:
    from lupe.config import Settings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"


@register_provider
class OpenRouterProvider(LLMProvider):
    """OpenRouter — uses the OpenAI-compatible chat completions endpoint."""

    name = "openrouter"
    requires_api_key = True

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openrouter_api_key or ""
        enforce_safe_url(settings.openrouter_base_url)
        self._base_url = settings.openrouter_base_url.rstrip("/")
        self._model = _DEFAULT_MODEL

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=120.0)
        except httpx.RequestError:
            return ""

        if response.status_code != 200:
            return ""

        try:
            data: dict = response.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            return ""

    async def stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers, timeout=120.0
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = httpx.Response(200, text=data_str).json()
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (ValueError, KeyError, IndexError):
                            continue
        except httpx.RequestError:
            return

    async def validate_key(self) -> bool:
        return self._api_key.startswith("sk-or-") and len(self._api_key) > 10

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(name="anthropic/claude-sonnet-4-20250514", family="claude"),
            ModelInfo(name="openai/gpt-4o", family="gpt"),
            ModelInfo(name="google/gemini-2.5-flash", family="gemini"),
        ]
