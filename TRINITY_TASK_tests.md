# Task for Trinity — Centinela: Unit Tests for Phone/OSINT Plugins

## Context

You are implementing unit tests for new phone OSINT plugins added to the **centinela** project.
Project path: `c:\Users\usuario\Documents\proyectos IA aplicada\centinela`

The following files were **recently created/modified** and need tests:

| File | What it does |
|------|-------------|
| `centinela/ioc_detect.py` | Added `_RE_PHONE` regex + phone detection branch |
| `centinela/enrichment/phonestatic.py` | Static phone analysis via `phonenumbers` lib (no API key) |
| `centinela/enrichment/whatsMyName.py` | Username enumeration via WhatsMyName dataset (no API key) |
| `centinela/enrichment/numverify.py` | NumVerify API plugin (requires API key) |
| `centinela/enrichment/ipqs.py` | Added `IPQSPhonePlugin` class at the end |

---

## Step 1 — Read before writing

Read these files first to understand existing patterns:
- `centinela/ioc_detect.py` — understand the detect_ioc function
- `centinela/enrichment/phonestatic.py` — understand the plugin
- `centinela/enrichment/whatsMyName.py` — understand the cache + async logic
- `tests/test_ioc_detect.py` — existing test file to extend
- `tests/__init__.py` — check if there's any fixture setup
- `pyproject.toml` — check pytest config (asyncio mode, etc.)

---

## Step 2 — Extend `tests/test_ioc_detect.py`

Add a new test class at the end of the existing file:

```python
class TestPhoneDetection:
    def test_argentina_mobile(self):
        ioc = detect_ioc("+54 9 2954 123456")
        assert ioc is not None
        assert ioc.type == IOCType.phone
        assert ioc.value == "+54 9 2954 123456"

    def test_argentina_local_with_parens(self):
        ioc = detect_ioc("+54 (02954) 123456")
        assert ioc is not None
        assert ioc.type == IOCType.phone

    def test_us_format(self):
        ioc = detect_ioc("+1-555-123-4567")
        assert ioc is not None
        assert ioc.type == IOCType.phone

    def test_international_with_spaces(self):
        ioc = detect_ioc("+44 20 7946 0958")
        assert ioc is not None
        assert ioc.type == IOCType.phone

    def test_no_plus_prefix_not_phone(self):
        # Without + prefix should NOT be detected as phone
        ioc = detect_ioc("2954123456")
        assert ioc is None or ioc.type != IOCType.phone

    def test_phone_not_confused_with_ip(self):
        # IP address should still be detected as IP, not phone
        ioc = detect_ioc("192.168.1.1")
        assert ioc is not None
        assert ioc.type in (IOCType.ipv4,)

    def test_email_still_detected_as_email(self):
        # Email detection should not be broken by phone regex
        ioc = detect_ioc("test@example.com")
        assert ioc is not None
        assert ioc.type == IOCType.email
```

Make sure `IOCType` is imported in the test file (add if missing).

---

## Step 3 — Create `tests/test_phone_static.py`

This plugin uses only the `phonenumbers` library — no HTTP calls, no mocking needed.

```python
import pytest
from centinela.enrichment.phonestatic import PhoneStaticPlugin
from centinela.models import IOC, IOCType, Severity
import httpx


@pytest.fixture
def plugin():
    return PhoneStaticPlugin()


@pytest.mark.asyncio
async def test_supports_only_phone(plugin):
    assert plugin.supports(IOCType.phone)
    assert not plugin.supports(IOCType.ipv4)
    assert not plugin.supports(IOCType.email)
    assert not plugin.supports(IOCType.username)


@pytest.mark.asyncio
async def test_valid_argentina_mobile(plugin):
    # +54 9 11 XXXX XXXX is a valid Buenos Aires mobile
    ioc = IOC(type=IOCType.phone, value="+54 9 11 5555 5555")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)
    assert result is not None
    assert result.source == "phone_static"
    assert result.raw_data["valid"] is True
    assert "Argentina" in result.raw_data["country"] or result.raw_data["country_code"] == 54
    assert result.severity == Severity.info


@pytest.mark.asyncio
async def test_invalid_number_returns_low_severity(plugin):
    # +54 9 2954 123456 — fake number, invalid
    ioc = IOC(type=IOCType.phone, value="+54 9 2954 123456")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)
    assert result is not None
    assert result.raw_data["valid"] is False
    assert result.severity == Severity.low


@pytest.mark.asyncio
async def test_unparseable_number_returns_none(plugin):
    ioc = IOC(type=IOCType.phone, value="not-a-phone-number")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)
    assert result is None


@pytest.mark.asyncio
async def test_us_number(plugin):
    ioc = IOC(type=IOCType.phone, value="+1 202 555 0173")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)
    assert result is not None
    assert result.raw_data["country_code"] == 1


@pytest.mark.asyncio
async def test_result_has_required_fields(plugin):
    ioc = IOC(type=IOCType.phone, value="+54 9 11 5555 5555")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)
    assert result is not None
    assert "valid" in result.raw_data
    assert "country" in result.raw_data
    assert "line_type" in result.raw_data
    assert "carrier" in result.raw_data
    assert "international_format" in result.raw_data
    assert result.ioc_value == ioc.value
```

---

## Step 4 — Create `tests/test_whats_my_name.py`

This requires mocking HTTP. Use `respx` (already in dev dependencies).

```python
import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import patch
import respx
import httpx
from centinela.enrichment.whatsMyName import WhatsMyNamePlugin, _CACHE_PATH, _WMN_URL
from centinela.models import IOC, IOCType, Severity


MOCK_WMN_DATA = {
    "sites": [
        {
            "name": "GitHub",
            "uri_check": "https://github.com/{account}",
            "e_code": 200,
            "cat": "coding"
        },
        {
            "name": "Twitter",
            "uri_check": "https://twitter.com/{account}",
            "e_code": 200,
            "cat": "social"
        },
        {
            "name": "NonExistent",
            "uri_check": "https://nonexistent-site-xyz.com/{account}",
            "e_code": 200,
            "cat": "other"
        },
    ]
}


@pytest.fixture
def plugin():
    return WhatsMyNamePlugin()


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    """Use a temp cache path so tests don't touch ~/.centinela/"""
    fake_cache = tmp_path / "wmn-data.json"
    monkeypatch.setattr("centinela.enrichment.whatsMyName._CACHE_PATH", fake_cache)
    yield fake_cache


@pytest.mark.asyncio
async def test_supports_only_username(plugin):
    assert plugin.supports(IOCType.username)
    assert not plugin.supports(IOCType.phone)
    assert not plugin.supports(IOCType.ipv4)


@pytest.mark.asyncio
@respx.mock
async def test_finds_accounts_on_matching_sites(plugin, clear_cache):
    # Mock the dataset fetch
    respx.get(_WMN_URL).mock(return_value=httpx.Response(200, json=MOCK_WMN_DATA))
    # Mock site checks: GitHub found, Twitter not found, NonExistent not found
    respx.head("https://github.com/testuser").mock(return_value=httpx.Response(200))
    respx.head("https://twitter.com/testuser").mock(return_value=httpx.Response(404))
    respx.head("https://nonexistent-site-xyz.com/testuser").mock(
        side_effect=httpx.ConnectError("connection refused")
    )

    ioc = IOC(type=IOCType.username, value="testuser")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)

    assert result is not None
    assert result.raw_data["found_count"] == 1
    assert result.raw_data["accounts"][0]["site"] == "GitHub"
    assert result.raw_data["accounts"][0]["url"] == "https://github.com/testuser"


@pytest.mark.asyncio
@respx.mock
async def test_no_accounts_found(plugin, clear_cache):
    respx.get(_WMN_URL).mock(return_value=httpx.Response(200, json=MOCK_WMN_DATA))
    respx.head("https://github.com/zzznobodyhasthisname999").mock(return_value=httpx.Response(404))
    respx.head("https://twitter.com/zzznobodyhasthisname999").mock(return_value=httpx.Response(404))
    respx.head("https://nonexistent-site-xyz.com/zzznobodyhasthisname999").mock(
        return_value=httpx.Response(404)
    )

    ioc = IOC(type=IOCType.username, value="zzznobodyhasthisname999")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)

    assert result is not None
    assert result.raw_data["found_count"] == 0
    assert result.severity == Severity.info


@pytest.mark.asyncio
@respx.mock
async def test_dataset_cached_after_fetch(plugin, clear_cache):
    respx.get(_WMN_URL).mock(return_value=httpx.Response(200, json=MOCK_WMN_DATA))
    respx.head(respx.pattern.M(url__regex=".*")).mock(return_value=httpx.Response(404))

    ioc = IOC(type=IOCType.username, value="anyuser")
    async with httpx.AsyncClient() as client:
        await plugin.enrich(ioc, client)

    # Cache file should now exist
    assert clear_cache.exists()
    cached = json.loads(clear_cache.read_text())
    assert "sites" in cached
    assert len(cached["sites"]) == 3


@pytest.mark.asyncio
@respx.mock
async def test_uses_stale_cache_when_github_fails(plugin, clear_cache):
    # Pre-populate cache
    clear_cache.write_text(json.dumps(MOCK_WMN_DATA), encoding="utf-8")
    # Make cache appear stale (older than TTL)
    import os, time
    stale_time = time.time() - 90000  # 25 hours ago
    os.utime(clear_cache, (stale_time, stale_time))

    # GitHub fetch fails
    respx.get(_WMN_URL).mock(side_effect=httpx.ConnectError("network error"))
    respx.head(respx.pattern.M(url__regex=".*")).mock(return_value=httpx.Response(404))

    ioc = IOC(type=IOCType.username, value="anyuser")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)

    # Should still work using stale cache as fallback
    assert result is not None


@pytest.mark.asyncio
@respx.mock
async def test_returns_none_when_dataset_unavailable(plugin, clear_cache):
    # No cache, no network
    respx.get(_WMN_URL).mock(side_effect=httpx.ConnectError("no network"))

    ioc = IOC(type=IOCType.username, value="anyuser")
    async with httpx.AsyncClient() as client:
        result = await plugin.enrich(ioc, client)

    assert result is None
```

---

## Step 5 — Verify pytest config

Check `pyproject.toml` for the `[tool.pytest.ini_options]` section. It should have:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

If `asyncio_mode` is not set to `"auto"`, the `@pytest.mark.asyncio` decorator alone may not work.
If it's missing, add it. If it's already there as `"auto"`, no change needed.

---

## Step 6 — Run the tests

```bash
cd "c:\Users\usuario\Documents\proyectos IA aplicada\centinela"
pytest tests/test_ioc_detect.py -v
pytest tests/test_phone_static.py -v
pytest tests/test_whats_my_name.py -v
```

Fix any failures before finishing. Common issues:
- Import errors → check the import paths match the actual module structure
- `asyncio_mode` not set → add to pyproject.toml
- `respx` mock pattern not matching URL exactly → use `url__regex` or exact URL

---

## Deliverable

Report back:
1. All tests passing (or specific failures with root cause)
2. Any adjustments made to match the actual code (e.g. if a field name differs)
3. Final pytest output summary
