"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lupe.config import Settings


@dataclass(frozen=True)
class ModelInfo:
    """Metadata about an LLM model."""

    name: str
    size: str | None = None
    family: str | None = None


class LLMProvider(ABC):
    """Abstract base for all LLM providers.

    Every provider must implement generate(), stream(), validate_key(),
    and list_models().  Providers are instantiated via the registry factory
    which passes the application Settings to the constructor.
    """

    name: str
    requires_api_key: bool = True

    def __init__(self, settings: Settings | None = None) -> None:  # pragma: no cover
        """Initialise the provider with application settings."""

    @abstractmethod
    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Send a prompt and return the model's text response."""
        ...

    @abstractmethod
    async def stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        """Send a prompt and yield tokens as they arrive."""
        ...
        # Make this an async generator for type-checkers
        yield ""  # pragma: no cover

    @abstractmethod
    async def validate_key(self) -> bool:
        """Return True if the configured API key appears valid."""
        ...

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """Return a list of models available from this provider."""
        ...
