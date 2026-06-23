from __future__ import annotations

import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import platformdirs
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PREFIX = "LUPE_"
_APP_NAME = "lupe"


def get_data_dir() -> Path:
    """Return the user data directory for Lupe CTI.

    Linux: ~/.local/share/lupe
    Windows: %LOCALAPPDATA%\\Lupe
    macOS: ~/Library/Application Support/lupe
    """
    return Path(platformdirs.user_data_dir(_APP_NAME, appauthor=False))


def get_config_dir() -> Path:
    """Return the user config directory for Lupe CTI.

    Linux: ~/.config/lupe
    Windows: %APPDATA%\\Lupe
    macOS: ~/Library/Application Support/lupe
    """
    return Path(platformdirs.user_config_dir(_APP_NAME, appauthor=False))


def get_cache_dir() -> Path:
    """Return the user cache directory for Lupe CTI.

    Linux: ~/.cache/lupe
    Windows: %LOCALAPPDATA%\\Lupe\\Cache
    macOS: ~/Library/Caches/lupe
    """
    return Path(platformdirs.user_cache_dir(_APP_NAME, appauthor=False))


def ensure_dirs() -> None:
    """Create data, config, and cache directories if they don't exist.

    On Linux, also sets chmod 700 on the config directory for security.
    """
    for d in (get_data_dir(), get_config_dir(), get_cache_dir()):
        d.mkdir(parents=True, exist_ok=True)

    # Restrict config dir permissions
    config_dir = get_config_dir()
    if sys.platform != "win32":
        config_dir.chmod(0o700)
    else:
        # Windows: use icacls to restrict to current user only
        try:
            subprocess.run(
                [
                    "icacls",
                    str(config_dir),
                    "/inheritance:r",
                    "/grant:r",
                    f"{os.environ.get('USERNAME', os.environ.get('USER', ''))}:F",
                ],
                check=False,
                capture_output=True,
                timeout=10,
            )
        except Exception:
            pass  # best-effort, not fatal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix=ENV_PREFIX,
        case_sensitive=False,
        extra="ignore",
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = (
        "gemma3:4b"  # Fast, fits 8GB RAM. Override via LUPE_OLLAMA_MODEL.
    )
    ollama_api_key: str | None = None  # Required for cloud models (gemma4:31b-cloud, etc.)
    db_path: str = ""  # Empty = use platformdirs default

    # LLM provider selection (empty = skip AI analysis)
    llm_provider: str = ""  # "ollama", "openai", "anthropic", "openrouter"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # CRITICAL #2 — PII redaction before sending data to any LLM provider.
    # Default ON. Set LUPE_LLM_REDACT_PII=false to disable (NOT recommended
    # for cloud LLM providers — exposes email PII to third parties).
    llm_redact_pii: bool = True

    # MISP integration
    misp_url: str | None = None
    misp_key: str | None = None

    # New enrichment keys
    hybrid_analysis_key: str | None = None
    censys_id: str | None = None
    censys_secret: str | None = None
    spamhaus_key: str | None = None

    # Existing enrichment keys
    abuseipdb_key: str | None = None
    virustotal_key: str | None = None
    shodan_key: str | None = None
    otx_key: str | None = None
    urlscan_key: str | None = None
    hibp_key: str | None = None
    greynoise_key: str | None = None
    ipqs_key: str | None = None
    numverify_key: str | None = None
    emailrep_key: str | None = None
    googlesb_key: str | None = None
    phishtank_key: str | None = None
    pulsedive_key: str | None = None

    # Auto-update
    github_repo: str = "lupe-cti/lupe"

    @field_validator("db_path", mode="before")
    @classmethod
    def expand_db_path(cls, v: str) -> str:
        """Resolve db_path: empty string uses platformdirs default."""
        if not v:
            return str(get_data_dir() / "lupe.db")
        return str(Path(v).expanduser())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
