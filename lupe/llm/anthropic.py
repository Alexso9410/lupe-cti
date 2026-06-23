"""Anthropic Claude LLM provider."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx

from lupe.llm.base import LLMProvider, ModelInfo
from lupe.llm.registry import register_provider

if TYPE_CHECKING:
    from lupe.config import Settings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-20250514"


@register_provider
class AnthropicProvider(LLMProvider):
    """Anthropic Claude models via the Messages API."""

    name = "anthropic"
    requires_api_key = True

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.anthropic_api_key or ""
        self._model = _DEFAULT_MODEL

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        messages = [{"role": "user", "content": prompt}]
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 2048,
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers,
                    timeout=120.0,
                )
        except httpx.RequestError:
            return ""

        if response.status_code != 200:
            return ""

        try:
            data: dict = response.json()
            return str(data["content"][0]["text"])
        except (KeyError, IndexError, ValueError):
            return ""

    async def stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        messages = [{"role": "user", "content": prompt}]
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 2048,
            "stream": True,
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers,
                    timeout=120.0,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                event = httpx.Response(200, text=data_str).json()
                                if event.get("type") == "content_block_delta":
                                    text = event.get("delta", {}).get("text", "")
                                    if text:
                                        yield text
                            except (ValueError, KeyError):
                                continue
        except httpx.RequestError:
            return

    async def validate_key(self) -> bool:
        return self._api_key.startswith("sk-ant-") and len(self._api_key) > 15

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(name="claude-sonnet-4-20250514", family="claude"),
            ModelInfo(name="claude-3-5-haiku-20241022", family="claude"),
            ModelInfo(name="claude-3-opus-20240229", family="claude"),
        ]
