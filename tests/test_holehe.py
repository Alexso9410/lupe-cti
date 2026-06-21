import pytest
import respx
import httpx
from lupe.enrichment.holehe import HolehePlugin
from lupe.models import IOC, IOCType, Severity
from lupe.enrichment import holehe


class TestHolehePlugin:
    @pytest.fixture
    def plugin(self):
        return HolehePlugin()

    @pytest.fixture
    def email_ioc(self):
        return IOC(type=IOCType.email, value="test@example.com")

    @respx.mock
    async def test_no_accounts_info_severity(self, plugin, email_ioc):
        """All sites respond negatively -> info severity"""
        # Mock all the sites to return "not found" responses
        for site in holehe._SITES:
            if "url" in site:
                pattern = site["url"].format(email=email_ioc.value)
            else:
                pattern = "/.*"

            if site["method"] == "POST":
                respx.post(pattern).mock(side_effect=Exception("timeout"))
            else:
                respx.get(pattern).mock(side_effect=Exception("timeout"))

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(email_ioc, client)
        assert result is not None
        assert result.severity == Severity.info
        assert "0 cuentas" in result.summary

    @respx.mock
    async def test_some_accounts_low_severity(self, plugin, email_ioc):
        """2-3 accounts found -> low severity"""
        orig = holehe._SITES
        # Create simplified test sites that always return found
        holehe._SITES = [
            {
                "name": "TestSite1",
                "url": "https://test1.example/check?email={email}",
                "method": "GET",
                "found_if": lambda r: True,
            },
            {
                "name": "TestSite2",
                "url": "https://test2.example/check?email={email}",
                "method": "GET",
                "found_if": lambda r: True,
            },
        ]

        respx.get("https://test1.example/check?email=test@example.com").mock(
            return_value=httpx.Response(200)
        )
        respx.get("https://test2.example/check?email=test@example.com").mock(
            return_value=httpx.Response(200)
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(email_ioc, client)
        assert result is not None
        assert result.severity == Severity.low

        holehe._SITES = orig

    @respx.mock
    async def test_many_accounts_medium_severity(self, plugin, email_ioc):
        """5+ accounts -> medium severity"""
        orig = holehe._SITES
        sites = []
        for i in range(7):
            sites.append(
                {
                    "name": f"Site{i}",
                    "url": f"https://site{i}.example/check?email={{email}}",
                    "method": "GET",
                    "found_if": lambda r: True,
                }
            )
            respx.get(
                f"https://site{i}.example/check?email=test@example.com"
            ).mock(return_value=httpx.Response(200))
        holehe._SITES = sites

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(email_ioc, client)
        assert result is not None
        assert result.severity == Severity.medium
        assert "+2 m\\u00e1s" in result.summary

        holehe._SITES = orig

    @respx.mock
    async def test_source_and_ioc(self, plugin, email_ioc):
        orig = holehe._SITES
        holehe._SITES = [
            {
                "name": "TestA",
                "url": "https://a.example?email={email}",
                "method": "GET",
                "found_if": lambda r: True,
            },
        ]
        respx.get("https://a.example?email=test@example.com").mock(
            return_value=httpx.Response(200)
        )

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(email_ioc, client)
        assert result.source == "holehe"
        assert result.ioc_value == "test@example.com"

        holehe._SITES = orig
