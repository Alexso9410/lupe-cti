from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from centinela.enrichment.whatsMyName import WhatsMyNamePlugin, _load_wmn_dataset
from centinela.models import IOC, IOCType, Severity


MOCK_WMN_DATA = {
    "sites": [
        {"name": "GitHub", "uri_check": "https://github.com/{account}", "e_code": 200, "cat": "coding"},
        {"name": "Twitter", "uri_check": "https://twitter.com/{account}", "e_code": 200, "cat": "social"},
        {"name": "NonExistent", "uri_check": "https://nonexistent-site-xyz.com/{account}", "e_code": 200, "cat": "other"},
    ]
}


@pytest.fixture
def clear_cache(tmp_path: Path) -> None:
    """Fixture to patch cache path to a temp directory."""
    cache_path = tmp_path / "wmn-data.json"
    with patch("centinela.enrichment.whatsMyName._CACHE_PATH", cache_path):
        yield cache_path


class TestWhatsMyNamePlugin:
    def test_supports_only_username(self) -> None:
        plugin = WhatsMyNamePlugin()
        assert plugin.supported_ioc_types == {IOCType.username}

    @pytest.mark.asyncio
    @respx.mock
    async def test_finds_accounts_on_matching_sites(self, clear_cache: Path) -> None:
        # Mock the dataset URL
        dataset_route = respx.get("https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json").mock(
            return_value=httpx.Response(200, json=MOCK_WMN_DATA)
        )
        # Mock GitHub returns 200 (account exists)
        github_route = respx.head("https://github.com/testuser").mock(
            return_value=httpx.Response(200)
        )
        # Mock Twitter returns 404 (account doesn't exist)
        twitter_route = respx.head("https://twitter.com/testuser").mock(
            return_value=httpx.Response(404)
        )
        # Mock NonExistent raises ConnectError
        nonexistent_route = respx.head("https://nonexistent-site-xyz.com/testuser").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        plugin = WhatsMyNamePlugin()
        ioc = IOC(type=IOCType.username, value="testuser")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "whats_my_name"
        assert result.raw_data["found_count"] == 1
        assert len(result.raw_data["accounts"]) == 1
        assert result.raw_data["accounts"][0]["site"] == "GitHub"

    @pytest.mark.asyncio
    @respx.mock
    async def test_no_accounts_found(self, clear_cache: Path) -> None:
        # Mock the dataset URL
        respx.get("https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json").mock(
            return_value=httpx.Response(200, json=MOCK_WMN_DATA)
        )
        # All sites return 404
        respx.head("https://github.com/unknownuser").mock(return_value=httpx.Response(404))
        respx.head("https://twitter.com/unknownuser").mock(return_value=httpx.Response(404))
        respx.head("https://nonexistent-site-xyz.com/unknownuser").mock(return_value=httpx.Response(404))

        plugin = WhatsMyNamePlugin()
        ioc = IOC(type=IOCType.username, value="unknownuser")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.raw_data["found_count"] == 0
        assert result.severity == Severity.info

    @pytest.mark.asyncio
    @respx.mock
    async def test_dataset_cached_after_fetch(self, clear_cache: Path) -> None:
        # Mock the dataset URL
        respx.get("https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json").mock(
            return_value=httpx.Response(200, json=MOCK_WMN_DATA)
        )
        # All sites return 404 for simplicity
        respx.route().mock(return_value=httpx.Response(404))

        plugin = WhatsMyNamePlugin()
        ioc = IOC(type=IOCType.username, value="testuser")

        async with httpx.AsyncClient() as client:
            await plugin.enrich(ioc, client)

        # Check cache file was created
        assert clear_cache.exists()
        cached_data = json.loads(clear_cache.read_text(encoding="utf-8"))
        assert "sites" in cached_data
        assert len(cached_data["sites"]) == 3

    @pytest.mark.asyncio
    @respx.mock
    async def test_uses_stale_cache_when_github_fails(self, clear_cache: Path) -> None:
        # Pre-populate stale cache (25 hours old)
        stale_time = time.time() - (25 * 3600)
        clear_cache.parent.mkdir(parents=True, exist_ok=True)
        clear_cache.write_text(json.dumps(MOCK_WMN_DATA), encoding="utf-8")
        # Set modification time to 25 hours ago
        import os
        os.utime(clear_cache, (stale_time, stale_time))

        # Mock GitHub dataset URL to fail
        respx.get("https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )
        # Mock site checks
        respx.head("https://github.com/testuser").mock(return_value=httpx.Response(200))
        respx.route().mock(return_value=httpx.Response(404))

        plugin = WhatsMyNamePlugin()
        ioc = IOC(type=IOCType.username, value="testuser")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        # Should still work using stale cache
        assert result is not None
        assert result.raw_data["found_count"] == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_returns_none_when_dataset_unavailable(self, clear_cache: Path) -> None:
        # Ensure no cache exists
        if clear_cache.exists():
            clear_cache.unlink()

        # Mock GitHub to fail
        respx.get("https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        plugin = WhatsMyNamePlugin()
        ioc = IOC(type=IOCType.username, value="testuser")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None
