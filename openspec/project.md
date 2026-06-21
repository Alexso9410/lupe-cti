# Project Context: centinela (future: Lupe CTI)

## Overview
IOC Enrichment & Investigation CLI for Heimdall Security. Analyzes Indicators of Compromise by running them through multiple threat-intel enrichment plugins in parallel, with optional AI analysis via a local Ollama instance.

Planned rebrand: **Centinela → Lupe CTI** (Cyber Threat Intelligence).
Target deployment: **distro Linux específica para OSINT y forense**.

## Stack

| Layer | Technology |
|-------|------------|
| Language | Python >=3.10 |
| Build | hatchling |
| CLI | typer + rich |
| HTTP | httpx (async) |
| Data | pydantic + pydantic-settings |
| DB | SQLite (stdlib) |
| Desktop GUI | pywebview (HTML estático) |
| PDF | reportlab |
| Phone parsing | phonenumbers |
| AI | Ollama local (`/v1/chat/completions`) |

### Dev Dependencies
- pytest >=8.0
- pytest-asyncio >=0.23 (auto mode)
- respx >=0.21

## Architecture

### Entry Points
- `centinela/cli.py` — Typer CLI with sub-apps: `config`, `case`, `person`, root commands (`enrich`, `email`)
- `centinela/desktop/app.py` — pywebview wrapper serving `centinela_kimi_frontend.html`
- `centinela-desktop.py` — standalone desktop launcher

### Core Data Flow
1. **IOC Detection** (`centinela/ioc_detect.py`) — regex-based auto-detection (priority: SHA256 > SHA1 > MD5 > URL > email > phone > IPv4 > IPv6 > domain)
2. **Enrichment** (`centinela/enrichment/`) — plugin system extending `EnrichmentPlugin` (ABC). `run_enrichment()` runs compatible plugins concurrently (semaphore limit: 5)
3. **AI Analysis** (`centinela/analysis.py`) — sends results to Ollama; silently no-ops if unreachable
4. **Persistence** (`centinela/db.py`) — SQLite via `Database` class; schema auto-migrated; stored at `~/.centinela/centinela.db`

### Plugin System
Every enrichment plugin must:
- Subclass `EnrichmentPlugin`
- Declare `name: str`, `supported_ioc_types: set[IOCType]`, `requires_api_key: bool`
- Implement `async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None`

Free plugins: `WhoisPlugin`, `IpInfoPlugin`, `ThreatFoxPlugin`, `URLhausPlugin`, `MalwareBazaarPlugin`, `PhoneStaticPlugin`, `WhatsMyNamePlugin`
Keyed plugins (env-gated): `AbuseIPDB`, `VirusTotal`, `Shodan`, `OTX`, `URLScan`, `HaveIBeenPwned`, `GreyNoise`, `IPQS`, `NumVerify`

### Configuration
`centinela/config.py` — pydantic-settings singleton (`get_settings()` with `lru_cache`). All settings use `CENTINELA_` prefix. Reads from `.env` or environment variables.

Key settings:
- `CENTINELA_OLLAMA_BASE_URL` / `CENTINELA_OLLAMA_MODEL`
- `CENTINELA_DB_PATH` (default: `~/.centinela/centinela.db`)
- One env var per API key (e.g., `CENTINELA_VIRUSTOTAL_KEY`)

### Database Schema
Six tables: `iocs`, `enrichments`, `analyses`, `cases`, `case_iocs`, `case_notes`, `email_analyses`

### Export Layer
- `obsidian.py` — Markdown notes with frontmatter, MITRE ATT&CK tag extraction
- `json_export.py` — raw JSON export
- `pdf_report.py` — PDF via ReportLab

### Email Analysis
Parses `.eml` files: headers, SPF/DKIM/DMARC auth results, received chain hops, attachments (SHA256), body IOCs, phishing score. Stored in `email_analyses` table.

### Heimdall Integration
Optional bridge to Heimdall's `agent-dashboard`. Activated by `CENTINELA_DASHBOARD_ENABLED=1`. Dynamically imports `AgentWriter` from `C:\Users\usuario\Documents\heimdall\tools\agent_writer.py`.

## Conventions

- `from __future__ import annotations` at top of modules
- snake_case module names
- Plugin class names: `{Service}Plugin` (PascalCase)
- Test files: `tests/test_{module}.py`
- Test classes: `Test{Feature}` (PascalCase)
- Async tests: no `@pytest.mark.asyncio` needed (auto mode configured)
- httpx mocking: `respx.mock` decorator
- Pydantic models for all data structures (`centinela/models.py`)
- Environment variables prefixed with `CENTINELA_`
- Plugin files live in `centinela/enrichment/`

## Key Files

| File | Role |
|------|------|
| `pyproject.toml` | Project config, deps, pytest settings |
| `CLAUDE.md` | Architecture and command reference |
| `centinela/cli.py` | CLI entry point (typer) |
| `centinela/models.py` | Pydantic models (IOC, EnrichmentResult, etc.) |
| `centinela/ioc_detect.py` | IOC auto-detection logic |
| `centinela/enrichment/base.py` | Plugin ABC |
| `centinela/db.py` | SQLite persistence |
| `centinela/config.py` | pydantic-settings singleton |
| `centinela/analysis.py` | Ollama AI analysis |
| `tests/test_ioc_detect.py` | Example sync tests |
| `tests/test_emailrep.py` | Example async tests with respx |
