import pytest
import respx
import httpx
from centinela.enrichment.emailrep import EmailRepPlugin
from centinela.models import IOC, IOCType, Severity


class TestEmailRepPlugin:
    @pytest.fixture
    def plugin_no_key(self):
        return EmailRepPlugin()

    @pytest.fixture
    def plugin_with_key(self):
        return EmailRepPlugin(api_key="test-key-123")

    @pytest.fixture
    def email_ioc(self):
        return IOC(type=IOCType.email, value="test@example.com")

    @respx.mock
    async def test_high_risk_suspicious_leaked(self, plugin_no_key, email_ioc):
        respx.get("https://emailrep.io/test@example.com").mock(
            return_value=httpx.Response(
                200,
                json={
                    "email": "test@example.com",
                    "reputation": "low",
                    "suspicious": True,
                    "references": 15,
                    "details": {
                        "credentials_leaked": True,
                        "data_breach": True,
                        "spam_lists": True,
                        "free_provider": False,
                        "disposable": False,
                        "profiles": ["twitter"],
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin_no_key.enrich(email_ioc, client)
        assert result is not None
        assert result.severity == Severity.high
        assert "suspicious=True" in result.summary
        assert "leaked=True" in result.summary

    @respx.mock
    async def test_medium_suspicious_no_leak(self, plugin_no_key, email_ioc):
        respx.get("https://emailrep.io/test@example.com").mock(
            return_value=httpx.Response(
                200,
                json={
                    "email": "test@example.com",
                    "reputation": "medium",
                    "suspicious": True,
                    "references": 5,
                    "details": {
                        "credentials_leaked": False,
                        "data_breach": False,
                        "spam_lists": False,
                        "free_provider": True,
                        "disposable": False,
                        "profiles": [],
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin_no_key.enrich(email_ioc, client)
        assert result.severity == Severity.medium

    @respx.mock
    async def test_low_data_breach(self, plugin_no_key, email_ioc):
        respx.get("https://emailrep.io/test@example.com").mock(
            return_value=httpx.Response(
                200,
                json={
                    "email": "test@example.com",
                    "reputation": "medium",
                    "suspicious": False,
                    "references": 3,
                    "details": {
                        "credentials_leaked": False,
                        "data_breach": True,
                        "spam_lists": False,
                        "free_provider": True,
                        "disposable": False,
                        "profiles": ["facebook"],
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin_no_key.enrich(email_ioc, client)
        assert result.severity == Severity.low

    @respx.mock
    async def test_info_clean_email(self, plugin_no_key, email_ioc):
        respx.get("https://emailrep.io/test@example.com").mock(
            return_value=httpx.Response(
                200,
                json={
                    "email": "test@example.com",
                    "reputation": "high",
                    "suspicious": False,
                    "references": 0,
                    "details": {
                        "credentials_leaked": False,
                        "data_breach": False,
                        "spam_lists": False,
                        "free_provider": False,
                        "disposable": False,
                        "profiles": ["linkedin"],
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin_no_key.enrich(email_ioc, client)
        assert result.severity == Severity.info

    @respx.mock
    async def test_returns_none_on_500(self, plugin_no_key, email_ioc):
        respx.get("https://emailrep.io/test@example.com").mock(
            return_value=httpx.Response(500)
        )
        async with httpx.AsyncClient() as client:
            result = await plugin_no_key.enrich(email_ioc, client)
        assert result is None

    @respx.mock
    async def test_uses_api_key_header(self, plugin_with_key, email_ioc):
        route = respx.get("https://emailrep.io/test@example.com").mock(
            return_value=httpx.Response(
                200,
                json={
                    "email": "test@example.com",
                    "reputation": "high",
                    "suspicious": False,
                    "references": 0,
                    "details": {
                        "credentials_leaked": False,
                        "data_breach": False,
                        "spam_lists": False,
                        "free_provider": True,
                        "disposable": False,
                        "profiles": [],
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin_with_key.enrich(email_ioc, client)
        assert result is not None
        # Verify the Key header was sent
        req = route.calls[0].request
        assert "key" in req.headers
        assert req.headers["key"] == "test-key-123"

    @respx.mock
    async def test_no_key_header_when_no_key(self, plugin_no_key, email_ioc):
        route = respx.get("https://emailrep.io/test@example.com").mock(
            return_value=httpx.Response(
                200,
                json={
                    "email": "test@example.com",
                    "reputation": "high",
                    "suspicious": False,
                    "references": 0,
                    "details": {
                        "credentials_leaked": False,
                        "data_breach": False,
                        "spam_lists": False,
                        "free_provider": False,
                        "disposable": False,
                        "profiles": [],
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await plugin_no_key.enrich(email_ioc, client)
        assert result is not None
        req = route.calls[0].request
        assert "key" not in req.headers
