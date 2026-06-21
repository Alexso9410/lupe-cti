"""Null/fallback LLM provider — does nothing, returns empty strings."""

from __future__ import annotations

from collections.abc import AsyncIterator

from lupe.llm.base import LLMProvider, ModelInfo


class NullProvider(LLMProvider):
    """Fallback provider used when no LLM is configured.

    All methods are safe no-ops.  generate() returns an empty string so
    callers can simply check ``if result:``.
    """

    name = "null"
    requires_api_key = False

    async def generate(
        self, prompt: str, *, system: str | None = None
    ) -> str:
        return ""

    async def stream(
        self, prompt: str, *, system: str | None = None
    ) -> AsyncIterator[str]:
        if False:  # pragma: no cover
            yield ""

    async def validate_key(self) -> bool:
        return False

    def list_models(self) -> list[ModelInfo]:
        return []
