# Design: Lupe CTI v1

## Technical Approach

Hard-cut rename of `centinela` → `lupe` package with XDG-compliant paths, Strategy-pattern LLM providers, Textual TUI replacing pywebview, MISP integration via raw REST, 7 new enrichment plugins, and full CI/CD hardening. Maps to proposal phases 1–4 and all 24 spec capabilities.

## Architecture Decisions

### AD-1: Textual TUI over pywebview

**Choice**: Replace pywebview desktop GUI with Textual TUI
**Alternatives**: (a) Keep pywebview + Vue CDN, (b) Electron, (c) kitty graphics protocol
**Rationale**: Textual runs in any terminal including SSH sessions, has zero native dependencies (no WebKitGTK), works identically on Windows and Linux, and supports rich widgets (tables, forms, key bindings). Critical for forensics distro where GUI is not guaranteed.

### AD-2: Strategy pattern for LLM providers

**Choice**: `LLMProvider` ABC with registry + factory; default = no AI (skip if unconfigured)
**Alternatives**: (a) Simple if/else chain, (b) Plugin system like enrichment, (c) LangChain abstraction
**Rationale**: Strategy gives compile-time type safety, easy provider addition, and explicit failure modes. LangChain adds heavy dependency for trivial use. Default to "no AI" avoids the Ollama requirement — users who don't configure a provider get plugin results only, matching existing behavior.

### AD-3: XDG paths via `platformdirs`

**Choice**: Use `platformdirs` library for all path resolution (data, config, cache)
**Alternatives**: (a) Manual `os.path.expanduser`, (b) `pathlib.Path.home()` construction
**Rationale**: `platformdirs` handles Linux (XDG), macOS, and Windows conventions correctly, including `%LOCALAPPDATA%` on Windows. Single dependency, well-maintained, used by pip itself.

### AD-4: MISP via raw httpx (no pymisp)

**Choice**: Direct REST API calls with `httpx.AsyncClient` + Pydantic response models
**Alternatives**: (a) `pymisp` library, (b) generated OpenAPI client
**Rationale**: pymisp adds 15+ transitive dependencies and is overkill for 2 endpoints (search indicators, add indicator). Raw httpx keeps the dependency tree lean and gives us full control over retries, timeouts, and error handling.

### AD-5: Hard-cut rename without compatibility shims

**Choice**: Full rename with migration script, no backward-compat aliases
**Alternatives**: (a) Import redirection `centinela → lupe`, (b) dual env var prefixes, (c) symlinks
**Rationale**: No public users exist. Maintaining dual names creates confusion and technical debt. A one-time `lupe migrate-from-centinela` command handles the transition cleanly.

## Data Flow

```
CLI (typer) ──→ TUI (Textual) ──→ Enrichment Engine ──→ DB (SQLite)
     │                │                    │                    │
     │                │              ┌────┴────┐            │
     │                │              │Plugins  │            │
     │                │              │(async)  │            │
     │                │              └────┬────┘            │
     │                │                   │                 │
     │           Settings Screen     LLM Provider           │
     │           (API keys, prov.)  (Strategy)               │
     │                │                   │                  │
     └────────────────┴───────────────────┴──────────────────┘
                          ┌─────────────────┐
                          │  MISP Client    │
                          │  (httpx REST)   │
                          └─────────────────┘
```

### Sequence: `lupe enrich 8.8.8.8`

```
User → CLI: lupe enrich 8.8.8.8
CLI → ioc_detect: detect_ioc("8.8.8.8") → IOC(ipv4, "8.8.8.8")
CLI → Settings: get_settings() → resolve LUPE_* env vars
CLI → Enrichment: run_enrichment(ioc, settings)
  Enrichment → Plugin registry: _build_plugins(settings) → filtered list
  Enrichment → asyncio.gather: run compatible plugins with semaphore(5)
    Plugin A → httpx.AsyncClient: GET https://... → parse → EnrichmentResult
    Plugin B → httpx.AsyncClient: GET https://... → parse → EnrichmentResult
    ...
  Enrichment → results list
CLI → LLM Provider: if configured, analyze_ioc(ioc, results, provider)
  Provider → httpx.AsyncClient: POST /v1/chat/completions → analysis text
  (or skip with warning if provider unavailable)
CLI → DB: _save_to_db(ioc, results, analysis)
CLI → Rich console: render table + analysis panel
```

### Deployment Diagram

```
~/.local/share/lupe/
├── lupe.db                          # SQLite database
└── logos/                           # Logo assets (installed)

~/.config/lupe/
├── lupe.toml                        # Persistent config (API keys, provider, etc.)
└── .env                             # Env vars override (LUPE_*)

~/.cache/lupe/
└── (plugin response cache - v1.1)

/usr/local/bin/lupe                  # CLI entry point (pipx)
/usr/local/bin/lupe-desktop          # TUI entry point (pipx)
/usr/share/applications/lupe.desktop # .desktop file
/usr/share/man/man1/lupe.1.gz        # manpage

%LOCALAPPDATA%\Lupe\
└── lupe.db                          # Windows DB path
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `lupe/__init__.py` | Create | Package init (replaces `centinela/`) |
| `lupe/cli.py` | Create | Typer CLI — rename all refs, add `migrate-from-centinela`, `misp` sub-apps |
| `lupe/config.py` | Create | Settings with `LUPE_*` prefix, `platformdirs` paths, LLM provider fields |
| `lupe/models.py` | Create | IOC, EnrichmentResult, Severity, LLM models (ModelInfo, ProviderConfig) |
| `lupe/ioc_detect.py` | Create | IOC detection (updated imports to `lupe.`) |
| `lupe/db.py` | Create | Database class — XDG path resolution |
| `lupe/analysis.py` | Create | Refactored: delegates to LLMProvider instead of hardcoded Ollama |
| `lupe/llm/__init__.py` | Create | LLM subpackage |
| `lupe/llm/base.py` | Create | `LLMProvider` ABC: `generate()`, `stream()`, `validate_key()`, `list_models()` |
| `lupe/llm/registry.py` | Create | Provider registry + `get_provider(name)` factory |
| `lupe/llm/ollama.py` | Create | OllamaProvider implementation |
| `lupe/llm/openai.py` | Create | OpenAIProvider implementation |
| `lupe/llm/anthropic.py` | Create | AnthropicProvider implementation |
| `lupe/llm/openrouter.py` | Create | OpenRouterProvider implementation |
| `lupe/enrichment/base.py` | Modify | Update import to `lupe.models` |
| `lupe/enrichment/__init__.py` | Modify | Update imports + add 7 new plugins |
| `lupe/enrichment/blocklist_de.py` | Create | Blocklist.de Plugin |
| `lupe/enrichment/spamhaus.py` | Create | Spamhaus Plugin |
| `lupe/enrichment/crtsh.py` | Create | crt.sh Certificate Transparency Plugin |
| `lupe/enrichment/cisco_talos.py` | Create | Cisco Talos Plugin |
| `lupe/enrichment/hybrid_analysis.py` | Create | Hybrid Analysis Plugin (keyed) |
| `lupe/enrichment/censys.py` | Create | Censys Plugin (keyed) |
| `lupe/tui/__init__.py` | Create | TUI subpackage |
| `lupe/tui/app.py` | Create | Textual App with dark theme + matrix green |
| `lupe/tui/screens/home.py` | Create | HomeScreen — dashboard summary |
| `lupe/tui/screens/enrich.py` | Create | EnrichScreen — input + results |
| `lupe/tui/screens/settings.py` | Create | SettingsScreen — API keys + LLM provider config |
| `lupe/tui/screens/misp.py` | Create | MISPScreen — pull/push indicators |
| `lupe/tui/screens/plugins.py` | Create | PluginsScreen — plugin status |
| `lupe/tui/screens/cases.py` | Create | CasesScreen — case management |
| `lupe/tui/theme.py` | Create | Theme definitions (cyan, #00FF41, dark) |
| `lupe/integrations/misp.py` | Create | MISPClient: httpx REST consumer + exporter |
| `lupe/integrations/agent_writer_bridge.py` | Modify | Update import paths |
| `lupe/security/__init__.py` | Create | Security subpackage |
| `lupe/security/redaction.py` | Create | API key redaction filter for logging |
| `lupe/security/validation.py` | Create | IOC input validation (length, format) |
| `lupe/security/https_only.py` | Create | httpx transport that rejects non-HTTPS |
| `lupe/security/rate_limit.py` | Create | Per-plugin rate limiter |
| `lupe/migrate.py` | Create | `lupe migrate-from-centinela` command |
| `lupe/desktop/app.py` | Delete | pywebview removed — replaced by TUI |
| `centinela-desktop.py` | Delete | Replaced by `lupe-desktop` entry point |
| `centinela/` (entire dir) | Delete | Replaced by `lupe/` package |
| `pyproject.toml` | Modify | `name=lupe-cti`, entry points, new deps |
| `.pre-commit-config.yaml` | Create | gitleaks, ruff, bandit hooks |
| `pyproject.toml` [bandit] | Create | bandit config exclude dirs |
| `.github/workflows/ci.yml` | Create | Matrix CI (5 OS × lint/type/test/security) |
| `.github/workflows/release.yml` | Create | Tag → PyPI + GitHub Release |
| `.github/workflows/codeql.yml` | Create | CodeQL scheduled + PR scan |
| `.github/workflows/dependency-review.yml` | Create | Dependabot + dependency review |
| `assets/logo.svg` | Create | Primary logo (lupa + binary + auriculares) |
| `assets/logo-256.png` | Create | PNG variants (256/128/64/32/16) |
| `assets/logo-mono.svg` | Create | Monochrome variant |
| `lupe.1` | Create | Groff manpage |
| `lupe.desktop` | Create | XDG .desktop file |
| `lupe-watch.service` | Create | Optional systemd unit |
| `tests/test_llm_base.py` | Create | LLMProvider ABC contract tests |
| `tests/test_llm_providers.py` | Create | Provider implementations (respx mocks) |
| `tests/test_misp_client.py` | Create | MISPClient REST tests (respx) |
| `tests/test_config_lupe.py` | Create | LUPE_* env var loading |
| `tests/test_migration.py` | Create | Legacy DB migration tests |
| `tests/test_security.py` | Create | Redaction, validation, HTTPS enforcement |
| `tests/test_tui_screens.py` | Create | TUI screen rendering snapshots |
| `tests/test_blocklist_de.py` | Create | Plugin tests |
| `tests/test_spamhaus.py` | Create | Plugin tests |
| `tests/test_crtsh.py` | Create | Plugin tests |
| `tests/test_cisco_talos.py` | Create | Plugin tests |
| `tests/test_hybrid_analysis.py` | Create | Plugin tests |
| `tests/test_censys.py` | Create | Plugin tests |
| Existing `tests/test_*.py` | Modify | Update all imports `centinela` → `lupe` |

## Interfaces / Contracts

### LLMProvider ABC

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str
    context_length: int | None = None

class LLMProvider(ABC):
    """Abstract base for all LLM providers."""
    name: str  # e.g. "ollama", "openai"
    requires_api_key: bool = True

    @abstractmethod
    async def generate(self, prompt: str, *, system: str | None = None) -> str: ...
    
    @abstractmethod
    async def stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]: ...
    
    @abstractmethod
    async def validate_key(self) -> bool: ...
    
    @abstractmethod
    def list_models(self) -> list[ModelInfo]: ...
```

### Provider Registry

```python
_PROVIDERS: dict[str, type[LLMProvider]] = {}

def register_provider(cls: type[LLMProvider]) -> type[LLMProvider]:
    _PROVIDERS[cls.name] = cls
    return cls

def get_provider(name: str, settings: Settings) -> LLMProvider | None:
    """Factory. Returns None if name invalid or key missing."""
    cls = _PROVIDERS.get(name)
    if cls is None:
        return None
    return cls.from_settings(settings)  # May return None if key not configured
```

### MISPClient

```python
class MISPClient:
    def __init__(self, url: str, api_key: str, timeout: float = 30.0): ...
    async def get_indicators(self, *, tags: list[str] | None = None, days: int = 7, ioc_type: str | None = None) -> list[IOC]: ...
    async def add_indicator(self, ioc: IOC, tags: list[str] | None = None, info: str = "") -> str: ...
    async def close(self) -> None: ...
    # Uses httpx.AsyncClient with connection pooling
```

### EnrichmentPlugin (unchanged interface)

```python
class EnrichmentPlugin(ABC):  # Existing, import path changes only
    name: str
    supported_ioc_types: set[IOCType]
    requires_api_key: bool = False
    
    @abstractmethod
    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None: ...
```

### New Settings Fields

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LUPE_", ...)
    
    # Existing (renamed)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:31b-cloud"
    
    # LLM provider
    llm_provider: str = ""  # empty = skip AI analysis
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # MISP
    misp_url: str | None = None
    misp_key: str | None = None
    
    # New enrichment keys
    hybrid_analysis_key: str | None = None
    censys_id: str | None = None
    censys_secret: str | None = None
    cisco_talos_key: str | None = None
    
    # Path resolution (via platformdirs in validator)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | LLMProvider ABC contract | Abstract class instantiation rejection, method signatures |
| Unit | Each LLM provider (4) | `respx.mock` HTTP responses — success, timeout, auth failure, quota exceeded |
| Unit | MISPClient REST calls | `respx.mock` — GET/POST to MISP API, error codes, timeout |
| Unit | Config loading (`LUPE_*`) | `monkeypatch` env vars, verify Settings fields, XDG paths |
| Unit | Security (redaction, validation, HTTPS) | Unit tests for `redact_secrets()`, `validate_ioc()`, `HttpsOnlyTransport` |
| Unit | New plugins (7) | `respx.mock` per plugin — success, empty, error, rate limit |
| Unit | IOC detection | Existing tests with updated imports |
| Integration | `run_enrichment()` end-to-end | Multiple respx mocks, verify plugin dispatch and result aggregation |
| Integration | Provider selection flow | Settings → registry → provider instantiation → generate/stream |
| Integration | DB persistence with new paths | In-memory SQLite, verify XDG path resolution |
| Integration | Migration script | Copy real DB, migrate, verify row counts and data integrity |
| E2E | CLI commands | Subprocess `lupe enrich 8.8.8.8` against mock server |

## Migration / Rollout

**`lupe migrate-from-centinela`** command:
1. Check `~/.centinela/centinela.db` exists; if not, exit with message
2. Create backup: `~/.centinela/centinela.db.bak`
3. Copy DB to `platformdirs.user_data_dir / "lupe.db"`
4. Report row counts and success
5. Optionally: convert env vars in `.env` from `CENTINELA_*` to `LUPE_*`

No feature flags needed — hard cut. The migration command is a one-time standalone tool.

## Open Questions

- [ ] Textual 2.x vs 1.x API stability — verify compatibility with Debian 12's Python 3.11
- [ ] Censys requires both `id` and `secret` — confirm this fits the single-key pattern or needs a new `censys_auth` field
- [ ] Cisco Talos has no public API — spec says "Cisco Talos" but may need web scraping or drop this plugin
- [ ] `lupe-desktop` entry point now launches Textual, not pywebview — confirm launch behavior on Windows GUI terminals