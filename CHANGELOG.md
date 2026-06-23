# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-21

### Added

- **Rebrand**: Renamed package from `centinela` to `lupe-cti`, CLI from `centinela` to `lupe`
- **Multi-LLM Analysis**: Strategy pattern with 4 providers — Ollama (local), OpenAI, Anthropic, OpenRouter
- **Terminal UI**: Interactive TUI built with Textual featuring 6 screens (Home, Enrich, Settings, MISP, Plugins, Cases)
- **TUI Settings Panel**: Visual API key editor with live validation, signup links, and secure persistence (chmod 600)
- **MISP Integration**: Pull/push indicators to MISP instances via raw REST API (`lupe misp pull/push`)
- **5 New Enrichment Plugins**:
  - Blocklist.de — IP reputation (free, no key)
  - Spamhaus — IP/domain reputation (free with key)
  - crt.sh — Certificate transparency for domains (free, no key)
  - Hybrid Analysis — Hash/URL sandbox analysis (freemium)
  - Censys — IP/domain/certificate intelligence (freemium)
- **Security Hardening**:
  - Secret redaction in log output (`lupe/security/redact.py`)
  - IOC input validation with per-type max lengths (`lupe/security/validation.py`)
  - HTTPS-only transport enforcement (`lupe/security/https_only.py`)
  - Token-bucket rate limiter for plugin concurrency (`lupe/security/rate_limit.py`)
  - Pre-commit hooks: gitleaks, ruff, bandit
- **CI/CD Pipeline**:
  - Matrix CI: Ubuntu 22.04/24.04, Debian 12, Windows, Python 3.10-3.12
  - PyPI release workflow with cibuildwheel and trusted publishing
  - CodeQL analysis (weekly + PR)
  - Dependency review on PRs
  - Dependabot configuration
  - PR and issue templates
- **XDG-Compliant Paths**: `platformdirs` integration for cross-platform data/config/cache directories
- **Migration Command**: `lupe migrate-from-centinela` with automatic backup
- **Logo Assets**: SVG logo (primary + mono variant), .desktop file, groff manpage
- **Export Formats**: Obsidian Markdown (with MITRE ATT&CK tags), JSON, PDF reports
- **Email Analysis**: .eml parser with SPF/DKIM/DMARC validation, phishing score
- **Ruff Configuration**: Code formatting and linting with zero errors across the entire codebase

### Changed

- Package name: `centinela` → `lupe-cti`
- CLI command: `centinela` → `lupe`
- Desktop command: `centinela-desktop` → `lupe-desktop`
- Environment variable prefix: `CENTINELA_*` → `LUPE_*`
- Database path: `~/.centinela/centinela.db` → XDG-compliant `~/.local/share/lupe/lupe.db`
- Config path: `~/.centinela/` → `~/.config/lupe/`
- AI analysis: from hardcoded Ollama to pluggable multi-LLM architecture
- Desktop UI: from pywebview (WebView) to Textual (terminal-native TUI)
- Plugin concurrency: configurable semaphore limit (default: 5)

### Deprecated

Nothing — this is a clean-slate rebrand with no backward compatibility layer.

### Removed

- **pywebview Desktop Frontend**: Replaced by Textual TUI
- **`centinela_kimi_frontend.html`**: Legacy web frontend eliminated
- **`centinela-desktop.py`**: Legacy standalone launcher eliminated
- **`CENTINELA_*` Environment Variables**: All replaced by `LUPE_*` equivalents
- **Backward Compatibility**: No aliases or shims for old names (intentional hard cut)

### Fixed

- Ruff lint errors: 247 errors across 97 files resolved (I001, E501, F841, F401, W293, W291, N806, N999)
- Plugin test coverage gaps in legacy plugins
- Input validation for IOC values with per-type length limits
- Transport security: all external HTTP calls now enforce HTTPS

### Security

- HTTPS-only transport for all external API calls (localhost Ollama exempted)
- IOC input validation with per-type max lengths (IPv4=15, domain=253, SHA256=64, URL=2048, absolute max=4096)
- Secret redaction in CLI output and log formatters
- Token-bucket rate limiter with configurable `max_requests` / `per_seconds`
- Pre-commit hooks enforce gitleaks (secret detection), ruff (lint + format), bandit (security)
- CI pipeline runs bandit, pip-audit, mypy, and CodeQL on every PR
- Config directory permissions restricted to 700 on Linux
- Config file permissions restricted to 600 on Linux (TUI settings persistence)

[1.0.0]: https://github.com/Alexso9410/lupe-cti/releases/tag/v1.0.0
