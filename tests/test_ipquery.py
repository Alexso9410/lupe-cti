import pytest
import respx
import httpx
from lupe.enrichment.ipquery import IPQueryPlugin
from lupe.models import IOC, IOCType, Severity
from datetime import datetime, timezone


class TestIPQueryPlugin:
    @pytest.fixture
    def plugin(self):
        return IPQueryPlugin()

    @pytest.fixture
    def ioc_ipv4(self):
        return IOC(type=IOCType.ipv4, value="1.2.3.4")

    @respx.mock
    async def test_high_risk_tor(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={
                    "isp": {"asn": "AS123", "org": "TOR Node", "isp": "TOR"},
                    "location": {"country": "DE", "city": "Frankfurt"},
                    "risk": {
                        "is_vpn": False,
                        "is_tor": True,
                        "is_proxy": False,
                        "is_datacenter": False,
                        "risk_score": 90,
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert result is not None
        assert result.severity == Severity.high
        assert "tor=True" in result.summary

    @respx.mock
    async def test_high_risk_score(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={
                    "isp": {"asn": "AS500"},
                    "location": {"country": "US", "city": "NY"},
                    "risk": {
                        "is_vpn": False,
                        "is_tor": False,
                        "is_proxy": False,
                        "is_datacenter": True,
                        "risk_score": 80,
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert result is not None
        assert result.severity == Severity.high

    @respx.mock
    async def test_medium_risk_vpn(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={
                    "isp": {"asn": "AS456"},
                    "location": {"country": "AR", "city": "Buenos Aires"},
                    "risk": {
                        "is_vpn": True,
                        "is_tor": False,
                        "is_proxy": False,
                        "is_datacenter": False,
                        "risk_score": 40,
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert result.severity == Severity.medium

    @respx.mock
    async def test_low_risk(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={
                    "isp": {"asn": "AS789"},
                    "location": {"country": "ES", "city": "Madrid"},
                    "risk": {
                        "is_vpn": False,
                        "is_tor": False,
                        "is_proxy": False,
                        "is_datacenter": False,
                        "risk_score": 30,
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert result.severity == Severity.low

    @respx.mock
    async def test_info_low_score(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={
                    "isp": {"asn": "AS111"},
                    "location": {"country": "FR", "city": "Paris"},
                    "risk": {
                        "is_vpn": False,
                        "is_tor": False,
                        "is_proxy": False,
                        "is_datacenter": False,
                        "risk_score": 5,
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert result.severity == Severity.info

    @respx.mock
    async def test_returns_none_on_500(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            return_value=httpx.Response(500)
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert result is None

    @respx.mock
    async def test_returns_none_on_timeout(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert result is None

    @respx.mock
    async def test_raw_data_contains_expected_fields(self, plugin, ioc_ipv4):
        respx.get("https://api.ipquery.io/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={
                    "isp": {"asn": "AS999"},
                    "location": {"country": "JP", "city": "Tokyo"},
                    "risk": {
                        "risk_score": 10,
                        "is_vpn": False,
                        "is_tor": False,
                        "is_proxy": False,
                        "is_datacenter": False,
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc_ipv4, client)
        assert "risk" in result.raw_data
        assert "location" in result.raw_data
        assert "isp" in result.raw_data
        assert result.source == "ipquery"
        assert result.ioc_value == "1.2.3.4"
