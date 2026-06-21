import pytest
import respx
import httpx
from lupe.enrichment.pulsedive import PulsedivePlugin
from lupe.models import IOC, IOCType, Severity


class TestPulsedivePlugin:
    @pytest.fixture
    def plugin(self):
        return PulsedivePlugin(api_key="test-pulsedive-key")

    @pytest.fixture
    def ipv4_ioc(self):
        return IOC(type=IOCType.ipv4, value="185.220.101.34")

    @respx.mock
    async def test_high_risk_malicious_ip(self, plugin, ipv4_ioc):
        route = respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(200, json={
                "iid": 12345,
                "indicator": ipv4_ioc.value,
                "type": "ip",
                "risk": "high",
                "threats": [{"name": "C2 Server"}, {"name": "Botnet"}],
                "feeds": [{"name": "AlienVault"}, {"name": "URLhaus"}],
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ipv4_ioc, client)
        assert result is not None
        assert result.severity == Severity.high
        assert "high" in result.summary
        assert "C2 Server" in result.summary

    @respx.mock
    async def test_clean_indicator_returns_none(self, plugin, ipv4_ioc):
        respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(200, json={
                "iid": 99999,
                "indicator": ipv4_ioc.value,
                "type": "ip",
                "risk": "none",
                "threats": [],
                "feeds": [],
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ipv4_ioc, client)
        assert result is None

    @respx.mock
    async def test_medium_risk_domain(self, plugin):
        domain_ioc = IOC(type=IOCType.domain, value="suspicious.example.com")
        respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(200, json={
                "iid": 55555,
                "indicator": domain_ioc.value,
                "type": "domain",
                "risk": "medium",
                "threats": [{"name": "Suspicious Activity"}],
                "feeds": [{"name": "Spamhaus"}],
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(domain_ioc, client)
        assert result is not None
        assert result.severity == Severity.medium

    @respx.mock
    async def test_critical_risk_url(self, plugin):
        url_ioc = IOC(type=IOCType.url, value="http://evil.example.com/malware")
        respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(200, json={
                "iid": 11111,
                "indicator": url_ioc.value,
                "type": "url",
                "risk": "critical",
                "threats": [{"name": "Phishing"}],
                "feeds": [{"name": "PhishTank"}, {"name": "OpenPhish"}],
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(url_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical

    @respx.mock
    async def test_low_risk(self, plugin, ipv4_ioc):
        respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(200, json={
                "iid": 22222,
                "indicator": ipv4_ioc.value,
                "type": "ip",
                "risk": "low",
                "threats": [],
                "feeds": [{"name": "Some Feed"}],
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ipv4_ioc, client)
        assert result is not None
        assert result.severity == Severity.low

    @respx.mock
    async def test_none_with_threats_still_returns(self, plugin, ipv4_ioc):
        """Even with risk=none, if there are threats, should return result"""
        respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(200, json={
                "iid": 33333,
                "indicator": ipv4_ioc.value,
                "type": "ip",
                "risk": "none",
                "threats": [{"name": "Historical Threat"}],
                "feeds": [{"name": "Archive"}],
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ipv4_ioc, client)
        assert result is not None
        assert result.severity == Severity.info  # risk=none -> info, but threats so not None

    @respx.mock
    async def test_returns_none_on_500(self, plugin, ipv4_ioc):
        respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(500)
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ipv4_ioc, client)
        assert result is None

    @respx.mock
    async def test_includes_api_key_in_url(self, plugin, ipv4_ioc):
        respx.get(url__startswith="https://pulsedive.com/api/indicator.php").mock(
            return_value=httpx.Response(200, json={
                "iid": 1,
                "indicator": ipv4_ioc.value,
                "risk": "low",
                "threats": [],
                "feeds": [],
                "type": "ip",
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ipv4_ioc, client)

        # Verify the API key was sent
        req = respx.calls[0].request
        url = str(req.url)
        assert "key=test-pulsedive-key" in url
        assert "indicator=" in url
