"""Ollama LLM provider — local inference server."""

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


@register_provider
class OllamaProvider(LLMProvider):
    """Ollama local LLM server.

    Uses the OpenAI-compatible ``/v1/chat/completions`` endpoint.
    No API key is required.
    """

    name = "ollama"
    requires_api_key = False  # Optional: only required for cloud models (e.g. gemma4:31b-cloud)

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._api_key = getattr(settings, "ollama_api_key", None) or None

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
        url = f"{self._base_url}/v1/chat/completions"

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=120.0)
        except httpx.ConnectError:
            logger.debug("Ollama not reachable at %s", self._base_url)
            return ""
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
        url = f"{self._base_url}/v1/chat/completions"

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

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
        # If no API key is set, verify Ollama is reachable
        if not self._api_key:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    r = await client.get(f"{self._base_url}/api/tags", timeout=5.0)
                    return r.status_code == 200
            except Exception:
                return False
        # If API key is set, verify it works against the server
        try:
            import httpx

            headers = {"Authorization": f"Bearer {self._api_key}"}
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self._base_url}/api/tags", headers=headers, timeout=5.0)
                return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(name=self._model)]
