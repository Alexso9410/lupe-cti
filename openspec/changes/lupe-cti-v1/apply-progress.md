# Apply Progress: lupe-cti-v1 — Phase 3 (Security + CI/CD)

## Status: `ready` — Phase 3 complete, ready for Phase 4

## PR Summary

| PR | Branch | Status | Commit | Description |
|----|--------|--------|--------|-------------|
| PR-0 | `feature/pr-0-coverage-baseline` | ✅ | `8b204ec` | Added pytest-cov config, 19 new tests for legacy plugins |
| PR-1 | `feature/pr-1-package-rename` | ✅ | `77bbe21` | Renamed `centinela/` → `lupe/`, updated all imports, pyproject.toml |
| PR-2 | `feature/pr-2-cli-rename` | ✅ | `19a6c2b` | CLI name `lupe`, help text, Rich banners rebranded |
| PR-3 | `feature/pr-3-env-vars-rename` | ✅ | `035c92a` | `CENTINELA_*` → `LUPE_*` in config, cli, bridge |
| PR-4 | `feature/pr-4-xdg-paths` | ✅ | `be012b7` | `platformdirs` integration, XDG-compliant paths |
| PR-5 | `feature/pr-5-db-migration` | ✅ | `79dc914` | `lupe migrate-from-centinela` command with backup |
| PR-6 | `feature/pr-6-tui-scaffold` | ✅ | `fe3e7a8` | Textual TUI with 6 screens, dark theme, key bindings |
| PR-7 | `feature/pr-7-tui-settings` | ✅ | `4b8a0e9` | SettingsScreen with validation, persistence, signup links |
| PR-8 | `feature/pr-8-multi-llm` | ✅ | `e36a6e4` | Multi-LLM strategy: Ollama/OpenAI/Anthropic/OpenRouter |
| PR-9 | `feature/pr-9-logo-assets` | ✅ | `fd0c150` | SVG logo, mono variant, .desktop, manpage |
| PR-10 | `feature/pr-10-misp` | ✅ | `dfe89d4` | MISP client (httpx raw) + CLI pull/push |
| PR-11..15 | `feature/pr-11-15-plugins` | ✅ | `d510255` | 5 new plugins: Blocklist.de, Spamhaus, crt.sh, Hybrid Analysis, Censys |
| PR-16 | `feature/pr-16-security-hardening` | ✅ | `5634e5d` | Security: redaction, validation, HTTPS-only, rate limit, pre-commit |
| PR-17 | `feature/pr-17-ci-cd` | ✅ | `8e5d873` | CI/CD: matrix CI, release, CodeQL, dependency review, templates |

## Phase 3 PR Details

### PR-16: Security Hardening
- **Commit**: `5634e5d`
- **Files**: `lupe/security/__init__.py`, `lupe/security/redact.py`, `lupe/security/validation.py`, `lupe/security/https_only.py`, `lupe/security/rate_limit.py`, `.pre-commit-config.yaml`, `pyproject.toml`, `tests/test_security.py`
- **Lines**: +456 / -1
- **Tests**: 31 new (test_security.py)
- **TDD**: ✅ RED → GREEN → REFACTOR

### PR-17: CI/CD Workflows
- **Commit**: `8e5d873`
- **Files**: `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/workflows/codeql.yml`, `.github/workflows/dependency-review.yml`, `.github/dependabot.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `pyproject.toml`
- **Lines**: +316
- **Tests**: 0 (config files, no runtime code)

## Phase 2 PR Details

### PR-8: Multi-LLM Strategy Pattern (PRIORIDAD 1)
- **Commit**: `e36a6e4`
- **Files**: `lupe/llm/base.py`, `lupe/llm/registry.py`, `lupe/llm/null.py`, `lupe/llm/ollama.py`, `lupe/llm/openai.py`, `lupe/llm/anthropic.py`, `lupe/llm/openrouter.py`, `lupe/analysis.py`, `lupe/config.py`
- **Lines**: +1,196 / -33
- **Tests**: 35 new (test_llm_base.py, test_llm_providers.py)
- **TDD**: ✅ RED → GREEN → REFACTOR

### PR-6: TUI Scaffold
- **Commit**: `fe3e7a8`
- **Files**: `lupe/tui/app.py`, `lupe/tui/theme.py`, `lupe/tui/screens/home.py`, `lupe/tui/screens/enrich.py`, `lupe/tui/screens/settings.py`, `lupe/tui/screens/misp.py`, `lupe/tui/screens/plugins.py`, `lupe/tui/screens/cases.py`, `pyproject.toml`
- **Lines**: +559 / -1
- **Tests**: 15 new (test_tui_screens.py)
- **TDD**: ✅ RED → GREEN → REFACTOR

### PR-7: TUI Settings Panel
- **Commit**: `4b8a0e9`
- **Files**: `lupe/tui/screens/settings.py`
- **Lines**: +422 / -5
- **Tests**: 19 new (test_tui_settings.py)
- **TDD**: ✅ RED → GREEN → REFACTOR

### PR-10: MISP Integration
- **Commit**: `dfe89d4`
- **Files**: `lupe/integrations/misp.py`, `lupe/cli.py`
- **Lines**: +494
- **Tests**: 11 new (test_misp_client.py)
- **TDD**: ✅ RED → GREEN → REFACTOR

### PR-9: Logo + Branding Assets
- **Commit**: `fd0c150`
- **Files**: `assets/lupe-logo/lupe-logo.svg`, `assets/lupe-logo/lupe-logo-mono.svg`, `lupe/desktop/lupe.desktop`, `man/lupe.1`, `pyproject.toml`
- **Lines**: +317
- **Tests**: 10 new (test_logo_assets.py)
- **Assets**: SVG logo (512x512), mono variant, .desktop file, groff manpage
- **Logo generation**: Programmatic SVG (XML-based), no external tool needed

### PR-11..15: Five New Enrichment Plugins
- **Commit**: `d510255`
- **Files**: `lupe/enrichment/blocklist_de.py`, `lupe/enrichment/spamhaus.py`, `lupe/enrichment/crtsh.py`, `lupe/enrichment/hybrid_analysis.py`, `lupe/enrichment/censys.py`, `lupe/enrichment/__init__.py`, `lupe/config.py`
- **Lines**: +939
- **Tests**: 31 new (test_plugins_new.py)
- **TDD**: ✅ RED → GREEN → REFACTOR

## Metrics

- **Total tasks completed**: 53/53 (Phases 1-3)
- **Total commits**: 16 (14 feature commits + 2 merge commits in Phase 3, + previous)
- **Total lines changed**: +772 / -1 (Phase 3 only)
- **Cumulative lines**: +5,882 / -1,835 (from main)
- **Tests passing**: 305 (was 274 baseline → +31 new)
- **Tests skipped**: 2 (chmod on Windows + Windows path test)
- **Coverage**: baseline set at `fail_under=25` in pyproject.toml

## TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| 8.1-8.9 | `test_llm_base.py`, `test_llm_providers.py` | Unit | ✅ | ✅ | ✅ |
| 6.1-6.7 | `test_tui_screens.py` | Unit | ✅ | ✅ | ✅ |
| 7.1-7.6 | `test_tui_settings.py` | Unit | ✅ | ✅ | ✅ |
| 10.1-10.6 | `test_misp_client.py` | Unit | ✅ | ✅ | ✅ |
| 9.1-9.6 | `test_logo_assets.py` | Unit | ✅ | ✅ | ✅ |
| 11.1-11.4 | `test_plugins_new.py` | Unit | ✅ | ✅ | ✅ |
| 12.1-12.5 | `test_plugins_new.py` | Unit | ✅ | ✅ | ✅ |
| 13.1-13.4 | `test_plugins_new.py` | Unit | ✅ | ✅ | ✅ |
| 14.1-14.5 | `test_plugins_new.py` | Unit | ✅ | ✅ | ✅ |
| 15.1-15.5 | `test_plugins_new.py` | Unit | ✅ | ✅ | ✅ |
| 16.1-16.8 | `test_security.py` | Unit | ✅ | ✅ | ✅ |
| 17.1-17.5 | N/A (config files) | Setup | ➖ | ✅ | ➖ |

## Decisions Made (Phase 2)

1. **TUI order override**: PR-7 depends on PR-6 per task dependencies, so executed PR-6 before PR-7 despite user's suggested order
2. **crt.sh early return**: Added `supports()` check before HTTP call to prevent spurious requests for unsupported IOC types
3. **Spamhaus key field**: Added `spamhaus_key` to Settings (not in original config.py spec)
4. **Plugins batch**: PR-11..15 done in single branch for efficiency (all follow same pattern)
5. **SVG logo**: Created programmatically (XML) rather than using image generation tool — functional but may want refinement

## Issues Found

1. **Syntax error in settings.py**: Stray quote on line 38 (`password=True"`) — caught and fixed in same commit
2. **Textual BINDINGS format**: `app.BINDINGS` returns tuples `(key, action, desc)` not named tuples — test adapted
3. **Test timeout**: Full suite takes ~3 minutes due to network-dependent plugin tests with respx

## Decisions Made (Phase 3)

1. **Redact regex minimum length**: `sk-` pattern requires 8+ chars after prefix to avoid false positives on short strings
2. **HTTPS allowlist**: localhost and 127.0.0.1 allowed for Ollama; all other HTTP rejected
3. **Rate limiter**: Token-bucket with asyncio.Lock for thread safety, configurable max_requests/per_seconds
4. **IOC validation**: Per-type max lengths (IPv4=15, domain=253, SHA256=64, URL=2048) + absolute max 4096
5. **Pre-commit hooks**: gitleaks (secrets), ruff (lint+format), bandit (security)
6. **CI matrix**: Ubuntu 22.04/24.04 + Windows + Debian 12 container, Python 3.10-3.12
7. **Release workflow**: cibuildwheel for manylinux + Windows wheels, PyPI via trusted publishing

## Issues Found (Phase 3)

1. **Pre-existing ruff issues**: 143 lint errors in existing code (I001 import sorting, E501 line length, F841 unused vars). Not in scope for PR-16/17 — should be cleaned in a future PR.
2. **pip-audit not installed**: Requires `pip install -e ".[dev]"` first — CI handles this automatically.

## Next Steps (Phase 4)

- PR-18: Docs (README, CONTRIBUTING, CHANGELOG, CLAUDE.md update)

## Status

- **Status**: `ready` — Phase 3 complete, 305 tests passing
- **Ready for Phase 4**: Yes
- **Blocked by**: Nothing
