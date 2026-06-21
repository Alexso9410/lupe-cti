"""Tests for MISP client and CLI commands."""

from __future__ import annotations

import httpx
import pytest
import respx


class TestMISPClient:
    """Tests for MISPClient class."""

    def test_client_instantiates(self):
        """MISPClient can be instantiated with URL and key."""
        from lupe.integrations.misp import MISPClient

        client = MISPClient(url="https://misp.example.com", api_key="test-key")
        assert client is not None
        assert client._base_url == "https://misp.example.com"

    def test_client_strips_trailing_slash(self):
        """MISPClient strips trailing slash from URL."""
        from lupe.integrations.misp import MISPClient

        client = MISPClient(url="https://misp.example.com/", api_key="key")
        assert client._base_url == "https://misp.example.com"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_indicators_returns_list(self):
        """get_indicators returns a list of IOC dicts."""
        from lupe.integrations.misp import MISPClient

        respx.post("https://misp.example.com/attributes/restSearch").mock(
            return_value=httpx.Response(
                200,
                json={
                    "response": {
                        "Attribute": [
                            {
                                "uuid": "abc-123",
                                "type": "ip-dst",
                                "value": "8.8.8.8",
                                "timestamp": "1700000000",
                            }
                        ]
                    }
                },
            )
        )

        client = MISPClient(url="https://misp.example.com", api_key="test-key")
        indicators = await client.get_indicators()
        assert isinstance(indicators, list)
        assert len(indicators) == 1
        assert indicators[0]["value"] == "8.8.8.8"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_indicators_with_tag_filter(self):
        """get_indicators sends tag filter in request body."""
        from lupe.integrations.misp import MISPClient

        route = respx.post("https://misp.example.com/attributes/restSearch").mock(
            return_value=httpx.Response(200, json={"response": {"Attribute": []}}),
        )

        client = MISPClient(url="https://misp.example.com", api_key="test-key")
        await client.get_indicators(tags=["osint"], days=7)

        request = route.calls.last.request
        body = request.content.decode()
        assert "osint" in body

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_indicators_auth_error(self):
        """get_indicators raises MISPAuthError on 401."""
        from lupe.integrations.misp import MISPAuthError, MISPClient

        respx.post("https://misp.example.com/attributes/restSearch").mock(
            return_value=httpx.Response(401, json={"message": "Unauthorized"}),
        )

        client = MISPClient(url="https://misp.example.com", api_key="bad-key")
        with pytest.raises(MISPAuthError):
            await client.get_indicators()

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_indicator_returns_uuid(self):
        """add_indicator returns the UUID of the created attribute."""
        from lupe.integrations.misp import MISPClient

        respx.post("https://misp.example.com/events").mock(
            return_value=httpx.Response(
                200,
                json={"Event": {"uuid": "event-uuid-123"}},
            )
        )
        respx.post("https://misp.example.com/attributes/add/").mock(
            return_value=httpx.Response(
                200,
                json={"Attribute": {"uuid": "attr-uuid-456"}},
            )
        )

        client = MISPClient(url="https://misp.example.com", api_key="test-key")
        uuid = await client.add_indicator(
            {"type": "ip-dst", "value": "8.8.8.8", "category": "Network activity"}
        )
        assert uuid == "attr-uuid-456"

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """get_indicators raises MISPConnectionError on timeout."""
        from lupe.integrations.misp import MISPClient, MISPConnectionError

        respx.post("https://misp.example.com/attributes/restSearch").mock(
            side_effect=httpx.ConnectError("Timeout")
        )

        client = MISPClient(url="https://misp.example.com", api_key="test-key")
        with pytest.raises(MISPConnectionError):
            await client.get_indicators()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """MISPClient works as async context manager."""
        from lupe.integrations.misp import MISPClient

        async with MISPClient(url="https://misp.example.com", api_key="key") as client:
            assert client is not None


class TestMISPCLI:
    """Tests for MISP CLI commands."""

    def test_misp_pull_help(self):
        """lupe misp pull --help works."""
        from typer.testing import CliRunner

        from lupe.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["misp", "pull", "--help"])
        assert result.exit_code == 0

    def test_misp_push_help(self):
        """lupe misp push --help works."""
        from typer.testing import CliRunner

        from lupe.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["misp", "push", "--help"])
        assert result.exit_code == 0

    def test_misp_pull_no_config_shows_error(self):
        """lupe misp pull shows error when MISP not configured."""
        from typer.testing import CliRunner

        from lupe.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["misp", "pull"])
        # Should fail with clear error about missing config
        assert result.exit_code != 0 or "MISP" in result.output or "misp" in result.output.lower()
