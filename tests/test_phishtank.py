import pytest
import respx
import httpx
from lupe.enrichment.phishtank import PhishTankPlugin
from lupe.models import IOC, IOCType, Severity


class TestPhishTankPlugin:
    @pytest.fixture
    def plugin(self):
        return PhishTankPlugin(api_key="test-app-key")

    @pytest.fixture
    def url_ioc(self):
        return IOC(type=IOCType.url, value="http://evil-phishing.example/login")

    @respx.mock
    async def test_verified_phishing(self, plugin, url_ioc):
        respx.post("https://checkurl.phishtank.com/checkurl/").mock(
            return_value=httpx.Response(200, json={
                "results": {
                    "url": url_ioc.value,
                    "in_database": True,
                    "phish_detail_page": "http://www.phishtank.com/phish_detail.php?phish_id=12345",
                    "verified": True,
                    "valid": True,
                }
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical
        assert "VERIFICADO" in result.summary
        assert "phishtank.com" in result.summary

    @respx.mock
    async def test_unverified_phishing(self, plugin, url_ioc):
        respx.post("https://checkurl.phishtank.com/checkurl/").mock(
            return_value=httpx.Response(200, json={
                "results": {
                    "url": url_ioc.value,
                    "in_database": True,
                    "phish_detail_page": "http://www.phishtank.com/phish_detail.php?phish_id=67890",
                    "verified": False,
                    "valid": True,
                }
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is not None
        assert result.severity == Severity.high
        assert "reportado" in result.summary

    @respx.mock
    async def test_not_in_database(self, plugin, url_ioc):
        respx.post("https://checkurl.phishtank.com/checkurl/").mock(
            return_value=httpx.Response(200, json={
                "results": {
                    "url": url_ioc.value,
                    "in_database": False,
                    "phish_detail_page": "",
                    "verified": False,
                    "valid": False,
                }
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is None

    @respx.mock
    async def test_not_valid(self, plugin, url_ioc):
        """URL was phishing but is no longer valid/offline"""
        respx.post("https://checkurl.phishtank.com/checkurl/").mock(
            return_value=httpx.Response(200, json={
                "results": {
                    "url": url_ioc.value,
                    "in_database": True,
                    "phish_detail_page": "http://www.phishtank.com/phish_detail.php?phish_id=111",
                    "verified": True,
                    "valid": False,
                }
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is None

    @respx.mock
    async def test_returns_none_on_500(self, plugin, url_ioc):
        respx.post("https://checkurl.phishtank.com/checkurl/").mock(
            return_value=httpx.Response(500)
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is None

    @respx.mock
    async def test_raw_data(self, plugin, url_ioc):
        respx.post("https://checkurl.phishtank.com/checkurl/").mock(
            return_value=httpx.Response(200, json={
                "results": {
                    "url": url_ioc.value,
                    "in_database": True,
                    "phish_detail_page": "https://example.com/detail",
                    "verified": True,
                    "valid": True,
                }
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result.raw_data["verified"] is True
        assert result.raw_data["valid"] is True
        assert result.source == "phishtank"

    @respx.mock
    async def test_sends_correct_payload(self, plugin, url_ioc):
        route = respx.post("https://checkurl.phishtank.com/checkurl/").mock(
            return_value=httpx.Response(200, json={
                "results": {
                    "url": url_ioc.value,
                    "in_database": True,
                    "phish_detail_page": "https://example.com",
                    "verified": True,
                    "valid": True,
                }
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        req = route.calls[0].request
        body = str(req.content)
        assert f"url={url_ioc.value}" in body or "url%3" in body or "url=" in body
        assert "test-app-key" in body
        assert "app_key" in body
