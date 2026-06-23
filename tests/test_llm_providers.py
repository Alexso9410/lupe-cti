"""Tests for LLM provider implementations using respx mocks."""

from __future__ import annotations

import httpx
import pytest
import respx

from lupe.config import Settings

# ---------------------------------------------------------------------------
# Ollama Provider Tests
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """OllamaProvider.generate returns model text on 200."""
        from lupe.llm.ollama import OllamaProvider

        respx.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Analysis: clean IP"}}]},
            )
        )

        settings = Settings(ollama_base_url="http://localhost:11434")
        provider = OllamaProvider(settings)
        result = await provider.generate("Analyze 8.8.8.8")
        assert result == "Analysis: clean IP"

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        """OllamaProvider.generate sends system prompt when provided."""
        from lupe.llm.ollama import OllamaProvider

        route = respx.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )

        settings = Settings(ollama_base_url="http://localhost:11434")
        provider = OllamaProvider(settings)
        await provider.generate("test", system="You are a CTI analyst")

        request = route.calls.last.request
        body = request.content.decode()
        assert "CTI analyst" in body

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_connect_error_returns_empty(self):
        """OllamaProvider.generate returns empty string on connection error."""
        from lupe.llm.ollama import OllamaProvider

        respx.post("http://localhost:11434/v1/chat/completions").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        settings = Settings(ollama_base_url="http://localhost:11434")
        provider = OllamaProvider(settings)
        result = await provider.generate("test")
        assert result == ""

    @pytest.mark.asyncio
    async def test_validate_key_returns_bool(self):
        """OllamaProvider.validate_key returns a bool (True if server reachable)."""
        from lupe.llm.ollama import OllamaProvider

        settings = Settings(ollama_base_url="http://localhost:11434")
        provider = OllamaProvider(settings)
        result = await provider.validate_key()
        assert isinstance(result, bool)  # True if Ollama running, False otherwise

    def test_list_models_returns_empty(self):
        """OllamaProvider.list_models returns a list (may be empty without server)."""
        from lupe.llm.ollama import OllamaProvider

        settings = Settings(ollama_base_url="http://localhost:11434")
        provider = OllamaProvider(settings)
        models = provider.list_models()
        assert isinstance(models, list)


# ---------------------------------------------------------------------------
# OpenAI Provider Tests
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """OpenAIProvider.generate returns text on 200."""
        from lupe.llm.openai import OpenAIProvider

        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Risk: 2/10 — benign IP"}}]},
            )
        )

        settings = Settings(openai_api_key="sk-test1234567890abcdef")
        provider = OpenAIProvider(settings)
        result = await provider.generate("Analyze 8.8.8.8")
        assert "benign IP" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_sends_auth_header(self):
        """OpenAIProvider sends Authorization: Bearer header."""
        from lupe.llm.openai import OpenAIProvider

        route = respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )

        settings = Settings(openai_api_key="sk-mykey1234567890")
        provider = OpenAIProvider(settings)
        await provider.generate("test")

        request = route.calls.last.request
        auth = request.headers.get("authorization", "")
        assert auth == "Bearer sk-mykey1234567890"

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_returns_empty_on_error(self):
        """OpenAIProvider.generate returns empty string on HTTP error."""
        from lupe.llm.openai import OpenAIProvider

        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        settings = Settings(openai_api_key="sk-badkey1234567890")
        provider = OpenAIProvider(settings)
        result = await provider.generate("test")
        assert result == ""

    @pytest.mark.asyncio
    async def test_validate_key_true_for_valid_format(self):
        """OpenAIProvider.validate_key returns True for sk-... format."""
        from lupe.llm.openai import OpenAIProvider

        settings = Settings(openai_api_key="sk-test1234567890abcdef")
        provider = OpenAIProvider(settings)
        assert await provider.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_false_for_invalid_format(self):
        """OpenAIProvider.validate_key returns False for non-sk- format."""
        from lupe.llm.openai import OpenAIProvider

        settings = Settings(openai_api_key="invalid-key-format")
        provider = OpenAIProvider(settings)
        assert await provider.validate_key() is False


# ---------------------------------------------------------------------------
# Anthropic Provider Tests
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """AnthropicProvider.generate returns text on 200."""
        from lupe.llm.anthropic import AnthropicProvider

        respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(
                200,
                json={
                    "content": [{"text": "Risk analysis complete"}],
                    "model": "claude-3-5-sonnet-20241022",
                },
            )
        )

        settings = Settings(anthropic_api_key="sk-ant-test1234567890abcdef")
        provider = AnthropicProvider(settings)
        result = await provider.generate("Analyze 8.8.8.8")
        assert "Risk analysis complete" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_uses_messages_format(self):
        """AnthropicProvider sends messages format (not chat completions)."""
        from lupe.llm.anthropic import AnthropicProvider

        route = respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(
                200,
                json={"content": [{"text": "ok"}], "model": "claude-3-5-sonnet-20241022"},
            )
        )

        settings = Settings(anthropic_api_key="sk-ant-test1234567890abcdef")
        provider = AnthropicProvider(settings)
        await provider.generate("test", system="Be concise")

        request = route.calls.last.request
        body = request.content.decode()
        assert '"messages"' in body
        assert '"system"' in body

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_sends_x_api_key_header(self):
        """AnthropicProvider sends x-api-key header."""
        from lupe.llm.anthropic import AnthropicProvider

        route = respx.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(
                200,
                json={"content": [{"text": "ok"}], "model": "claude-3-5-sonnet-20241022"},
            )
        )

        settings = Settings(anthropic_api_key="sk-ant-mykey1234567890")
        provider = AnthropicProvider(settings)
        await provider.generate("test")

        request = route.calls.last.request
        assert request.headers.get("x-api-key") == "sk-ant-mykey1234567890"

    @pytest.mark.asyncio
    async def test_validate_key_true_for_valid_format(self):
        """AnthropicProvider.validate_key returns True for sk-ant-... format."""
        from lupe.llm.anthropic import AnthropicProvider

        settings = Settings(anthropic_api_key="sk-ant-test1234567890abcdef")
        provider = AnthropicProvider(settings)
        assert await provider.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_false_for_invalid_format(self):
        """AnthropicProvider.validate_key returns False for non-sk-ant- format."""
        from lupe.llm.anthropic import AnthropicProvider

        settings = Settings(anthropic_api_key="invalid-key")
        provider = AnthropicProvider(settings)
        assert await provider.validate_key() is False


# ---------------------------------------------------------------------------
# OpenRouter Provider Tests
# ---------------------------------------------------------------------------


class TestOpenRouterProvider:
    """Tests for OpenRouterProvider (OpenAI-compatible endpoint)."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """OpenRouterProvider.generate returns text on 200."""
        from lupe.llm.openrouter import OpenRouterProvider

        respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "Analysis via OpenRouter"}}]},
            )
        )

        settings = Settings(openrouter_api_key="sk-or-test1234567890abcdef")
        provider = OpenRouterProvider(settings)
        result = await provider.generate("Analyze 8.8.8.8")
        assert "OpenRouter" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_uses_openai_compatible_endpoint(self):
        """OpenRouterProvider uses openrouter.ai/api/v1/chat/completions."""
        from lupe.llm.openrouter import OpenRouterProvider

        route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )

        settings = Settings(openrouter_api_key="sk-or-test1234567890abcdef")
        provider = OpenRouterProvider(settings)
        await provider.generate("test")

        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_sends_bearer_auth(self):
        """OpenRouterProvider sends Authorization: Bearer header."""
        from lupe.llm.openrouter import OpenRouterProvider

        route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
            )
        )

        settings = Settings(openrouter_api_key="sk-or-mykey1234567890")
        provider = OpenRouterProvider(settings)
        await provider.generate("test")

        request = route.calls.last.request
        auth = request.headers.get("authorization", "")
        assert auth == "Bearer sk-or-mykey1234567890"

    @pytest.mark.asyncio
    async def test_validate_key_true_for_valid_format(self):
        """OpenRouterProvider.validate_key returns True for sk-or-... format."""
        from lupe.llm.openrouter import OpenRouterProvider

        settings = Settings(openrouter_api_key="sk-or-test1234567890abcdef")
        provider = OpenRouterProvider(settings)
        assert await provider.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_false_for_invalid_format(self):
        """OpenRouterProvider.validate_key returns False for non-sk-or- format."""
        from lupe.llm.openrouter import OpenRouterProvider

        settings = Settings(openrouter_api_key="invalid-key")
        provider = OpenRouterProvider(settings)
        assert await provider.validate_key() is False


# ---------------------------------------------------------------------------
# Null Provider Tests
# ---------------------------------------------------------------------------


class TestNullProvider:
    """Tests for NullProvider (fallback when no provider configured)."""

    @pytest.mark.asyncio
    async def test_generate_returns_empty(self):
        """NullProvider.generate returns empty string."""
        from lupe.llm.null import NullProvider

        provider = NullProvider()
        result = await provider.generate("test")
        assert result == ""

    @pytest.mark.asyncio
    async def test_validate_key_returns_false(self):
        """NullProvider.validate_key returns False."""
        from lupe.llm.null import NullProvider

        provider = NullProvider()
        assert await provider.validate_key() is False

    def test_list_models_returns_empty(self):
        """NullProvider.list_models returns empty list."""
        from lupe.llm.null import NullProvider

        provider = NullProvider()
        assert provider.list_models() == []

    def test_name_is_null(self):
        """NullProvider.name is 'null'."""
        from lupe.llm.null import NullProvider

        provider = NullProvider()
        assert provider.name == "null"
