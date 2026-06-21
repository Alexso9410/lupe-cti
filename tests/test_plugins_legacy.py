"""Tests for legacy enrichment plugins without coverage (PR-0, Task 0.2)."""

from __future__ import annotations

import httpx
import pytest
import respx

from lupe.enrichment.ipinfo import IpInfoPlugin
from lupe.enrichment.malwarebazaar import MalwareBazaarPlugin
from lupe.enrichment.threatfox import ThreatFoxPlugin
from lupe.enrichment.urlhaus import URLhausPlugin
from lupe.enrichment.whois_plugin import WhoisPlugin
from lupe.models import IOC, IOCType, Severity


class TestWhoisPlugin:
    """Tests for WhoisPlugin — domain WHOIS lookup."""

    def test_plugin_metadata(self) -> None:
        plugin = WhoisPlugin()
        assert plugin.name == "whois"
        assert IOCType.domain in plugin.supported_ioc_types
        assert plugin.requires_api_key is False

    def test_supports_domain_and_ipv4(self) -> None:
        plugin = WhoisPlugin()
        assert plugin.supports(IOCType.domain) is True
        assert plugin.supports(IOCType.ipv4) is True
        assert plugin.supports(IOCType.url) is False

    @pytest.mark.asyncio
    async def test_enrich_domain_returns_without_crash(self) -> None:
        plugin = WhoisPlugin()
        ioc = IOC(type=IOCType.domain, value="example.com")
        # WhoisPlugin uses python-whois library (not httpx for the lookup).
        # The important thing is it doesn't raise unhandled exceptions.
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        # May return None or EnrichmentResult depending on python-whois availability
        assert result is None or result.source == "whois"


class TestIpInfoPlugin:
    """Tests for IpInfoPlugin — IP geolocation via ipinfo.io."""

    def test_plugin_metadata(self) -> None:
        plugin = IpInfoPlugin()
        assert plugin.name == "ipinfo"
        assert IOCType.ipv4 in plugin.supported_ioc_types
        assert IOCType.ipv6 in plugin.supported_ioc_types
        assert plugin.requires_api_key is False

    def test_supports_ipv4_and_ipv6(self) -> None:
        plugin = IpInfoPlugin()
        assert plugin.supports(IOCType.ipv4) is True
        assert plugin.supports(IOCType.ipv6) is True
        assert plugin.supports(IOCType.domain) is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_ipv4_success(self) -> None:
        plugin = IpInfoPlugin()
        ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")

        respx.get("https://ipinfo.io/8.8.8.8/json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "ip": "8.8.8.8",
                    "hostname": "dns.google",
                    "city": "Mountain View",
                    "region": "California",
                    "country": "US",
                    "org": "AS15169 Google LLC",
                },
            )
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "ipinfo"
        assert result.ioc_value == "8.8.8.8"
        assert result.severity == Severity.info
        assert "Google" in result.summary or "US" in result.summary

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_ipv4_rate_limited(self) -> None:
        plugin = IpInfoPlugin()
        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")

        respx.get("https://ipinfo.io/1.2.3.4/json").mock(return_value=httpx.Response(429))

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        # IpInfoPlugin returns a result on 429 with rate limit message
        assert result is not None
        assert "rate" in result.summary.lower()
        assert result.severity == Severity.info

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_ipv4_server_error_returns_none(self) -> None:
        plugin = IpInfoPlugin()
        ioc = IOC(type=IOCType.ipv4, value="1.2.3.4")

        respx.get("https://ipinfo.io/1.2.3.4/json").mock(return_value=httpx.Response(500))

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None


class TestThreatFoxPlugin:
    """Tests for ThreatFoxPlugin — IOC reputation from abuse.ch."""

    def test_plugin_metadata(self) -> None:
        plugin = ThreatFoxPlugin()
        assert plugin.name == "threatfox"
        assert IOCType.ipv4 in plugin.supported_ioc_types
        assert IOCType.domain in plugin.supported_ioc_types
        assert IOCType.url in plugin.supported_ioc_types
        assert IOCType.hash_md5 in plugin.supported_ioc_types
        assert plugin.requires_api_key is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_ioc_found(self) -> None:
        plugin = ThreatFoxPlugin()
        ioc = IOC(type=IOCType.ipv4, value="45.142.212.100")

        respx.post("https://threatfox-api.abuse.ch/api/v1/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "query_status": "ok",
                    "data": [
                        {
                            "id": "12345",
                            "threat_type": "botnet_cc",
                            "threat_type_desc": "Botnet C&C",
                            "ioc_type": "ip:port",
                            "ioc": "45.142.212.100:443",
                            "malware": "Win.Trojan.Generic",
                            "malware_alias": "Generic",
                            "malware_printable": "Generic Trojan",
                            "first_seen": "2024-01-01 00:00:00",
                            "last_seen": "2024-06-01 00:00:00",
                            "confidence_level": 100,
                            "reference": "",
                            "tags": [{"tag": "botnet"}],
                        }
                    ],
                },
            )
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "threatfox"
        assert result.severity == Severity.critical
        assert "Generic Trojan" in result.summary

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_ioc_not_found(self) -> None:
        plugin = ThreatFoxPlugin()
        ioc = IOC(type=IOCType.ipv4, value="1.1.1.1")

        respx.post("https://threatfox-api.abuse.ch/api/v1/").mock(
            return_value=httpx.Response(
                200,
                json={"query_status": "no_result", "data": []},
            )
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None


class TestURLhausPlugin:
    """Tests for URLhausPlugin — URL/domain reputation from abuse.ch."""

    def test_plugin_metadata(self) -> None:
        plugin = URLhausPlugin()
        assert plugin.name == "urlhaus"
        assert IOCType.url in plugin.supported_ioc_types
        assert IOCType.domain in plugin.supported_ioc_types
        assert plugin.requires_api_key is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_url_found(self) -> None:
        plugin = URLhausPlugin()
        ioc = IOC(type=IOCType.url, value="http://evil.com/malware.exe")

        respx.post("https://urlhaus-api.abuse.ch/v1/url/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "query_status": "is_url",
                    "id": "12345",
                    "url": "http://evil.com/malware.exe",
                    "url_status": "online",
                    "threat": "malware_download",
                    "date_added": "2024-01-01 00:00:00",
                    "tags": ["elf", "mirai"],
                },
            )
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "urlhaus"
        assert result.severity == Severity.critical  # online = critical

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_domain_found(self) -> None:
        plugin = URLhausPlugin()
        ioc = IOC(type=IOCType.domain, value="evil.com")

        respx.post("https://urlhaus-api.abuse.ch/v1/host/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "query_status": "is_host",
                    "urls_count": 5,
                    "tags": ["malware"],
                    "payloads": [],
                },
            )
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "urlhaus"
        assert result.severity == Severity.high  # urls_count > 0


class TestMalwareBazaarPlugin:
    """Tests for MalwareBazaarPlugin — hash lookup from abuse.ch."""

    def test_plugin_metadata(self) -> None:
        plugin = MalwareBazaarPlugin()
        assert plugin.name == "malwarebazaar"
        assert IOCType.hash_sha256 in plugin.supported_ioc_types
        assert IOCType.hash_md5 in plugin.supported_ioc_types
        assert IOCType.hash_sha1 in plugin.supported_ioc_types
        assert plugin.requires_api_key is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_hash_found(self) -> None:
        plugin = MalwareBazaarPlugin()
        ioc = IOC(
            type=IOCType.hash_sha256,
            value="275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f",
        )

        respx.post("https://mb-api.abuse.ch/api/v1/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "query_status": "ok",
                    "data": [
                        {
                            "sha256_hash": (
                                "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
                            ),
                            "sha1_hash": "3395856ce81f2b7382dee72602f798b642f14d40",
                            "md5_hash": "44d88612fea8a8f36de82e1278abb02f",
                            "file_type": "exe",
                            "file_size": 123456,
                            "signature": "Trojan.Generic",
                            "tags": ["exe", "trojan"],
                            "first_seen": "2024-01-01",
                            "intelligence": {"clamav": []},
                        }
                    ],
                },
            )
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "malwarebazaar"
        assert result.severity == Severity.critical  # has signature
        assert "Trojan.Generic" in result.summary

    @respx.mock
    @pytest.mark.asyncio
    async def test_enrich_hash_not_found(self) -> None:
        plugin = MalwareBazaarPlugin()
        ioc = IOC(
            type=IOCType.hash_sha256,
            value="a" * 64,
        )

        respx.post("https://mb-api.abuse.ch/api/v1/").mock(
            return_value=httpx.Response(
                200,
                json={"query_status": "hash_not_found", "data": []},
            )
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None
