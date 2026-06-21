import pytest
import respx
import httpx
from datetime import datetime, timezone, timedelta
from lupe.enrichment.certsh import CertShPlugin
from lupe.models import IOC, IOCType, Severity

class TestCertShPlugin:
    @pytest.fixture
    def plugin(self):
        return CertShPlugin()

    @pytest.fixture
    def ioc(self):
        return IOC(type=IOCType.domain, value="example.com")

    @respx.mock
    async def test_active_certs_with_subdomains(self, plugin, ioc):
        future = (datetime.now(tz=timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        past = (datetime.now(tz=timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        respx.get("https://crt.sh/?q=example.com&output=json").mock(return_value=httpx.Response(200, json=[
            {
                "name_value": "example.com\nsub1.example.com",
                "not_after": future,
                "issuer_name": "CN=Let's Encrypt",
            },
            {
                "name_value": "example.com\nsub2.example.com",
                "not_after": future,
                "issuer_name": "CN=Cloudflare",
            },
            {
                "name_value": "example.com\nold.example.com",
                "not_after": past,
                "issuer_name": "CN=DigiCert",
            },
        ]))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        assert result is not None
        assert result.severity == Severity.medium
        assert "3 certs" in result.summary
        assert "2 activos" in result.summary
        assert "sub1.example.com" in result.raw_data["subdomains"]
        assert "sub2.example.com" in result.raw_data["subdomains"]

    @respx.mock
    async def test_no_active_certs_info_severity(self, plugin, ioc):
        past = (datetime.now(tz=timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        respx.get("https://crt.sh/?q=example.com&output=json").mock(return_value=httpx.Response(200, json=[
            {"name_value": "example.com", "not_after": past, "issuer_name": "CN=Old CA"},
        ]))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        assert result is not None
        assert result.severity == Severity.info
        assert result.raw_data["active_certs"] == 0

    @respx.mock
    async def test_returns_none_on_500(self, plugin, ioc):
        respx.get("https://crt.sh/?q=example.com&output=json").mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        assert result is None

    @respx.mock
    async def test_returns_none_on_non_json(self, plugin, ioc):
        respx.get("https://crt.sh/?q=example.com&output=json").mock(return_value=httpx.Response(200, text="not json"))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        assert result is None

    @respx.mock
    async def test_many_subdomains_truncated(self, plugin, ioc):
        future = (datetime.now(tz=timezone.utc) + timedelta(days=100)).strftime("%Y-%m-%d %H:%M:%S")
        certs = []
        for i in range(12):
            certs.append({
                "name_value": f"example.com\nsub{i}.example.com",
                "not_after": future,
                "issuer_name": "CN=Test",
            })
        respx.get("https://crt.sh/?q=example.com&output=json").mock(return_value=httpx.Response(200, json=certs))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        assert result is not None
        assert len(result.raw_data["subdomains"]) == 12
        assert "+7 más" in result.summary

    @respx.mock
    async def test_unique_subdomains(self, plugin, ioc):
        future = (datetime.now(tz=timezone.utc) + timedelta(days=50)).strftime("%Y-%m-%d %H:%M:%S")
        respx.get("https://crt.sh/?q=example.com&output=json").mock(return_value=httpx.Response(200, json=[
            {"name_value": "example.com\nsub1.example.com", "not_after": future},
            {"name_value": "example.com\nsub1.example.com", "not_after": future},  # duplicate
            {"name_value": "example.com\nsub2.example.com", "not_after": future},
        ]))
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        assert result.raw_data["subdomains"] == ["sub1.example.com", "sub2.example.com"]
        assert result.raw_data["total_certs"] == 3
