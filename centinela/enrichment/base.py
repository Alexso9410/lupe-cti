from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from centinela.models import IOC, IOCType, EnrichmentResult


class EnrichmentPlugin(ABC):
    """Abstract base class for all IOC enrichment plugins."""

    name: str
    supported_ioc_types: set[IOCType]
    requires_api_key: bool = False

    @abstractmethod
    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Enrich an IOC. Return None if no useful data found."""
        ...

    def supports(self, ioc_type: IOCType) -> bool:
        """Return True if this plugin handles the given IOC type."""
        return ioc_type in self.supported_ioc_types
