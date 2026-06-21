from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CENTINELA_",
        case_sensitive=False,
        extra="ignore",
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:31b-cloud"
    db_path: str = "~/.centinela/centinela.db"

    abuseipdb_key: str | None = None
    virustotal_key: str | None = None
    shodan_key: str | None = None
    otx_key: str | None = None
    urlscan_key: str | None = None
    hibp_key: str | None = None
    greynoise_key: str | None = None    # CENTINELA_GREYNOISE_KEY
    ipqs_key: str | None = None         # CENTINELA_IPQS_KEY
    numverify_key: str | None = None    # CENTINELA_NUMVERIFY_KEY
    emailrep_key: str | None = None     # CENTINELA_EMAILREP_KEY
    googlesb_key: str | None = None     # CENTINELA_GOOGLESB_KEY
    phishtank_key: str | None = None    # CENTINELA_PHISHTANK_KEY
    pulsedive_key: str | None = None    # CENTINELA_PULSEDIVE_KEY

    @field_validator("db_path", mode="before")
    @classmethod
    def expand_db_path(cls, v: str) -> str:
        """Expand ~ in db_path to the actual home directory."""
        return str(Path(v).expanduser())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
