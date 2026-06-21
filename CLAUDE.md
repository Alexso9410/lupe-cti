# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Centinela** — IOC Enrichment & Investigation CLI for Heimdall Security. Analyzes Indicators of Compromise (IPs, domains, URLs, hashes, emails, phones, usernames) by running them through multiple threat-intel enrichment plugins in parallel, with optional AI analysis via a local Ollama instance.

## Commands

```bash
# Install (editable)
pip install -e ".[dev]"

# Run CLI
centinela enrich <IOC>
centinela case list
centinela person phone "+54 9 2954 123456"
centinela config show

# Desktop GUI
centinela-desktop

# Run all tests
pytest

# Run a single test file
pytest tests/test_ioc_detect.py

# Run a specific test class or method
pytest tests/test_ioc_detect.py::TestIPv4Detection
pytest tests/test_ioc_detect.py::TestIPv4Detection::test_valid_ipv4
```

## Architecture

### Entry Points
- `centinela/cli.py` — Typer CLI with four sub-apps: `config`, `case`, `person`, and root commands (`enrich`, `email`)
- `centinela/desktop/app.py` — pywebview desktop wrapper that serves `centinela_kimi_frontend.html`
- `centinela-desktop.py` — standalone desktop launcher at project root

### Core Data Flow
1. **IOC Detection** (`centinela/ioc_detect.py`) — regex-based auto-detection of IOC type (priority order: SHA256 > SHA1 > MD5 > URL > email > phone > IPv4 > IPv6 > domain)
2. **Enrichment** (`centinela/enrichment/`) — plugin system where each plugin extends `EnrichmentPlugin` (ABC in `base.py`). `__init__.py:run_enrichment()` runs all compatible plugins concurrently (semaphore limit: 5)
3. **AI Analysis** (`centinela/analysis.py`) — sends enrichment results to Ollama via `/v1/chat/completions`; silently no-ops if Ollama is unreachable
4. **Persistence** (`centinela/db.py`) — SQLite via `Database` class; schema auto-migrated on init; stored at `~/.centinela/centinela.db`

### Plugin System
Every enrichment plugin lives in `centinela/enrichment/` and must:
- Subclass `EnrichmentPlugin`
- Declare `name: str`, `supported_ioc_types: set[IOCType]`, and `requires_api_key: bool`
- Implement `async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None`

Free plugins (no key): `WhoisPlugin`, `IpInfoPlugin`, `ThreatFoxPlugin`, `URLhausPlugin`, `MalwareBazaarPlugin`, `PhoneStaticPlugin`, `WhatsMyNamePlugin`

Keyed plugins (loaded only when env var is set): `AbuseIPDB`, `VirusTotal`, `Shodan`, `OTX`, `URLScan`, `HaveIBeenPwned`, `GreyNoise`, `IPQS` (also has phone variant), `NumVerify`

### Configuration
`centinela/config.py` — `pydantic-settings` singleton (`get_settings()` with `lru_cache`). All settings use `CENTINELA_` prefix. Reads from `.env` file or environment variables.

Key settings:
- `CENTINELA_OLLAMA_BASE_URL` / `CENTINELA_OLLAMA_MODEL` — AI analysis backend
- `CENTINELA_DB_PATH` — SQLite path (default: `~/.centinela/centinela.db`)
- One env var per API key (e.g., `CENTINELA_VIRUSTOTAL_KEY`)

### Export Layer (`centinela/export/`)
- `obsidian.py` — generates Markdown notes with frontmatter, MITRE ATT&CK tag extraction
- `json_export.py` — raw JSON export
- `pdf_report.py` — PDF report via ReportLab (also used for email analysis reports)

### Email Analysis (`centinela/email_parser.py`, `centinela/email_analyzer.py`)
Parses `.eml` files: extracts headers, SPF/DKIM/DMARC auth results, received chain hops, attachments (SHA256), body IOCs, and computes a phishing score. Results stored in `email_analyses` table.

### Heimdall Integration (`centinela/integrations/agent_writer_bridge.py`)
Optional bridge to Heimdall's `agent-dashboard`. Activated by `CENTINELA_DASHBOARD_ENABLED=1`. Dynamically imports `AgentWriter` from `C:\Users\usuario\Documents\heimdall\tools\agent_writer.py`. Silently disabled if not found.

## Database Schema

Six tables: `iocs`, `enrichments`, `analyses`, `cases`, `case_iocs`, `case_notes`, `email_analyses`. Key relationships:
- `cases` → `case_iocs` → `iocs` → `enrichments`
- `email_analyses` optionally linked to a `case_id`

## Testing

Tests live in `tests/`. `pytest-asyncio` is configured with `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed. Use `respx` for mocking `httpx` calls in enrichment plugin tests.
