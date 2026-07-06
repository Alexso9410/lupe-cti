"""Google Gemini LLM provider via Google AI Studio REST API."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import httpx

from lupe.llm.base import LLMProvider, ModelInfo
from lupe.llm.registry import register_provider

if TYPE_CHECKING:
    from lupe.config import Settings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


@register_provider
class GeminiProvider(LLMProvider):
    """Google Gemini models via the Google AI Studio generateContent API.

    Uses raw ``httpx`` (no SDK) to match the pattern of other Lupe providers.
    Auth via ``x-goog-api-key`` header.  Payload uses Google's
    ``contents/parts`` structure, not OpenAI's ``messages`` format.
    """

    name = "gemini"
    requires_api_key = True

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.gemini_api_key or ""
        self._model = getattr(settings, "gemini_model", _DEFAULT_MODEL) or _DEFAULT_MODEL

    # ------------------------------------------------------------------
    # generate
    # ------------------------------------------------------------------

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        contents: list[dict] = [{"role": "user", "parts": [{"text": prompt}]}]

        payload: dict = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        url = f"{_BASE_URL}/{self._model}:generateContent"
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=headers, timeout=120.0
                )
        except httpx.RequestError:
            return ""

        if response.status_code != 200:
            return ""

        try:
            data: dict = response.json()
            return str(data["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, ValueError):
            return ""

    # ------------------------------------------------------------------
    # stream
    # ------------------------------------------------------------------

    async def stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        contents: list[dict] = [{"role": "user", "parts": [{"text": prompt}]}]

        payload: dict = {"contents": contents}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        url = f"{_BASE_URL}/{self._model}:streamGenerateContent?alt=sse"
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers, timeout=120.0
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                            if text:
                                yield text
                        except (json.JSONDecodeError, KeyError, IndexError, ValueError):
                            continue
        except httpx.RequestError:
            return

    # ------------------------------------------------------------------
    # validate_key
    # ------------------------------------------------------------------

    async def validate_key(self) -> bool:
        if not self._api_key:
            return False
        # Google AI Studio keys typically start with "AIza"
        return self._api_key.startswith("AIza") and len(self._api_key) > 10

    # ------------------------------------------------------------------
    # list_models
    # ------------------------------------------------------------------

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(name="gemini-2.5-flash", family="gemini"),
            ModelInfo(name="gemini-2.5-pro", family="gemini"),
        ]
