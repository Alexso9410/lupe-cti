from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity

_WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
_CACHE_PATH = Path.home() / ".centinela" / "wmn-data.json"
_CACHE_TTL_SECONDS = 86400
_INNER_CONCURRENCY = 10
_REQUEST_TIMEOUT = 8.0


async def _load_wmn_dataset(client: httpx.AsyncClient) -> list[dict]:
    if _CACHE_PATH.exists():
        age = time.time() - _CACHE_PATH.stat().st_mtime
        if age < _CACHE_TTL_SECONDS:
            try:
                return json.loads(_CACHE_PATH.read_text(encoding="utf-8")).get("sites", [])
            except (json.JSONDecodeError, KeyError):
                pass
    try:
        response = await client.get(_WMN_URL, timeout=30.0)
        if response.status_code == 200:
            data = response.json()
            if "sites" not in data:
                return []
            _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_PATH.write_text(response.text, encoding="utf-8")
            return data["sites"]
    except (httpx.RequestError, ValueError):
        pass
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8")).get("sites", [])
        except (json.JSONDecodeError, KeyError):
            pass
    return []


class WhatsMyNamePlugin(EnrichmentPlugin):
    name = "whats_my_name"
    supported_ioc_types: set[IOCType] = {IOCType.username}
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        username = ioc.value
        sites = await _load_wmn_dataset(client)
        if not sites:
            return None

        semaphore = asyncio.Semaphore(_INNER_CONCURRENCY)

        async def _check_site(site: dict) -> dict | None:
            url_template = site.get("uri_check", "")
            if not url_template or "{account}" not in url_template:
                return None
            url = url_template.replace("{account}", username)
            expected_code = site.get("e_code", 200)
            async with semaphore:
                try:
                    r = await client.head(
                        url, timeout=_REQUEST_TIMEOUT, follow_redirects=True
                    )
                    if r.status_code == expected_code:
                        return {
                            "site": site.get("name", ""),
                            "url": url,
                            "category": site.get("cat", ""),
                            "status_code": r.status_code,
                        }
                except (httpx.RequestError, httpx.TimeoutException):
                    pass
            return None

        tasks = [_check_site(site) for site in sites]
        raw_results = await asyncio.gather(*tasks)
        found = [r for r in raw_results if r is not None]

        if not found:
            return EnrichmentResult(
                source=self.name,
                ioc_value=ioc.value,
                severity=Severity.info,
                summary="No se encontraron cuentas en sitios conocidos",
                raw_data={"found_count": 0, "accounts": []},
                enriched_at=datetime.now(tz=timezone.utc),
            )

        count = len(found)
        site_names = [f["site"] for f in found[:5]]
        more = f" (+{count - 5} más)" if count > 5 else ""
        severity = Severity.medium if count >= 5 else Severity.low

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=f"Cuentas encontradas: {count} | {', '.join(site_names)}{more}",
            raw_data={"found_count": count, "accounts": found},
            enriched_at=datetime.now(tz=timezone.utc),
        )
