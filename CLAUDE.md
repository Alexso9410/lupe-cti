# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Lupe CTI** — Cyber Threat Intelligence CLI for OSINT, Forensics & Incident Response. Enriches Indicators of Compromise (IPs, domains, URLs, hashes, emails, phones, usernames) by running them through 25+ threat-intel enrichment plugins in parallel, with optional AI analysis via multiple LLM providers (Ollama, OpenAI, Anthropic, OpenRouter).

## Commands

```bash
# Install (editable)
pip install -e ".[dev]"

# Run CLI
lupe enrich <IOC>
lupe case list
lupe person phone "+54 9 2954 123456"
lupe config show
lupe misp pull --days 7
lupe migrate-from-centinela

# Desktop app
lupe-desktop

# Run all tests
pytest

# Run tests with coverage
pytest --cov=lupe --cov-report=term-missing

# Run a single test file
pytest tests/test_ioc_detect.py

# Run a specific test class or method
pytest tests/test_ioc_detect.py::TestIPv4Detection
pytest tests/test_ioc_detect.py::TestIPv4Detection::test_valid_ipv4

# Lint and format
ruff check lupe/ tests/
ruff format lupe/ tests/

# Type check
mypy lupe/

# Security
bandit -r lupe/
pip-audit

# All checks
make all
```

## Architecture

### Entry Points
- `lupe/cli.py` — Typer CLI with sub-apps: `config`, `case`, `person`, `misp`, and root commands (`enrich`, `email`)
- `lupe/flet/app.py` — Flet desktop app with 6 views (Home, Enrich, Settings, MISP, Plugins, Cases)

### Core Data Flow
1. **IOC Detection** (`lupe/ioc_detect.py`) — regex-based auto-detection of IOC type (priority: SHA256 > SHA1 > MD5 > URL > email > phone > IPv4 > IPv6 > domain)
2. **Enrichment** (`lupe/enrichment/`) — plugin system where each plugin extends `EnrichmentPlugin` (ABC in `base.py`). `__init__.py:run_enrichment()` runs all compatible plugins concurrently (semaphore limit: 5)
3. **AI Analysis** (`lupe/analysis.py`) — delegates to LLM provider via strategy pattern; silently no-ops if no provider configured
4. **Persistence** (`lupe/db.py`) — SQLite via `Database` class; schema auto-migrated on init; stored at XDG data dir

### Plugin System
Every enrichment plugin lives in `lupe/enrichment/` and must:
- Subclass `EnrichmentPlugin`
- Declare `name: str`, `supported_ioc_types: set[IOCType]`, and `requires_api_key: bool`
- Implement `async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None`

Free plugins (no key): `WhoisPlugin`, `IpInfoPlugin`, `ThreatFoxPlugin`, `URLhausPlugin`, `MalwareBazaarPlugin`, `PhoneStaticPlugin`, `WhatsMyNamePlugin`, `IPQueryPlugin`, `CertShPlugin`, `CIRCLHashlookupPlugin`, `HolehePlugin`, `BlocklistDePlugin`, `CrtShPlugin`

Keyed plugins (loaded only when env var is set): `AbuseIPDB`, `VirusTotal`, `Shodan`, `OTX`, `URLScan`, `HaveIBeenPwned`, `GreyNoise`, `IPQS` (also has phone variant), `NumVerify`, `EmailRep`, `GoogleSafeBrowsing`, `PhishTank`, `Pulsedive`, `Spamhaus`, `HybridAnalysis`, `Censys`

### Multi-LLM System
`lupe/llm/` implements a strategy pattern:
- `base.py` — `LLMProvider` ABC with `generate()`, `stream()`, `validate_key()`, `list_models()`
- `registry.py` — Provider factory with `get_provider(name, settings)`
- Providers: `ollama.py`, `openai.py`, `anthropic.py`, `openrouter.py`
- Selection: `LUPE_LLM_PROVIDER` env var (empty = skip AI)

### Security Layer (`lupe/security/`)
- `redact.py` — Secret redaction in log output
- `validation.py` — IOC input validation with per-type max lengths
- `https_only.py` — HTTPS transport enforcement
- `rate_limit.py` — Token-bucket rate limiter

### Configuration
`lupe/config.py` — `pydantic-settings` singleton (`get_settings()` with `lru_cache`). All settings use `LUPE_` prefix. Reads from `.env` file or environment variables. Uses `platformdirs` for XDG-compliant paths.

Key settings:
- `LUPE_OLLAMA_BASE_URL` / `LUPE_OLLAMA_MODEL` — Ollama backend
- `LUPE_LLM_PROVIDER` — Provider selection (ollama/openai/anthropic/openrouter)
- `LUPE_DB_PATH` — SQLite path (default: XDG data dir)
- One env var per API key (e.g., `LUPE_VIRUSTOTAL_KEY`)

### MISP Integration (`lupe/integrations/misp.py`)
Raw REST client for MISP. Commands: `lupe misp pull`, `lupe misp push`. Activated by `LUPE_MISP_URL` + `LUPE_MISP_KEY`.

### Export Layer (`lupe/export/`)
- `obsidian.py` — Markdown with frontmatter and MITRE ATT&CK tag extraction
- `json_export.py` — Raw JSON export
- `pdf_report.py` — PDF via ReportLab

### Email Analysis (`lupe/email_parser.py`, `lupe/email_analyzer.py`)
Parses `.eml` files: headers, SPF/DKIM/DMARC auth, received chain, attachments (SHA256), body IOCs, phishing score.

## Database Schema

Six tables: `iocs`, `enrichments`, `analyses`, `cases`, `case_iocs`, `case_notes`, `email_analyses`. Key relationships:
- `cases` → `case_iocs` → `iocs` → `enrichments`
- `email_analyses` optionally linked to a `case_id`

## Testing

Tests live in `tests/`. `pytest-asyncio` is configured with `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed. Use `respx` for mocking `httpx` calls in enrichment plugin tests.

Current status: 312 tests passing, 0 ruff errors.
