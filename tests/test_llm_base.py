"""Tests for LLM provider ABC, registry, factory, and analysis integration."""

from __future__ import annotations

import pytest

from lupe.llm.base import LLMProvider, ModelInfo


class TestLLMBase:
    """Tests for the LLMProvider abstract base class."""

    def test_abc_cannot_instantiate(self):
        """LLMProvider is abstract — direct instantiation must raise TypeError."""
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore[abstract]

    def test_model_info_dataclass(self):
        """ModelInfo is a frozen dataclass with expected fields."""
        m = ModelInfo(name="gpt-4", size="large", family="gpt")
        assert m.name == "gpt-4"
        assert m.size == "large"
        assert m.family == "gpt"

    def test_model_info_defaults(self):
        """ModelInfo size and family default to None."""
        m = ModelInfo(name="test-model")
        assert m.size is None
        assert m.family is None


class TestLLMRegistry:
    """Tests for the provider registry and get_provider factory."""

    def test_registry_factory_returns_ollama(self, monkeypatch):
        """get_provider('ollama', settings) returns an OllamaProvider instance."""
        from lupe.config import Settings
        from lupe.llm.registry import get_provider

        # Ensure no API keys interfere
        monkeypatch.delenv("LUPE_LLM_PROVIDER", raising=False)
        settings = Settings(
            ollama_base_url="http://localhost:11434",
            ollama_model="test-model",
        )
        provider = get_provider("ollama", settings)
        assert provider is not None
        assert provider.name == "ollama"

    def test_registry_factory_returns_null_for_unknown(self, monkeypatch):
        """get_provider('unknown', settings) returns a NullProvider."""
        from lupe.config import Settings
        from lupe.llm.registry import get_provider

        settings = Settings()
        provider = get_provider("unknown", settings)
        assert provider is not None
        assert provider.name == "null"

    def test_registry_factory_returns_null_for_empty(self, monkeypatch):
        """get_provider('', settings) returns a NullProvider."""
        from lupe.config import Settings
        from lupe.llm.registry import get_provider

        settings = Settings()
        provider = get_provider("", settings)
        assert provider is not None
        assert provider.name == "null"

    def test_registry_factory_returns_openai(self, monkeypatch):
        """get_provider('openai', settings) returns OpenAIProvider."""
        from lupe.config import Settings
        from lupe.llm.registry import get_provider

        settings = Settings(openai_api_key="sk-test1234567890")
        provider = get_provider("openai", settings)
        assert provider is not None
        assert provider.name == "openai"

    def test_registry_factory_returns_anthropic(self, monkeypatch):
        """get_provider('anthropic', settings) returns AnthropicProvider."""
        from lupe.config import Settings
        from lupe.llm.registry import get_provider

        settings = Settings(anthropic_api_key="sk-ant-test1234567890")
        provider = get_provider("anthropic", settings)
        assert provider is not None
        assert provider.name == "anthropic"

    def test_registry_factory_returns_openrouter(self, monkeypatch):
        """get_provider('openrouter', settings) returns OpenRouterProvider."""
        from lupe.config import Settings
        from lupe.llm.registry import get_provider

        settings = Settings(openrouter_api_key="sk-or-test1234567890")
        provider = get_provider("openrouter", settings)
        assert provider is not None
        assert provider.name == "openrouter"


class TestAnalysisDelegation:
    """Tests for analyze_ioc delegating to LLMProvider."""

    @pytest.mark.asyncio
    async def test_analysis_returns_none_when_no_enrichments(self):
        """analyze_ioc returns None when enrichment list is empty."""
        from lupe.analysis import analyze_ioc
        from lupe.config import Settings
        from lupe.models import IOC, IOCType

        ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        settings = Settings()
        result = await analyze_ioc(ioc, [], settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_analysis_delegates_to_provider(self, monkeypatch):
        """analyze_ioc uses the configured LLM provider."""
        from datetime import datetime

        from lupe.analysis import analyze_ioc
        from lupe.config import Settings
        from lupe.models import IOC, EnrichmentResult, IOCType, Severity

        ioc = IOC(type=IOCType.ipv4, value="8.8.8.8")
        enrichments = [
            EnrichmentResult(
                source="test",
                ioc_value="8.8.8.8",
                severity=Severity.low,
                summary="Clean IP",
                raw_data={},
                enriched_at=datetime.now(),
            )
        ]
        # With empty llm_provider, should return None (NullProvider)
        settings = Settings(llm_provider="")
        result = await analyze_ioc(ioc, enrichments, settings)
        assert result is None
