"""Tests for lupe.security — redaction, validation, HTTPS-only, rate limiting."""

from __future__ import annotations

import asyncio

import pytest


class TestRedactSecrets:
    """Task 16.1 — redact_secrets replaces sensitive values."""

    def test_redact_sk_key(self) -> None:
        from lupe.security.redact import redact_secrets

        result = redact_secrets("key=sk-abc123def456ghij789")
        assert "sk-abc123def456ghij789" not in result
        assert "***" in result

    def test_redact_bearer_token(self) -> None:
        from lupe.security.redact import redact_secrets

        result = redact_secrets("Authorization: Bearer my-secret-token-12345")
        assert "my-secret-token-12345" not in result
        assert "***" in result

    def test_redact_api_key_param(self) -> None:
        from lupe.security.redact import redact_secrets

        result = redact_secrets("api_key=supersecretvalue123")
        assert "supersecretvalue123" not in result

    def test_redact_preserves_non_secret_text(self) -> None:
        from lupe.security.redact import redact_secrets

        text = "Connecting to https://api.example.com with key=sk-abc1234567890abcdef"
        result = redact_secrets(text)
        assert "https://api.example.com" in result
        assert "sk-abc1234567890abcdef" not in result

    def test_redact_empty_string(self) -> None:
        from lupe.security.redact import redact_secrets

        assert redact_secrets("") == ""

    def test_redact_no_secrets_unchanged(self) -> None:
        from lupe.security.redact import redact_secrets

        text = "Normal log message with no secrets"
        assert redact_secrets(text) == text

    def test_redact_multiple_secrets(self) -> None:
        from lupe.security.redact import redact_secrets

        text = "key=sk-aaaabbbbccccdddd btoken=Bearer eeeeffffgggghhhh"
        result = redact_secrets(text)
        assert "sk-aaaabbbbccccdddd" not in result
        assert "eeeeffffgggghhhh" not in result


class TestValidateIOC:
    """Task 16.2 — validate_ioc rejects overlong / invalid inputs."""

    def test_validate_rejects_overlong_domain(self) -> None:
        from lupe.security.validation import validate_ioc_value

        with pytest.raises(ValueError, match="too long"):
            validate_ioc_value("a" * 254, ioc_type="domain")

    def test_validate_rejects_overlong_ipv4(self) -> None:
        from lupe.security.validation import validate_ioc_value

        with pytest.raises(ValueError, match="too long"):
            validate_ioc_value("1.2.3.4.5.6.7.8.9.0.1", ioc_type="ipv4")

    def test_validate_accepts_valid_ipv4(self) -> None:
        from lupe.security.validation import validate_ioc_value

        # Should not raise
        validate_ioc_value("8.8.8.8", ioc_type="ipv4")

    def test_validate_accepts_valid_domain(self) -> None:
        from lupe.security.validation import validate_ioc_value

        validate_ioc_value("example.com", ioc_type="domain")

    def test_validate_rejects_overlong_sha256(self) -> None:
        from lupe.security.validation import validate_ioc_value

        with pytest.raises(ValueError, match="too long"):
            validate_ioc_value("a" * 65, ioc_type="hash_sha256")

    def test_validate_accepts_valid_sha256(self) -> None:
        from lupe.security.validation import validate_ioc_value

        validate_ioc_value("a" * 64, ioc_type="hash_sha256")

    def test_validate_rejects_empty_value(self) -> None:
        from lupe.security.validation import validate_ioc_value

        with pytest.raises(ValueError, match="empty"):
            validate_ioc_value("", ioc_type="ipv4")


class TestHttpsOnly:
    """Task 16.3 — HTTPS enforcement rejects plain HTTP."""

    def test_https_allowed(self) -> None:
        from lupe.security.https_only import enforce_https

        # Should not raise for HTTPS
        enforce_https("https://api.example.com/data")

    def test_http_rejected(self) -> None:
        from lupe.security.https_only import enforce_https

        with pytest.raises(ValueError, match="HTTPS"):
            enforce_https("http://api.example.com/data")

    def test_localhost_http_allowed(self) -> None:
        from lupe.security.https_only import enforce_https

        # localhost HTTP should be allowed (Ollama)
        enforce_https("http://localhost:11434/api")

    def test_127_http_allowed(self) -> None:
        from lupe.security.https_only import enforce_https

        enforce_https("http://127.0.0.1:11434/api")


class TestRateLimiter:
    """Task 16.4 — RateLimiter token-bucket implementation."""

    @pytest.mark.asyncio
    async def test_allows_under_limit(self) -> None:
        from lupe.security.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=5, per_seconds=1.0)
        for _ in range(5):
            await limiter.acquire()

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self) -> None:
        from lupe.security.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=2, per_seconds=10.0)
        await limiter.acquire()
        await limiter.acquire()
        # Third acquire should block — we cancel after short delay
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(limiter.acquire(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_constructor_defaults(self) -> None:
        from lupe.security.rate_limit import RateLimiter

        limiter = RateLimiter()
        assert limiter._max_requests == 5
        assert limiter._per_seconds == 1.0


class TestPrecommitConfig:
    """Task 16.5 — .pre-commit-config.yaml exists and has required hooks."""

    def test_precommit_config_exists(self) -> None:
        from pathlib import Path

        config = Path(".pre-commit-config.yaml")
        assert config.exists(), ".pre-commit-config.yaml not found"

    def test_precommit_has_gitleaks(self) -> None:
        import yaml

        with open(".pre-commit-config.yaml") as f:
            config = yaml.safe_load(f)
        repo_urls = [r["repo"] for r in config["repos"]]
        assert any("gitleaks" in url for url in repo_urls)

    def test_precommit_has_ruff(self) -> None:
        import yaml

        with open(".pre-commit-config.yaml") as f:
            config = yaml.safe_load(f)
        repo_urls = [r["repo"] for r in config["repos"]]
        assert any("ruff" in url for url in repo_urls)

    def test_precommit_has_bandit(self) -> None:
        import yaml

        with open(".pre-commit-config.yaml") as f:
            config = yaml.safe_load(f)
        repo_urls = [r["repo"] for r in config["repos"]]
        assert any("bandit" in url for url in repo_urls)


class TestBanditConfig:
    """Task 16.6 — bandit configured in pyproject.toml."""

    def test_bandit_section_exists(self) -> None:
        from lupe.compat import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        assert "bandit" in config.get("tool", {})

    def test_bandit_excludes_tests(self) -> None:
        from lupe.compat import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        bandit = config["tool"]["bandit"]
        assert "tests" in bandit.get("exclude_dirs", [])


class TestPipAuditDeps:
    """Task 16.7 — pip-audit and bandit available as dev deps."""

    def test_bandit_in_dev_deps(self) -> None:
        from lupe.compat import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        dev_deps = config["project"]["optional-dependencies"]["dev"]
        assert any("bandit" in d for d in dev_deps)

    def test_pip_audit_in_dev_deps(self) -> None:
        from lupe.compat import tomllib

        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        dev_deps = config["project"]["optional-dependencies"]["dev"]
        assert any("pip-audit" in d for d in dev_deps)


class TestSecurityIntegration:
    """Task 16.8 — Integration: redact works in log-like contexts."""

    def test_redact_in_log_message(self) -> None:
        from lupe.security.redact import redact_secrets

        log_msg = "Connecting to MISP at https://misp.local with api_key=abc123secretvalue"
        safe = redact_secrets(log_msg)
        assert "abc123secretvalue" not in safe
        assert "misp.local" in safe

    def test_redact_censys_credentials(self) -> None:
        from lupe.security.redact import redact_secrets

        msg = "Censys auth failed for api_key=abc123456789 secret=xyz789password123"
        safe = redact_secrets(msg)
        assert "abc123456789" not in safe
        assert "xyz789password123" not in safe
