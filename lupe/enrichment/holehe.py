from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, EnrichmentResult, IOCType, Severity
from lupe.security.rate_limit import RateLimiter

# Per-domain rate limit: 3 req/s — these are unauthenticated public endpoints
# and we don't want to look like a credential-stuffing tool.
_DOMAIN_LIMITERS: dict[str, RateLimiter] = {}
_LIMITER_LOCK = asyncio.Lock()


async def _get_domain_limiter(host: str) -> RateLimiter:
    if host in _DOMAIN_LIMITERS:
        return _DOMAIN_LIMITERS[host]
    async with _LIMITER_LOCK:
        if host not in _DOMAIN_LIMITERS:
            _DOMAIN_LIMITERS[host] = RateLimiter(max_requests=3, per_seconds=1.0)
        return _DOMAIN_LIMITERS[host]

_SITES = [
    {
        "name": "Twitter",
        "url": "https://api.twitter.com/i/users/email_available.json?email={email}",
        "method": "GET",
        "found_if": lambda r: r.status_code == 200 and r.json().get("taken", False),
    },
    {
        "name": "Instagram",
        "url": "https://www.instagram.com/accounts/web_create_ajax/attempt/",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: (
            r.status_code == 200
            and (
                "email" in r.text.lower()
                or "taken" in r.text.lower()
                or "username" in r.text.lower()
            )
        ),
    },
    {
        "name": "Imgur",
        "url": "https://api.imgur.com/account/emailcheck?email={email}",
        "method": "GET",
        "found_if": lambda r: r.status_code == 200 and "false" not in r.text.lower(),
    },
    {
        "name": "Pinterest",
        "url": "https://www.pinterest.com/resource/BaseSearchResource/get/",
        "method": "GET",
        "found_if": lambda r: r.status_code == 200,
    },
    {
        "name": "Tinder",
        "url": "https://www.gotinder.com/auth/send_magic_link",
        "method": "POST",
        "json": {"email": "{email}"},
        "found_if": lambda r: r.status_code == 422 or r.status_code == 200,
    },
    {
        "name": "Scribd",
        "url": "https://www.scribd.com/user/confirm_email",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: "taken" in r.text.lower() or r.status_code == 200,
    },
    {
        "name": "Soundcloud",
        "url": "https://api-v2.soundcloud.com/lookup?email={email}",
        "method": "GET",
        "found_if": lambda r: r.status_code == 200 and r.text,
    },
    {
        "name": "Spotify",
        "url": "https://spclient.wg.spotify.com/signup/public/v1/account",
        "method": "GET",
        "found_if": lambda r: (
            r.status_code == 200
            and ("status" not in r.text or "taken" in r.text.lower() or "1" in r.text)
        ),
    },
    {
        "name": "Flipboard",
        "url": "https://flipboard.com/api/users/email_available?email={email}",
        "method": "GET",
        "found_if": lambda r: r.status_code == 200 and "true" in r.text.lower(),
    },
    {
        "name": "GitHub",
        "url": "https://github.com/join",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: r.status_code == 200,
    },
    {
        "name": "GitLab",
        "url": "https://gitlab.com/users",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: r.status_code == 200,
    },
    {
        "name": "Archive",
        "url": "https://archive.org/account/signup",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: r.status_code == 200,
    },
    {
        "name": "Patreon",
        "url": "https://www.patreon.com/create_account",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: r.status_code == 200,
    },
    {
        "name": "Reddit",
        "url": "https://www.reddit.com/api/v1/users",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: r.status_code == 200,
    },
    {
        "name": "Xbox",
        "url": "https://signup.live.com/API/CheckLiveAccount",
        "method": "POST",
        "data": {"email": "{email}"},
        "found_if": lambda r: r.status_code == 200,
    },
]


class HolehePlugin(EnrichmentPlugin):
    """Email account discovery via registration endpoint probing.

    Checks common services to see if an email is already associated
    with an account by inspecting signup/registration responses.
    """

    name = "holehe"
    supported_ioc_types: set[IOCType] = {IOCType.email}
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        try:
            return await self._do_check(ioc.value)
        except Exception:
            return None

    async def _do_check(self, email: str) -> EnrichmentResult:
        accounts: list[dict] = []
        semaphore = asyncio.Semaphore(8)

        async def check_site(site_def: dict) -> None:
            async with semaphore:
                try:
                    url = site_def["url"].format(email=email)
                    timeout = httpx.Timeout(8.0)

                    # Per-domain rate limit (extracted from the URL host)
                    host = (urlparse(url).hostname or "").lower()
                    if host:
                        try:
                            limiter = await _get_domain_limiter(host)
                            await limiter.acquire()
                        except Exception:
                            pass

                    if site_def["method"] == "POST":
                        if "data" in site_def:
                            form_data = {
                                k: v.format(email=email) for k, v in site_def["data"].items()
                            }
                            resp = await httpx.AsyncClient(timeout=timeout).post(
                                url, data=form_data
                            )
                        elif "json" in site_def:
                            json_data = {
                                k: v.format(email=email) for k, v in site_def["json"].items()
                            }
                            resp = await httpx.AsyncClient(timeout=timeout).post(
                                url, json=json_data
                            )
                        else:
                            resp = await httpx.AsyncClient(timeout=timeout).post(url)
                    else:
                        resp = await httpx.AsyncClient(timeout=timeout).get(url)

                    if site_def["found_if"](resp):
                        accounts.append({"site": site_def["name"], "url": url})
                except Exception:
                    pass

        tasks = [check_site(site) for site in _SITES]
        await asyncio.gather(*tasks)

        count = len(accounts)
        names = [a["site"] for a in accounts]

        if count >= 5:
            severity = Severity.medium
        elif count >= 1:
            severity = Severity.low
        else:
            severity = Severity.info

        extra = f" (+{count - 5} m\\u00e1s)" if count > 5 else ""
        names_str = ", ".join(names[:5]) + extra if names else "ninguna"

        summary = f"Holehe: {count} cuentas encontradas | {names_str}"

        return EnrichmentResult(
            source=self.name,
            ioc_value=email,
            severity=severity,
            summary=summary,
            raw_data={"found_count": count, "accounts": accounts},
            enriched_at=datetime.now(tz=timezone.utc),
        )
