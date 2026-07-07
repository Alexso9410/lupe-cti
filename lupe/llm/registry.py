"""LLM provider registry and factory."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lupe.llm.base import LLMProvider
from lupe.llm.null import NullProvider

if TYPE_CHECKING:
    from lupe.config import Settings

logger = logging.getLogger(__name__)

# Provider name → class mapping.  Populated by register_provider().
_PROVIDERS: dict[str, type[LLMProvider]] = {}


def register_provider(cls: type[LLMProvider]) -> type[LLMProvider]:
    """Class decorator that registers an LLM provider by its ``name``."""
    _PROVIDERS[cls.name] = cls
    return cls


def get_provider(name: str, settings: Settings) -> LLMProvider:
    """Factory: return an LLM provider instance for *name*.

    Returns a :class:`NullProvider` when:
    - *name* is empty or not recognised
    - The provider's ``from_settings()`` returns ``None`` (missing key)
    """
    if not name:
        logger.warning("No LLM provider configured — AI analysis disabled")
        return NullProvider()

    cls = _PROVIDERS.get(name)
    if cls is None:
        valid = ", ".join(sorted(_PROVIDERS)) or "none registered"
        logger.warning(
            "Unknown LLM provider %r (valid: %s) — falling back to NullProvider",
            name,
            valid,
        )
        return NullProvider()

    try:
        provider = cls(settings)
    except Exception:
        logger.warning("Failed to initialize LLM provider %r", name, exc_info=True)
        return NullProvider()

    return provider


# Import submodules so their @register_provider decorators execute.
# This must happen AFTER _PROVIDERS and register_provider are defined.
from lupe.llm import anthropic as _anthropic  # noqa: E402, F401
from lupe.llm import gemini as _gemini  # noqa: E402, F401
from lupe.llm import ollama as _ollama  # noqa: E402, F401
from lupe.llm import openai as _openai  # noqa: E402, F401
from lupe.llm import openrouter as _openrouter  # noqa: E402, F401
