"""MISP REST API client using httpx (no pymisp dependency).

Provides get_indicators() for pulling IOCs and add_indicator() for pushing.
Uses connection pooling via httpx.AsyncClient.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MISPConnectionError(Exception):
    """Raised when the MISP server is unreachable."""


class MISPAuthError(Exception):
    """Raised when MISP authentication fails (401)."""


class MISPRateLimitError(Exception):
    """Raised when MISP returns 429 Too Many Requests."""


class MISPClient:
    """Async REST client for MISP threat intelligence platform.

    Uses raw httpx (no pymisp) with connection pooling.
    """

    def __init__(self, url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base_url = url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> MISPClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def get_indicators(
        self,
        *,
        tags: list[str] | None = None,
        days: int = 7,
        ioc_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for indicators (attributes) in MISP.

        Args:
            tags: Filter by tag names (OR logic).
            days: Look back N days.
            ioc_type: Filter by attribute type (e.g. "ip-dst", "domain").

        Returns:
            List of attribute dicts with uuid, type, value, timestamp.

        Raises:
            MISPAuthError: On 401 Unauthorized.
            MISPConnectionError: On connection failure.
            MISPRateLimitError: On 429 Too Many Requests.
        """
        body: dict[str, Any] = {
            "limit": 100,
            "page": 1,
        }

        if tags:
            body["tags"] = tags

        if days:
            body["last"] = f"{days}d"

        if ioc_type:
            body["type"] = ioc_type

        try:
            response = await self._client.post(
                "/attributes/restSearch",
                json=body,
            )
        except httpx.ConnectError as exc:
            raise MISPConnectionError(f"Cannot connect to MISP: {exc}") from exc
        except httpx.RequestError as exc:
            raise MISPConnectionError(f"MISP request failed: {exc}") from exc

        if response.status_code == 401:
            raise MISPAuthError("MISP authentication failed — check your API key")
        if response.status_code == 429:
            raise MISPRateLimitError("MISP rate limit exceeded")

        response.raise_for_status()

        data = response.json()
        attributes = data.get("response", {}).get("Attribute", [])
        return [
            {
                "uuid": attr.get("uuid", ""),
                "type": attr.get("type", ""),
                "value": attr.get("value", ""),
                "timestamp": attr.get("timestamp", ""),
                "category": attr.get("category", ""),
                "comment": attr.get("comment", ""),
            }
            for attr in attributes
        ]

    async def add_indicator(
        self,
        indicator: dict[str, Any],
        *,
        tags: list[str] | None = None,
        info: str = "",
    ) -> str:
        """Push an indicator to MISP as a new event + attribute.

        Args:
            indicator: Dict with 'type', 'value', 'category' keys.
            tags: Optional list of tag names to apply.
            info: Event description/info text.

        Returns:
            UUID of the created attribute.

        Raises:
            MISPAuthError: On 401.
            MISPConnectionError: On connection failure.
        """
        event_body: dict[str, Any] = {
            "Event": {
                "info": info or f"Lupe CTI indicator: {indicator.get('value', '')}",
                "date": "today",
                "distribution": 0,
                "threat_level_id": 2,
                "analysis": 1,
            }
        }

        if tags:
            event_body["Event"]["Tag"] = [{"name": t} for t in tags]

        try:
            event_resp = await self._client.post("/events", json=event_body)
        except httpx.ConnectError as exc:
            raise MISPConnectionError(f"Cannot connect to MISP: {exc}") from exc
        except httpx.RequestError as exc:
            raise MISPConnectionError(f"MISP request failed: {exc}") from exc

        if event_resp.status_code == 401:
            raise MISPAuthError("MISP authentication failed")
        event_resp.raise_for_status()

        event_data = event_resp.json()
        event_uuid = event_data.get("Event", {}).get("uuid", "")

        # Now add the attribute to the event
        attr_body: dict[str, Any] = {
            "Attribute": {
                "event_id": event_uuid,
                "type": indicator.get("type", "ip-dst"),
                "value": indicator.get("value", ""),
                "category": indicator.get("category", "Network activity"),
                "to_ids": True,
                "distribution": 5,
            }
        }

        try:
            attr_resp = await self._client.post(
                f"/attributes/add/", json=attr_body
            )
        except httpx.ConnectError as exc:
            raise MISPConnectionError(f"Cannot connect to MISP: {exc}") from exc
        except httpx.RequestError as exc:
            raise MISPConnectionError(f"MISP request failed: {exc}") from exc

        if attr_resp.status_code == 401:
            raise MISPAuthError("MISP authentication failed")
        attr_resp.raise_for_status()

        attr_data = attr_resp.json()
        return attr_data.get("Attribute", {}).get("uuid", "")
