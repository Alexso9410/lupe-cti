import json
import pytest
import respx
import httpx

from centinela.enrichment.google_safebrowsing import GoogleSafeBrowsingPlugin
from centinela.models import IOC, IOCType, Severity


class TestGoogleSafeBrowsingPlugin:
    @pytest.fixture
    def plugin(self):
        return GoogleSafeBrowsingPlugin(api_key="test-api-key")

    @pytest.fixture
    def url_ioc(self):
        return IOC(type=IOCType.url, value="http://malicious-site.example/malware")

    @pytest.fixture
    def domain_ioc(self):
        return IOC(type=IOCType.domain, value="evil-domain.example")

    @respx.mock
    async def test_malware_detection_url(self, plugin, url_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(200, json={
            "matches": [{
                "threatType": "MALWARE",
                "platformType": "ANY_PLATFORM",
                "threat": {"url": "http://malicious-site.example/malware"},
                "threatEntryType": "URL",
            }]
        }))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical
        assert "MALWARE" in result.summary
        assert "AMENAZA DETECTADA" in result.summary

    @respx.mock
    async def test_social_engineering_detection(self, plugin, url_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(200, json={
            "matches": [{
                "threatType": "SOCIAL_ENGINEERING",
                "platformType": "ANY_PLATFORM",
                "threat": {"url": "http://malicious-site.example/phishing"},
                "threatEntryType": "URL",
            }]
        }))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical
        assert "SOCIAL_ENGINEERING" in result.summary

    @respx.mock
    async def test_unwanted_software(self, plugin, url_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(200, json={
            "matches": [{
                "threatType": "UNWANTED_SOFTWARE",
                "platformType": "ANY_PLATFORM",
                "threat": {"url": url_ioc.value},
                "threatEntryType": "URL",
            }]
        }))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is not None
        assert result.severity == Severity.high

    @respx.mock
    async def test_clean_url_returns_none(self, plugin, url_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(200, json={}))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is None

    @respx.mock
    async def test_empty_matches_returns_none(self, plugin, url_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(200, json={"matches": []}))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is None

    @respx.mock
    async def test_domain_check(self, plugin, domain_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(200, json={
            "matches": [{
                "threatType": "MALWARE",
                "platformType": "ANY_PLATFORM",
                "threat": {"url": "https://evil-domain.example"},
                "threatEntryType": "URL",
            }]
        }))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(domain_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical
        # Verify the domain was converted to https://
        call_data = json.loads(respx.calls.last.request.content)
        assert call_data["threatInfo"]["threatEntries"][0]["url"] == "https://evil-domain.example"

    @respx.mock
    async def test_returns_none_on_500(self, plugin, url_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is None

    @respx.mock
    async def test_raw_data_contains_matches(self, plugin, url_ioc):
        respx.post(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=test-api-key"
        ).mock(return_value=httpx.Response(200, json={
            "matches": [
                {"threatType": "MALWARE", "platformType": "ANY_PLATFORM", "threat": {"url": url_ioc.value}},
                {"threatType": "SOCIAL_ENGINEERING", "platformType": "ANY_PLATFORM", "threat": {"url": url_ioc.value}},
            ]
        }))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert len(result.raw_data["matches"]) == 2
        assert result.source == "google_safebrowsing"
