"""Tests for new enrichment plugins: Blocklist.de, Spamhaus, crt.sh, Hybrid Analysis, Censys."""

from __future__ import annotations

import httpx
import pytest
import respx

from lupe.models import IOC, IOCType

# ---------------------------------------------------------------------------
# Blocklist.de Plugin Tests
# ---------------------------------------------------------------------------


class TestBlocklistDePlugin:
    """Tests for BlocklistDePlugin."""

    def test_plugin_name(self):
        from lupe.enrichment.blocklist_de import BlocklistDePlugin

        plugin = BlocklistDePlugin()
        assert plugin.name == "blocklist-de"

    def test_supports_ipv4(self):
        from lupe.enrichment.blocklist_de import BlocklistDePlugin

        plugin = BlocklistDePlugin()
        assert plugin.supports(IOCType.ipv4)
        assert plugin.supports(IOCType.ipv6)
        assert not plugin.supports(IOCType.domain)

    def test_no_api_key_required(self):
        from lupe.enrichment.blocklist_de import BlocklistDePlugin

        plugin = BlocklistDePlugin()
        assert plugin.requires_api_key is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_listed_ip(self):
        from lupe.enrichment.blocklist_de import BlocklistDePlugin

        plugin = BlocklistDePlugin()

        respx.get("https://api.blocklist.de/api.php").mock(
            return_value=httpx.Response(
                200,
                json={"attacks": 42, "blacklists": {"spamhaus": True, "barracuda": True}},
            )
        )

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "blocklist.de"
        assert result.severity.value in ("low", "medium", "high")

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_clean_ip_returns_none(self):
        from lupe.enrichment.blocklist_de import BlocklistDePlugin

        plugin = BlocklistDePlugin()

        respx.get("https://api.blocklist.de/api.php").mock(
            return_value=httpx.Response(200, json={"attacks": 0})
        )

        ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_error_returns_none(self):
        from lupe.enrichment.blocklist_de import BlocklistDePlugin

        plugin = BlocklistDePlugin()

        respx.get("https://api.blocklist.de/api.php").mock(return_value=httpx.Response(500))

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None


# ---------------------------------------------------------------------------
# Spamhaus Plugin Tests
# ---------------------------------------------------------------------------


class TestSpamhausPlugin:
    """Tests for SpamhausPlugin."""

    def test_plugin_name(self):
        from lupe.enrichment.spamhaus import SpamhausPlugin

        plugin = SpamhausPlugin(api_key="test")
        assert plugin.name == "spamhaus"

    def test_supports_ip_and_domain(self):
        from lupe.enrichment.spamhaus import SpamhausPlugin

        plugin = SpamhausPlugin(api_key="test")
        assert plugin.supports(IOCType.ipv4)
        assert plugin.supports(IOCType.domain)
        assert not plugin.supports(IOCType.hash_sha256)

    def test_requires_api_key(self):
        from lupe.enrichment.spamhaus import SpamhausPlugin

        plugin = SpamhausPlugin()
        assert plugin.requires_api_key is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_ipv4_malicious(self):
        from lupe.enrichment.spamhaus import SpamhausPlugin

        plugin = SpamhausPlugin(api_key="test-key")

        respx.get("https://api.spamhaus.org/api/v2/intel/ipv4/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={"score": 7, "categories": ["spam", "botnet"], "description": "Known spammer"},
            )
        )

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "spamhaus"
        assert "spam" in result.summary.lower() or "botnet" in result.summary.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_not_found_returns_none(self):
        from lupe.enrichment.spamhaus import SpamhausPlugin

        plugin = SpamhausPlugin(api_key="test-key")

        respx.get("https://api.spamhaus.org/api/v2/intel/ipv4/8.8.8.8").mock(
            return_value=httpx.Response(404)
        )

        ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_auth_failure_returns_none(self):
        from lupe.enrichment.spamhaus import SpamhausPlugin

        plugin = SpamhausPlugin(api_key="bad-key")

        respx.get("https://api.spamhaus.org/api/v2/intel/ipv4/1.2.3.4").mock(
            return_value=httpx.Response(401)
        )

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @pytest.mark.asyncio
    async def test_no_key_returns_none(self):
        from lupe.enrichment.spamhaus import SpamhausPlugin

        plugin = SpamhausPlugin(api_key="")

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None


# ---------------------------------------------------------------------------
# crt.sh Plugin Tests
# ---------------------------------------------------------------------------


class TestCrtShPlugin:
    """Tests for CrtShPlugin."""

    def test_plugin_name(self):
        from lupe.enrichment.crtsh import CrtShPlugin

        plugin = CrtShPlugin()
        assert plugin.name == "crt.sh"

    def test_supports_domain_only(self):
        from lupe.enrichment.crtsh import CrtShPlugin

        plugin = CrtShPlugin()
        assert plugin.supports(IOCType.domain)
        assert not plugin.supports(IOCType.ipv4)

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_domain_returns_certs(self):
        from lupe.enrichment.crtsh import CrtShPlugin

        plugin = CrtShPlugin()

        respx.get("https://crt.sh/").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"name_value": "example.com\nwww.example.com", "issuer_name": "Let's Encrypt"},
                    {"name_value": "mail.example.com", "issuer_name": "Let's Encrypt"},
                ],
            )
        )

        ioc = IOC(type=IOCType.domain, value="example.com")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "crt.sh"
        assert "certificate" in result.summary.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_response_returns_none(self):
        from lupe.enrichment.crtsh import CrtShPlugin

        plugin = CrtShPlugin()

        respx.get("https://crt.sh/").mock(return_value=httpx.Response(200, json=[]))

        ioc = IOC(type=IOCType.domain, value="nonexistent.example")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_unsupported_type_returns_none(self):
        from lupe.enrichment.crtsh import CrtShPlugin

        plugin = CrtShPlugin()

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None


# ---------------------------------------------------------------------------
# Hybrid Analysis Plugin Tests
# ---------------------------------------------------------------------------


class TestHybridAnalysisPlugin:
    """Tests for HybridAnalysisPlugin."""

    def test_plugin_name(self):
        from lupe.enrichment.hybrid_analysis import HybridAnalysisPlugin

        plugin = HybridAnalysisPlugin(api_key="test")
        assert plugin.name == "hybrid_analysis"

    def test_supports_hashes_and_urls(self):
        from lupe.enrichment.hybrid_analysis import HybridAnalysisPlugin

        plugin = HybridAnalysisPlugin(api_key="test")
        assert plugin.supports(IOCType.hash_sha256)
        assert plugin.supports(IOCType.url)
        assert not plugin.supports(IOCType.ipv4)

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_hash(self):
        from lupe.enrichment.hybrid_analysis import HybridAnalysisPlugin

        plugin = HybridAnalysisPlugin(api_key="test-key")

        respx.post("https://www.hybrid-analysis.com/api/v2/search/hash").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "verdict": "malicious",
                        "threat_score": 85,
                        "type_description": "PE32 executable",
                        "environment_description": "Windows 10 64-bit",
                    }
                ],
            )
        )

        ioc = IOC(type=IOCType.hash_sha256, value="abc123" * 11)
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "hybrid_analysis"
        assert "malicious" in result.summary.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_quota_exceeded_returns_none(self):
        from lupe.enrichment.hybrid_analysis import HybridAnalysisPlugin

        plugin = HybridAnalysisPlugin(api_key="test-key")

        respx.post("https://www.hybrid-analysis.com/api/v2/search/hash").mock(
            return_value=httpx.Response(429)
        )

        ioc = IOC(type=IOCType.hash_sha256, value="abc123" * 11)
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_auth_error_returns_none(self):
        from lupe.enrichment.hybrid_analysis import HybridAnalysisPlugin

        plugin = HybridAnalysisPlugin(api_key="bad-key")

        respx.post("https://www.hybrid-analysis.com/api/v2/search/hash").mock(
            return_value=httpx.Response(401)
        )

        ioc = IOC(type=IOCType.hash_sha256, value="abc123" * 11)
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @pytest.mark.asyncio
    async def test_no_key_returns_none(self):
        from lupe.enrichment.hybrid_analysis import HybridAnalysisPlugin

        plugin = HybridAnalysisPlugin(api_key="")

        ioc = IOC(type=IOCType.hash_sha256, value="abc123" * 11)
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None


# ---------------------------------------------------------------------------
# Censys Plugin Tests
# ---------------------------------------------------------------------------


class TestCensysPlugin:
    """Tests for CensysPlugin."""

    def test_plugin_name(self):
        from lupe.enrichment.censys import CensysPlugin

        plugin = CensysPlugin(censys_id="id", censys_secret="secret")
        assert plugin.name == "censys"

    def test_supports_ip_and_domain(self):
        from lupe.enrichment.censys import CensysPlugin

        plugin = CensysPlugin(censys_id="id", censys_secret="secret")
        assert plugin.supports(IOCType.ipv4)
        assert plugin.supports(IOCType.domain)
        assert not plugin.supports(IOCType.hash_sha256)

    def test_requires_two_keys(self):
        from lupe.enrichment.censys import CensysPlugin

        plugin = CensysPlugin()
        assert plugin.requires_api_key is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_ipv4(self):
        from lupe.enrichment.censys import CensysPlugin

        plugin = CensysPlugin(censys_id="test-id", censys_secret="test-secret")

        respx.get("https://search.censys.io/api/v2/hosts/1.2.3.4").mock(
            return_value=httpx.Response(
                200,
                json={
                    "result": {
                        "services": [
                            {"service_name": "HTTP", "port": 80},
                            {"service_name": "HTTPS", "port": 443},
                        ],
                        "operating_system": {"product": "Linux"},
                        "autonomous_system": {"asn": 12345},
                        "last_updated_at": "2024-01-01T00:00:00Z",
                    }
                },
            )
        )

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "censys"
        assert "service" in result.summary.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_invalid_credentials_returns_none(self):
        from lupe.enrichment.censys import CensysPlugin

        plugin = CensysPlugin(censys_id="bad-id", censys_secret="bad-secret")

        respx.get("https://search.censys.io/api/v2/hosts/1.2.3.4").mock(
            return_value=httpx.Response(401)
        )

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @pytest.mark.asyncio
    async def test_no_keys_returns_none(self):
        from lupe.enrichment.censys import CensysPlugin

        plugin = CensysPlugin(censys_id="", censys_secret="")

        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        from lupe.enrichment.censys import CensysPlugin

        plugin = CensysPlugin(censys_id="id", censys_secret="secret")

        respx.get("https://search.censys.io/api/v2/hosts/10.0.0.1").mock(
            return_value=httpx.Response(404)
        )

        ioc = IOC(type=IOCType.ipv4, value="10.0.0.1")
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None
