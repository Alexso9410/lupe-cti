"""Tests for GeminiProvider using respx mocks (strict TDD — RED phase)."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from lupe.config import Settings

# Gemini API base for convenience
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class TestGeminiProviderGenerate:
    """Tests for GeminiProvider.generate()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_flash_model(self):
        """GeminiProvider.generate returns text with gemini-2.5-flash."""
        from lupe.llm.gemini import GeminiProvider

        respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-flash:generateContent"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Risk: low — benign IP"}],
                                "role": "model",
                            }
                        }
                    ]
                },
            )
        )

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)
        result = await provider.generate("Analyze 8.8.8.8")
        assert "benign IP" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_pro_model(self):
        """GeminiProvider.generate returns text with gemini-2.5-pro."""
        from lupe.llm.gemini import GeminiProvider

        respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-pro:generateContent"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [{"text": "Deep analysis complete"}],
                                "role": "model",
                            }
                        }
                    ]
                },
            )
        )

        settings = Settings(
            gemini_api_key="AIzaSyTestKey1234567890abcdef",
            gemini_model="gemini-2.5-pro",
        )
        provider = GeminiProvider(settings)
        result = await provider.generate("Analyze malware sample")
        assert "Deep analysis" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_sends_api_key_header(self):
        """GeminiProvider sends x-goog-api-key header."""
        from lupe.llm.gemini import GeminiProvider

        route = respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-flash:generateContent"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "candidates": [
                        {"content": {"parts": [{"text": "ok"}], "role": "model"}}
                    ]
                },
            )
        )

        settings = Settings(gemini_api_key="AIzaSyMyKey1234567890")
        provider = GeminiProvider(settings)
        await provider.generate("test")

        request = route.calls.last.request
        assert request.headers.get("x-goog-api-key") == "AIzaSyMyKey1234567890"

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_sends_contents_format(self):
        """GeminiProvider sends Google contents/parts payload, not OpenAI messages."""
        from lupe.llm.gemini import GeminiProvider

        route = respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-flash:generateContent"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "candidates": [
                        {"content": {"parts": [{"text": "ok"}], "role": "model"}}
                    ]
                },
            )
        )

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)
        await provider.generate("Analyze this IP", system="You are a CTI analyst")

        request = route.calls.last.request
        body = json.loads(request.content)

        # Must use contents array, not messages
        assert "contents" in body
        assert body["contents"][0]["role"] == "user"
        assert body["contents"][0]["parts"][0]["text"] == "Analyze this IP"

        # System instruction goes at top level
        assert "systemInstruction" in body
        assert body["systemInstruction"]["parts"][0]["text"] == "You are a CTI analyst"

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_connect_error_returns_empty(self):
        """GeminiProvider.generate returns '' on connection error."""
        from lupe.llm.gemini import GeminiProvider

        respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-flash:generateContent"
        ).mock(side_effect=httpx.ConnectError("Connection refused"))

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)
        result = await provider.generate("test")
        assert result == ""

    @respx.mock
    @pytest.mark.asyncio
    async def test_generate_http_error_returns_empty(self):
        """GeminiProvider.generate returns '' on non-200 status."""
        from lupe.llm.gemini import GeminiProvider

        respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-flash:generateContent"
        ).mock(
            return_value=httpx.Response(403, json={"error": "Forbidden"})
        )

        settings = Settings(gemini_api_key="AIzaSyBadKey1234567890")
        provider = GeminiProvider(settings)
        result = await provider.generate("test")
        assert result == ""


class TestGeminiProviderValidateKey:
    """Tests for GeminiProvider.validate_key()."""

    @pytest.mark.asyncio
    async def test_validate_key_true_for_aiza_prefix(self):
        """validate_key returns True for keys starting with AIza."""
        from lupe.llm.gemini import GeminiProvider

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)
        assert await provider.validate_key() is True

    @pytest.mark.asyncio
    async def test_validate_key_false_for_invalid_format(self):
        """validate_key returns False for keys not matching Gemini format."""
        from lupe.llm.gemini import GeminiProvider

        settings = Settings(gemini_api_key="invalid-key-format")
        provider = GeminiProvider(settings)
        assert await provider.validate_key() is False

    @pytest.mark.asyncio
    async def test_validate_key_false_for_empty_key(self):
        """validate_key returns False when key is empty."""
        from lupe.llm.gemini import GeminiProvider

        settings = Settings(gemini_api_key="")
        provider = GeminiProvider(settings)
        assert await provider.validate_key() is False

    @pytest.mark.asyncio
    async def test_validate_key_false_for_none_key(self):
        """validate_key returns False when key is None."""
        from lupe.llm.gemini import GeminiProvider

        settings = Settings(gemini_api_key=None)
        provider = GeminiProvider(settings)
        assert await provider.validate_key() is False


class TestGeminiProviderListModels:
    """Tests for GeminiProvider.list_models()."""

    def test_list_models_returns_flash_and_pro(self):
        """list_models returns gemini-2.5-flash and gemini-2.5-pro."""
        from lupe.llm.gemini import GeminiProvider

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)
        models = provider.list_models()

        names = [m.name for m in models]
        assert "gemini-2.5-flash" in names
        assert "gemini-2.5-pro" in names

    def test_list_models_returns_model_info(self):
        """list_models returns ModelInfo instances with family='gemini'."""
        from lupe.llm.base import ModelInfo
        from lupe.llm.gemini import GeminiProvider

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)
        models = provider.list_models()

        for m in models:
            assert isinstance(m, ModelInfo)
            assert m.family == "gemini"


class TestGeminiProviderStream:
    """Tests for GeminiProvider.stream()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self):
        """GeminiProvider.stream yields text chunks from SSE responses."""
        from lupe.llm.gemini import GeminiProvider

        # Gemini streaming format: each line is "data: {json}\n\n"
        chunk1 = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "Hello "}]}}]}
        )
        chunk2 = json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "world"}]}}]}
        )
        sse_body = f"data: {chunk1}\n\ndata: {chunk2}\n\n"

        respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-flash:streamGenerateContent"
        ).mock(
            return_value=httpx.Response(
                200,
                text=sse_body,
                headers={"content-type": "text/event-stream"},
            )
        )

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)

        chunks = []
        async for chunk in provider.stream("test"):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello world"

    @respx.mock
    @pytest.mark.asyncio
    async def test_stream_connect_error_yields_nothing(self):
        """GeminiProvider.stream yields nothing on connection error."""
        from lupe.llm.gemini import GeminiProvider

        respx.post(
            f"{_GEMINI_BASE}/gemini-2.5-flash:streamGenerateContent"
        ).mock(side_effect=httpx.ConnectError("Connection refused"))

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)

        chunks = []
        async for chunk in provider.stream("test"):
            chunks.append(chunk)

        assert chunks == []


class TestGeminiProviderRegistration:
    """Tests that Gemini provider is registered in the registry."""

    def test_gemini_registered_in_registry(self):
        """get_provider('gemini', settings) returns a GeminiProvider."""
        from lupe.llm.gemini import GeminiProvider
        from lupe.llm.registry import get_provider

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = get_provider("gemini", settings)
        assert isinstance(provider, GeminiProvider)

    def test_gemini_name_is_gemini(self):
        """GeminiProvider.name is 'gemini'."""
        from lupe.llm.gemini import GeminiProvider

        settings = Settings(gemini_api_key="AIzaSyTestKey1234567890abcdef")
        provider = GeminiProvider(settings)
        assert provider.name == "gemini"
