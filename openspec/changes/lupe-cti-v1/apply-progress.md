# Apply Progress: lupe-cti-v1 — Phase 1 (Foundation)

## Status: `ready` — Phase 1 complete, ready for Phase 2

## PR Summary

| PR | Branch | Status | Commit | Description |
|----|--------|--------|--------|-------------|
| PR-0 | `feature/pr-0-coverage-baseline` | ✅ | `8b204ec` | Added pytest-cov config, 19 new tests for legacy plugins |
| PR-1 | `feature/pr-1-package-rename` | ✅ | `77bbe21` | Renamed `centinela/` → `lupe/`, updated all imports, pyproject.toml |
| PR-2 | `feature/pr-2-cli-rename` | ✅ | `19a6c2b` | CLI name `lupe`, help text, Rich banners rebranded |
| PR-3 | `feature/pr-3-env-vars-rename` | ✅ | `035c92a` | `CENTINELA_*` → `LUPE_*` in config, cli, bridge |
| PR-4 | `feature/pr-4-xdg-paths` | ✅ | `be012b7` | `platformdirs` integration, XDG-compliant paths |
| PR-5 | `feature/pr-5-db-migration` | ✅ | `79dc914` | `lupe migrate-from-centinela` command with backup |

## Metrics

- **Total tasks completed**: 18/18 (Phase 1)
- **Total commits**: 12 (6 PR commits + 6 merge commits)
- **Total lines changed**: +1,123 / -1,804 (net -681 due to removed legacy files)
- **Tests passing**: 152 (was 115 baseline → +37 new)
- **Tests skipped**: 1 (chmod test on Windows — expected)
- **Coverage**: baseline set at `fail_under=25` in pyproject.toml

## Verification Results

### `grep -r "from centinela\." --include="*.py"` → 0 matches ✅
### `grep -r "CENTINELA_" --include="*.py" lupe/` → 2 matches (bridge comments only) ✅
- `lupe/desktop/bridge.py:468` — comment about legacy env var names
- `lupe/desktop/bridge.py:472` — comment example

### Remaining `centinela` string literals (all intentional)
- `lupe/migrate.py` — migration script MUST reference legacy paths
- `lupe/cli.py` — `migrate-from-centinela` command name (by design)
- `lupe/enrichment/google_safebrowsing.py:29` — external API client ID
- `lupe/enrichment/hibp.py:38` — external API User-Agent
- `lupe/desktop/` — pywebview frontend (being replaced by TUI in Phase 2)

### `pytest` output
```
152 passed, 1 skipped in 109.22s
```

## Decisions Made

1. **Hatchling wheel config**: Added `[tool.hatch.build.targets.wheel] packages=["lupe"]` because hatchling couldn't auto-detect the renamed package
2. **platformdirs>=4.0**: Used v4.0 minimum (not 3.0) for latest API stability
3. **ENV_PREFIX constant**: Extracted to `lupe/config.py` for reuse
4. **db_path default**: Empty string → platformdirs resolves to `~/.local/share/lupe/lupe.db`
5. **Migration script**: Opt-in only, creates timestamped backup, reports row counts

## TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| 0.1 | `test_coverage_baseline.py` | Unit | ✅ | ✅ | ➖ |
| 0.2 | `test_plugins_legacy.py` | Unit | ✅ | ✅ | ✅ |
| 1.1-1.5 | existing tests | Unit | ✅ | ✅ | ✅ |
| 2.1-2.4 | existing tests | Unit | ✅ | ✅ | ✅ |
| 3.1-3.4 | existing tests | Unit | ✅ | ✅ | ✅ |
| 4.1-4.5 | `test_xdg_paths.py` | Unit | ✅ | ✅ | ✅ |
| 5.1-5.4 | `test_migration.py` | Unit | ✅ | ✅ | ✅ |

## Next Steps (Phase 2)

- PR-6: TUI Scaffold (Textual App)
- PR-8: Multi-LLM Strategy Pattern (before PR-6 per decision)
- PR-7: TUI Settings Panel (after PR-6)
- PR-9: Logo + Branding Assets
