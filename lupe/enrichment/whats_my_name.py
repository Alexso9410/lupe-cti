from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from lupe.config import get_cache_dir
from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity
from lupe.security.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

_WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
_WMN_HOST = "raw.githubusercontent.com"
_WMN_PATH = "/WebBreacher/WhatsMyName/main/wmn-data.json"
_CACHE_PATH = get_cache_dir() / "wmn-data.json"
_CACHE_TTL_SECONDS = 86400
_INNER_CONCURRENCY = 10
_REQUEST_TIMEOUT = 8.0

# Integrity pin for the WhatsMyName dataset.
# Update with each release from https://github.com/WebBreacher/WhatsMyName
# (compute via: sha256sum wmn-data.json). A placeholder of all-zeros means
# the pin is inactive — verification is skipped but the warning is emitted
# so operators can opt in to pinning once they have a known-good digest.
_WMN_SHA256 = "0" * 64

# Per-domain rate limit: be a polite client to GitHub raw content (and any
# other site we query). 5 req/s is well within GitHub's unauthenticated limit.
_DOMAIN_LIMITERS: dict[str, RateLimiter] = {}
_LIMITER_LOCK = asyncio.Lock()


async def _get_domain_limiter(host: str) -> RateLimiter:
    """Return a per-host RateLimiter, creating it on first use."""
    if host in _DOMAIN_LIMITERS:
        return _DOMAIN_LIMITERS[host]
    async with _LIMITER_LOCK:
        if host not in _DOMAIN_LIMITERS:
            _DOMAIN_LIMITERS[host] = RateLimiter(max_requests=5, per_seconds=1.0)
        return _DOMAIN_LIMITERS[host]


def _is_safe_redirect_target(url: httpx.URL) -> bool:
    """Allow only redirects that stay on the original trusted host.

    The WhatsMyName dataset is fetched from ``raw.githubusercontent.com``.
    Any cross-host redirect could pivot to attacker-controlled infrastructure.
    """
    host = url.host or ""
    if host != _WMN_HOST:
        return False
    # Must stay on the same path prefix (no path traversal to other repos)
    if not url.path.startswith(_WMN_PATH):
        return False
    return True


async def _load_wmn_dataset(client: httpx.AsyncClient) -> list[dict]:
    if _CACHE_PATH.exists():
        age = time.time() - _CACHE_PATH.stat().st_mtime
        if age < _CACHE_TTL_SECONDS:
            try:
                return json.loads(_CACHE_PATH.read_text(encoding="utf-8")).get("sites", [])
            except (json.JSONDecodeError, KeyError):
                pass

    # Rate-limit per-host (raw.githubusercontent.com) before hitting the network
    limiter = await _get_domain_limiter(_WMN_HOST)
    await limiter.acquire()

    # follow_redirects=True is required for the raw.githubusercontent.com
    # -> objects.githubusercontent.com 302 dance, but we validate the
    # final URL stays on the trusted host.
    try:
        response = await client.get(_WMN_URL, timeout=30.0, follow_redirects=True)
    except (httpx.RequestError, ValueError):
        return _fallback_to_cache()

    if response.status_code != 200:
        return _fallback_to_cache()

    # Verify the redirect target is still on the trusted host
    if not _is_safe_redirect_target(response.url):
        logger.warning(
            "WhatsMyName dataset fetch redirected to unexpected host: %s",
            response.url,
        )
        return _fallback_to_cache()

    # Integrity check against pinned SHA256
    raw_bytes = response.content
    actual_digest = _sha256_bytes(raw_bytes)
    if _WMN_SHA256 != "0" * 64:
        if actual_digest != _WMN_SHA256:
            logger.warning(
                "WhatsMyName dataset SHA256 mismatch: got %s, expected %s. "
                "Falling back to cache.",
                actual_digest,
                _WMN_SHA256,
            )
            return _fallback_to_cache()
    else:
        logger.debug(
            "WhatsMyName SHA256 pin inactive (placeholder). "
            "Computed digest: %s",
            actual_digest,
        )

    try:
        data = response.json()
    except ValueError:
        return _fallback_to_cache()

    sites = data.get("sites")
    if not isinstance(sites, list):
        return _fallback_to_cache()

    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_bytes(raw_bytes)
    return sites


def _sha256_bytes(data: bytes) -> str:
    """SHA256 hex digest of a bytes payload (mirrors compute_sha256 for files)."""
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _fallback_to_cache() -> list[dict]:
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

            # Per-host rate limit (extracted from the URL host)
            host = (urlparse(url).hostname or "").lower()
            if host:
                try:
                    limiter = await _get_domain_limiter(host)
                    await limiter.acquire()
                except Exception:
                    pass

            async with semaphore:
                try:
                    r = await client.head(url, timeout=_REQUEST_TIMEOUT, follow_redirects=False)
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
