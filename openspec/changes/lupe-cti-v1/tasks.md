# Tasks: Lupe CTI v1 — Rebrand + Multi-LLM + Security Hardening + Distro Packaging

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 2,000 – 2,800 (additions + deletions) |
| 400-line budget risk | **High** |
| Chained PRs recommended | **Yes** |
| Suggested split | PR-0 → PR-1 → PR-2/3/4 (parallel) → PR-5/6/8/9 (parallel) → PR-7 → PR-10 → PR-11..15 (parallel) → PR-16 → PR-17 → PR-18 |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

## Suggested Work Units (PRs)

| PR | Name | Tasks | Goal (1 línea) | Est. Total | Base Branch |
|---|---|---|---|---|---|
| PR-0 | `test/coverage-baseline` | 0.1–0.3 | Medir coverage actual y cerrar gaps en plugins legacy antes de tocar código | 4h | `main` |
| PR-1 | `breaking/package-rename` | 1.1–1.5 | `centinela/` → `lupe/`, imports, `pyproject.toml` package name | 6h | `feature/lupe-cti-v1` |
| PR-2 | `feat/cli-rename` | 2.1–2.4 | Entry points `lupe` / `lupe-desktop`, banners Rich, help text | 4h | PR-1 branch |
| PR-3 | `feat/env-vars-rename` | 3.1–3.4 | `CENTINELA_*` → `LUPE_*` hard cut en config y docs | 4h | PR-1 branch |
| PR-4 | `feat/xdg-paths` | 4.1–4.5 | `platformdirs` settings singleton + XDG/Linux + Windows `%LOCALAPPDATA%` | 5h | PR-1 branch |
| PR-5 | `feat/db-migration` | 5.1–5.4 | Comando `lupe migrate-from-centinela` con backup automático | 4h | PR-4 branch |
| PR-6 | `feat/tui-scaffold` | 6.1–6.7 | Textual App base + theme + Home/Enrich/Cases/MISP/Plugins screens + navegación | 8h | PR-1 branch |
| PR-7 | `feat/tui-settings` | 7.1–7.6 | SettingsScreen con API keys, validación en vivo, signup links, persistencia 600 | 8h | PR-6 branch |
| PR-8 | `feat/multi-llm` | 8.1–8.9 | `LLMProvider` ABC + registry + 4 implementaciones + refactor `analysis.py` | 10h | PR-4 branch |
| PR-9 | `feat/logo-assets` | 9.1–9.6 | SVG/PNGs logo, mono variant, integración TUI splash, `.desktop` icon | 6h | `feature/lupe-cti-v1` |
| PR-10 | `feat/misp-client` | 10.1–10.6 | `MISPClient` httpx raw + `lupe misp pull/push` CLI | 8h | PR-8 branch |
| PR-11 | `feat/plugin-blocklist-de` | 11.1–11.4 | `BlocklistDePlugin` IPv4 reputation (gratis, sin key) | 3h | PR-8 branch |
| PR-12 | `feat/plugin-spamhaus` | 12.1–12.5 | `SpamhausPlugin` IP/domain reputation (gratis con key) | 4h | PR-8 branch |
| PR-13 | `feat/plugin-crtsh` | 13.1–13.4 | `CrtShPlugin` certificado transparency para dominios (gratis, sin key) | 3h | PR-8 branch |
| PR-14 | `feat/plugin-hybrid-analysis` | 14.1–14.5 | `HybridAnalysisPlugin` hash/URL sandbox (freemium) | 5h | PR-8 branch |
| PR-15 | `feat/plugin-censys` | 15.1–15.5 | `CensysPlugin` IP/domain/certificates (freemium, id+secret) | 6h | PR-8 branch |
| PR-16 | `feat/security-hardening` | 16.1–16.8 | Redaction, validation, HTTPS-only, rate limit, pre-commit, bandit, pip-audit | 8h | PR-10 branch |
| PR-17 | `feat/ci-cd` | 17.1–17.5 | Matrix CI (Ubuntu/Debian/Windows), release PyPI, CodeQL, dependency review | 6h | PR-16 branch |
| PR-18 | `feat/docs-packaging` | 18.1–18.5 | README, CONTRIBUTING, CHANGELOG, CLAUDE.md update, packaging final | 5h | PR-17 branch |

---

## PR-0: Test Infrastructure & Coverage Baseline

**Goal**: Medir coverage actual y agregar tests a plugins legacy sin cobertura antes de cualquier refactor grande.
**Acceptance Criteria**: `pytest --cov` ejecuta sin errores; coverage report visible; tests legacy plugins existen.
**Verificación**: `pytest --cov=lupe tests/ && coverage report -m`
**Estimación Total**: 4h

### Task 0.1: Instalar pytest-cov y medir baseline

**PR**: PR-0
**Depende de**: none
**Bloquea**: 0.2, 0.3
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_coverage_baseline.py::TestCoverageBaseline::test_pytest_cov_installed`
- Verifica que `pytest --cov` no falle por falta de plugin.
- No requiere mock.

**GREEN — Implementación mínima**:
- Modificar `pyproject.toml` / `requirements-dev.txt`: agregar `pytest-cov>=5.0`
- Agregar sección `[tool.coverage.run]` en `pyproject.toml` (source=`lupe`, omit=`tests/*`)

**REFACTOR — Mejoras**:
- Agregar `.coverage` a `.gitignore`.

**Verificación**:
- `pytest --cov=lupe tests/ -q`
- `ruff check pyproject.toml`

**Rollback**:
- Revertir commit; eliminar dependencia si falla en CI.

### Task 0.2: Escribir tests para plugins legacy sin cobertura

**PR**: PR-0
**Depende de**: 0.1
**Bloquea**: 0.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_plugins_legacy.py::TestWhoisPlugin::test_enrich_ipv4`
- Verifica que `WhoisPlugin` responde con `EnrichmentResult` para `8.8.8.8` (mockeado).
- Mockear `httpx.AsyncClient.get` con `respx`.

**GREEN — Implementación mínima**:
- Crear `tests/test_plugins_legacy.py` con clases `TestWhoisPlugin`, `TestIpInfoPlugin`, `TestThreatFoxPlugin`.
- Cada test usa `@respx.mock` y responde con JSON/HTTP 200 fixture.

**REFACTOR — Mejoras**:
- Extraer fixtures comunes a `tests/conftest.py`.

**Verificación**:
- `pytest tests/test_plugins_legacy.py -v`
- `bandit -r tests/`

**Rollback**:
- Eliminar `tests/test_plugins_legacy.py` si introduce dependencias rotas.

### Task 0.3: Documentar coverage baseline en repo

**PR**: PR-0
**Depende de**: 0.2
**Bloquea**: none
**Estimación**: S
**Tipo**: docs

**RED — Test que debe fallar**: N/A (docs task)

**GREEN — Implementación mínima**:
- Agregar badge/estado a `README.md` temporal o `CLAUDE.md` con comando para correr coverage.

**REFACTOR — Mejoras**:
- Integrar con CI en PR-17.

**Verificación**:
- `pytest --cov=lupe tests/ --cov-report=term-missing`

**Rollback**:
- Revertir cambio de documentación.

---

## PR-1: Package Rename (`centinela` → `lupe`)

**Goal**: Renombrar el package Python y todas las referencias internas sin backward compat.
**Acceptance Criteria**: `pip install -e .` funciona; `from lupe.ioc_detect import detect_ioc` resuelve; `from centinela...` falla con `ImportError`.
**Verificación**: `python -c "from lupe.cli import app; print('ok')" && python -c "from centinela.cli import app" 2>&1 | grep ImportError`
**Estimación Total**: 6h

### Task 1.1: Renombrar directorio `centinela/` → `lupe/`

**PR**: PR-1
**Depende de**: none (after PR-0 merge)
**Bloquea**: 1.2, 1.3, 1.4, 1.5
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_package_rename.py::TestPackageRename::test_old_import_fails`
- `from centinela.ioc_detect import detect_ioc` debe lanzar `ModuleNotFoundError`.

**GREEN — Implementación mínima**:
- `git mv centinela/ lupe/`

**REFACTOR — Mejoras**:
- N/A (movimiento puro).

**Verificación**:
- `python -c "import lupe"` (éxito)
- `python -c "import centinela"` (fallo)

**Rollback**:
- `git mv lupe/ centinela/`

### Task 1.2: Actualizar todos los imports internos `centinela.` → `lupe.`

**PR**: PR-1
**Depende de**: 1.1
**Bloquea**: 1.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_package_rename.py::TestPackageRename::test_new_imports_resolve`
- Iterar sobre módulos clave (`cli`, `db`, `config`, `analysis`, `ioc_detect`, `enrichment.base`) y verificar que se importan desde `lupe.`.

**GREEN — Implementación mínima**:
- Reemplazo global en `lupe/**/*.py`: `from centinela.` → `from lupe.` y `import centinela` → `import lupe`.
- Archivos afectados: `lupe/cli.py`, `lupe/db.py`, `lupe/config.py`, `lupe/analysis.py`, `lupe/ioc_detect.py`, `lupe/enrichment/base.py`, `lupe/enrichment/__init__.py`, etc.

**REFACTOR — Mejoras**:
- Verificar que no queden strings literales con `"centinela"` que deban ser `"lupe"` (ej. nombres de archivo estáticos).

**Verificación**:
- `pytest tests/test_package_rename.py -v`
- `grep -r "from centinela" lupe/ || echo "clean"`

**Rollback**:
- Revertir commit de reemplazo.

### Task 1.3: Actualizar `pyproject.toml` package name y build config

**PR**: PR-1
**Depende de**: 1.2
**Bloquea**: 1.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_package_rename.py::TestPackageRename::test_pip_install_new_name`
- Verifica que `pyproject.toml` contiene `name = "lupe-cti"`.

**GREEN — Implementación mínima**:
- Modificar `pyproject.toml`:
  - `name = "lupe-cti"`
  - `[project.scripts]`: `lupe = "lupe.cli:app"`, `lupe-desktop = "lupe.tui.app:run"` (o placeholder)
  - `packages = ["lupe"]`

**REFACTOR — Mejoras**:
- Actualizar `description`, `urls.Homepage` si aplica.

**Verificación**:
- `pip install -e .` (éxito)
- `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert d['project']['name']=='lupe-cti'"`

**Rollback**:
- Revertir `pyproject.toml`.

### Task 1.4: Actualizar imports en `tests/`

**PR**: PR-1
**Depende de**: 1.3
**Bloquea**: 1.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_package_rename.py::TestPackageRename::test_tests_import_lupe`
- `pytest tests/` falla si hay imports `centinela` en tests.

**GREEN — Implementación mínima**:
- Reemplazo global en `tests/**/*.py`: `from centinela.` → `from lupe.`.

**REFACTOR — Mejoras**:
- Revisar fixtures en `conftest.py`.

**Verificación**:
- `pytest tests/ -q`
- `grep -r "from centinela" tests/ || echo "clean"`

**Rollback**:
- Revertir cambios en tests.

### Task 1.5: Eliminar archivos legacy (`centinela-desktop.py`, HTML frontend)

**PR**: PR-1
**Depende de**: 1.4
**Bloquea**: none
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_package_rename.py::TestPackageRename::test_legacy_files_removed`
- Verifica que `centinela-desktop.py` y `centinela_kimi_frontend.html` no existen.

**GREEN — Implementación mínima**:
- `git rm centinela-desktop.py centinela_kimi_frontend.html` (si existen en repo).

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `test -f centinela-desktop.py && exit 1 || exit 0`

**Rollback**:
- `git checkout -- centinela-desktop.py centinela_kimi_frontend.html` si es necesario.

---

## PR-2: CLI Rename (`centinela` → `lupe`)

**Goal**: Entry points, comando `lupe`, Rich banners, help text rebranded.
**Acceptance Criteria**: `lupe --help` muestra "Lupe CTI"; `lupe enrich 8.8.8.8` funciona; `centinela` no está en PATH.
**Verificación**: `lupe --help | grep "Lupe CTI" && lupe enrich --help`
**Estimación Total**: 4h

### Task 2.1: Renombrar entry points en `pyproject.toml`

**PR**: PR-2
**Depende de**: PR-1 (merge)
**Bloquea**: 2.2, 2.3, 2.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_cli_rename.py::TestCliRename::test_entry_points_registered`
- Verifica que `import importlib.metadata; eps = importlib.metadata.entry_points(group='console_scripts'); assert 'lupe' in [e.name for e in eps]`.

**GREEN — Implementación mínima**:
- `[project.scripts]`:
  - `lupe = "lupe.cli:main"`
  - `lupe-desktop = "lupe.tui.app:run"` (o `lupe.tui.app:main` según API Textual)

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pip install -e .`
- `lupe --help`

**Rollback**:
- Revertir `pyproject.toml` scripts.

### Task 2.2: Actualizar `lupe/cli.py`: comando root, banners, help text

**PR**: PR-2
**Depende de**: 2.1
**Bloquea**: 2.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_cli_rename.py::TestCliRename::test_help_banner_rebrand`
- Ejecuta `subprocess.run(["lupe", "--help"], capture_output=True, text=True)` y busca `"Lupe CTI"` en stdout.

**GREEN — Implementación mínima**:
- En `lupe/cli.py`:
  - `app = typer.Typer(name="lupe", help="Lupe CTI — Cyber Threat Intelligence for OSINT & Forensics")`
  - Banner Rich con `Panel`, colores `#00FF41` y cyan.
  - Renombrar sub-apps: `config_app`, `case_app`, `person_app` mantienen lógica.

**REFACTOR — Mejoras**:
- Extraer banner a función `print_banner(console: Console)`.

**Verificación**:
- `pytest tests/test_cli_rename.py -v`
- `lupe --help`

**Rollback**:
- Revertir `lupe/cli.py`.

### Task 2.3: Migrar subcomandos existentes bajo nuevo nombre

**PR**: PR-2
**Depende de**: 2.2
**Bloquea**: 2.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_cli_rename.py::TestCliRename::test_subcommands_exist`
- Verifica que `lupe config`, `lupe case`, `lupe person`, `lupe enrich`, `lupe email` existen.

**GREEN — Implementación mínima**:
- Actualizar `typer.Typer()` instancias y `app.add_typer()` calls para reflejar nombres limpios.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `lupe config --help && lupe case --help && lupe enrich --help`

**Rollback**:
- Revertir cambios.

### Task 2.4: Verificar que `lupe --help` muestra branding correcto

**PR**: PR-2
**Depende de**: 2.3
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_cli_rename.py::TestCliRename::test_banner_colors_and_text`
- Verifica que `lupe --help` contiene strings esperados de branding.

**GREEN — Implementación mínima**:
- Ajustar textos en `cli.py` para que tests pasen.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_cli_rename.py -v`

**Rollback**:
- Revertir textos.

---

## PR-3: Env Vars Rename (`CENTINELA_*` → `LUPE_*`)

**Goal**: Hard cut de prefijo de variables de entorno, sin alias.
**Acceptance Criteria**: `LUPE_VIRUSTOTAL_KEY=xxx` carga; `CENTINELA_VIRUSTOTAL_KEY=xxx` es ignorado.
**Verificación**: `LUPE_VIRUSTOTAL_KEY=vt pytest tests/test_config_lupe.py -v`
**Estimación Total**: 4h

### Task 3.1: Actualizar `lupe/config.py`: `env_prefix` y fields

**PR**: PR-3
**Depende de**: PR-1 (merge)
**Bloquea**: 3.2, 3.3, 3.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_config_lupe.py::TestConfigLupe::test_lupe_prefix_loads`
- `monkeypatch.setenv("LUPE_VIRUSTOTAL_KEY", "vt-123")`; `settings.virustotal_key == "vt-123"`.

**GREEN — Implementación mínima**:
- En `lupe/config.py`:
  - `model_config = SettingsConfigDict(env_prefix="LUPE_", ...)`
  - Renombrar defaults que contenían `CENTINELA_` en docstrings.

**REFACTOR — Mejoras**:
- Extraer constante `ENV_PREFIX = "LUPE_"`.

**Verificación**:
- `pytest tests/test_config_lupe.py -v`
- `ruff check lupe/config.py`

**Rollback**:
- Revertir `lupe/config.py`.

### Task 3.2: Actualizar docstrings y mensajes de error que mencionan `CENTINELA_`

**PR**: PR-3
**Depende de**: 3.1
**Bloquea**: 3.3
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_config_lupe.py::TestConfigLupe::test_no_centinela_references_in_config`
- `grep -i "CENTINELA" lupe/config.py` debe estar vacío.

**GREEN — Implementación mínima**:
- Reemplazo de strings literales `CENTINELA` → `LUPE` en `lupe/config.py`.

**REFACTOR — Mejoras**:
- Revisar otros módulos (`db.py`, `analysis.py`) por strings `CENTINELA`.

**Verificación**:
- `grep -ri "CENTINELA" lupe/ || echo "clean"`

**Rollback**:
- Revertir reemplazo.

### Task 3.3: Actualizar tests de config para usar `monkeypatch` con `LUPE_*`

**PR**: PR-3
**Depende de**: 3.2
**Bloquea**: 3.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_config_lupe.py::TestConfigLupe::test_legacy_prefix_ignored`
- `monkeypatch.setenv("CENTINELA_VIRUSTOTAL_KEY", "old")`; `settings.virustotal_key is None`.

**GREEN — Implementación mínima**:
- Crear `tests/test_config_lupe.py` con tests de carga/ignorancia.

**REFACTOR — Mejoras**:
- Agregar fixture `clear_lupe_env` para limpiar env vars entre tests.

**Verificación**:
- `pytest tests/test_config_lupe.py -v`

**Rollback**:
- Eliminar `tests/test_config_lupe.py`.

### Task 3.4: Actualizar Heimdall bridge y referencias externas

**PR**: PR-3
**Depende de**: 3.3
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**: N/A (código externo dinámico)

**GREEN — Implementación mínima**:
- En `lupe/integrations/agent_writer_bridge.py`:
  - Actualizar `CENTINELA_DASHBOARD_ENABLED` → `LUPE_DASHBOARD_ENABLED`.

**REFACTOR — Mejoras**:
- Documentar breaking change en CHANGELOG (PR-18).

**Verificación**:
- `grep -ri "CENTINELA" lupe/integrations/ || echo "clean"`

**Rollback**:
- Revertir bridge.

---

## PR-4: XDG Paths + Windows Path + Settings Singleton Refactor (`platformdirs`)

**Goal**: `platformdirs` para resolver paths cross-platform; settings singleton usa esos paths.
**Acceptance Criteria**: DB en `~/.local/share/lupe/lupe.db` (Linux), `%LOCALAPPDATA%\Lupe\lupe.db` (Windows); `XDG_DATA_HOME` respetado.
**Verificación**: `pytest tests/test_xdg_paths.py -v`
**Estimación Total**: 5h

### Task 4.1: Agregar `platformdirs` a dependencias

**PR**: PR-4
**Depende de**: PR-1 (merge)
**Bloquea**: 4.2, 4.3, 4.4, 4.5
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_xdg_paths.py::TestXdgPaths::test_platformdirs_importable`
- `import platformdirs` debe funcionar tras install.

**GREEN — Implementación mínima**:
- `pyproject.toml`: agregar `platformdirs>=4.0` a `dependencies`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pip install -e .`
- `python -c "import platformdirs; print(platformdirs.__version__)"`

**Rollback**:
- Revertir `pyproject.toml`.

### Task 4.2: Refactorizar `Settings` para usar `platformdirs` (data/config/cache)

**PR**: PR-4
**Depende de**: 4.1
**Bloquea**: 4.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_xdg_paths.py::TestXdgPaths::test_settings_resolves_data_dir`
- `settings.data_dir.endswith("lupe")` y es absoluto.

**GREEN — Implementación mínima**:
- En `lupe/config.py`:
  - Importar `platformdirs`.
  - En `Settings` o helper: `user_data_dir = platformdirs.user_data_dir("lupe", appauthor=False)`.
  - `user_config_dir = platformdirs.user_config_dir(...)`.
  - `user_cache_dir = platformdirs.user_cache_dir(...)`.

**REFACTOR — Mejoras**:
- Usar `functools.lru_cache` para los helpers de path si son llamados frecuentemente.

**Verificación**:
- `pytest tests/test_xdg_paths.py::TestXdgPaths::test_settings_resolves_data_dir -v`
- `mypy lupe/config.py`

**Rollback**:
- Revertir `lupe/config.py`.

### Task 4.3: Actualizar `lupe/db.py` para usar `platformdirs.user_data_dir`

**PR**: PR-4
**Depende de**: 4.2
**Bloquea**: 4.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_xdg_paths.py::TestXdgPaths::test_db_path_in_xdg`
- `Database().db_path` contiene `user_data_dir / "lupe.db"`.

**GREEN — Implementación mínima**:
- En `lupe/db.py`:
  - Importar `get_settings` o helper de paths.
  - Cambiar default path de `~/.centinela/centinela.db` a `settings.user_data_dir / "lupe.db"`.

**REFACTOR — Mejoras**:
- Extraer `DEFAULT_DB_PATH = lambda: get_settings().user_data_dir / "lupe.db"`.

**Verificación**:
- `pytest tests/test_xdg_paths.py::TestXdgPaths::test_db_path_in_xdg -v`

**Rollback**:
- Revertir `lupe/db.py`.

### Task 4.4: Manejar Windows `%LOCALAPPDATA%` correctamente

**PR**: PR-4
**Depende de**: 4.3
**Bloquea**: 4.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_xdg_paths.py::TestXdgPaths::test_windows_path_format`
- Simular Windows (`monkeypatch.platform = "win32"` o mock `platformdirs._platform`) y verificar que path contiene `Lupe\lupe.db`.

**GREEN — Implementación mínima**:
- `platformdirs` ya maneja esto; solo validar en test que no se usa `os.path.expanduser("~/.local/share")` en Windows.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_xdg_paths.py -v` (en Windows o con mock).

**Rollback**:
- Revertir tests.

### Task 4.5: Tests de resolución de paths XDG y Windows

**PR**: PR-4
**Depende de**: 4.4
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_xdg_paths.py::TestXdgPaths::test_custom_xdg_data_home`
- `monkeypatch.setenv("XDG_DATA_HOME", "/opt/forensics/data")`; DB path = `/opt/forensics/data/lupe/lupe.db`.

**GREEN — Implementación mínima**:
- Completar tests en `tests/test_xdg_paths.py`.

**REFACTOR — Mejoras**:
- Agregar test de `XDG_CONFIG_HOME`.

**Verificación**:
- `pytest tests/test_xdg_paths.py -v`

**Rollback**:
- Eliminar tests.

---

## PR-5: DB Path Migration + Script `lupe migrate-from-centinela`

**Goal**: Comando manual para copiar DB legacy a nueva XDG path con backup automático.
**Acceptance Criteria**: `lupe migrate-from-centinela` copia `~/.centinela/centinela.db` a `~/.local/share/lupe/lupe.db` y crea `.bak`.
**Verificación**: `pytest tests/test_migration.py -v`
**Estimación Total**: 4h

### Task 5.1: Crear `lupe/migrate.py` con comando `migrate-from-centinela`

**PR**: PR-5
**Depende de**: PR-4 (merge)
**Bloquea**: 5.2, 5.3, 5.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_migration.py::TestMigration::test_migrate_command_exists`
- `python -m lupe.migrate` o import de función `migrate_from_centinela()`.

**GREEN — Implementación mínima**:
- Crear `lupe/migrate.py`:
  - `def migrate_from_centinela() -> Path:`
  - Busca `Path.home() / ".centinela" / "centinela.db"`.
  - Si no existe: `sys.exit(1)` con mensaje.
  - Si existe: backup `.bak`, `shutil.copy2()`, reportar filas.

**REFACTOR — Mejoras**:
- Extraer helpers de path legacy a constantes.

**Verificación**:
- `pytest tests/test_migration.py::TestMigration::test_migrate_command_exists -v`
- `bandit -r lupe/migrate.py`

**Rollback**:
- Eliminar `lupe/migrate.py`.

### Task 5.2: Backup automático de DB legacy antes de copiar

**PR**: PR-5
**Depende de**: 5.1
**Bloquea**: 5.3
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_migration.py::TestMigration::test_backup_created`
- Tras migración, `centinela.db.bak` existe.

**GREEN — Implementación mínima**:
- En `migrate_from_centinela()`: si `legacy_db.exists()`, crear `legacy_db.with_suffix(".db.bak")` (o timestamp) antes de copy.

**REFACTOR — Mejoras**:
- Usar timestamp para no sobrescribir backups previos.

**Verificación**:
- `pytest tests/test_migration.py::TestMigration::test_backup_created -v`

**Rollback**:
- Revertir lógica de backup.

### Task 5.3: Tests de migración: copy, backup, verificación de integridad

**PR**: PR-5
**Depende de**: 5.2
**Bloquea**: 5.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_migration.py::TestMigration::test_data_integrity_after_migration`
- Crea DB legacy fake con SQLite, migra, verifica que tablas y row counts coinciden.

**GREEN — Implementación mínima**:
- En `tests/test_migration.py`:
  - Fixture `fake_legacy_db(tmp_path)` crea `centinela.db` con schema mínimo y datos.
  - Llama `migrate_from_centinela(src=..., dst=...)`.
  - Compara `PRAGMA user_version` y `SELECT count(*) FROM iocs`.

**REFACTOR — Mejoras**:
- Agregar test de idempotencia (migrar dos veces no rompe).

**Verificación**:
- `pytest tests/test_migration.py -v`

**Rollback**:
- Eliminar tests.

### Task 5.4: Agregar subcomando `lupe migrate-from-centinela` en `cli.py`

**PR**: PR-5
**Depende de**: 5.3
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_migration.py::TestMigration::test_cli_subcommand_runs`
- `subprocess.run(["lupe", "migrate-from-centinela"], ...)` y verifica exit code 0 o 1 según exista legacy.

**GREEN — Implementación mínima**:
- En `lupe/cli.py`: `@app.command(name="migrate-from-centinela") def migrate_command(): ...`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_migration.py::TestMigration::test_cli_subcommand_runs -v`
- `lupe migrate-from-centinela --help`

**Rollback**:
- Revertir `cli.py`.

---

## PR-6: TUI Scaffold (Textual App + Theme + Navegación)

**Goal**: Textual TUI base que reemplace pywebview; funciona en SSH/headless.
**Acceptance Criteria**: `lupe-desktop` lanza TUI; navegación entre screens funciona; colores correctos.
**Verificación**: `pytest tests/test_tui_screens.py -v` + `textual run lupe.tui.app` (smoke test)
**Estimación Total**: 8h

### Task 6.1: Agregar `textual` a dependencias

**PR**: PR-6
**Depende de**: PR-1 (merge)
**Bloquea**: 6.2–6.7
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiApp::test_textual_importable`
- `import textual` funciona.

**GREEN — Implementación mínima**:
- `pyproject.toml`: `dependencies` += `textual>=0.50`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pip install -e ".[dev]"`
- `python -c "import textual; print(textual.__version__)"`

**Rollback**:
- Revertir `pyproject.toml`.

### Task 6.2: Crear `lupe/tui/app.py` con Textual App base

**PR**: PR-6
**Depende de**: 6.1
**Bloquea**: 6.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiApp::test_app_instantiates`
- `app = LupeTuiApp(); assert app.title == "Lupe CTI"`.

**GREEN — Implementación mínima**:
- Crear `lupe/tui/app.py`:
  - `class LupeTuiApp(App): BINDINGS = [("q", "quit", "Quit")]; CSS_PATH = "theme.tcss"`
  - `def compose(self) -> ComposeResult: yield Header(); yield Footer()`

**REFACTOR — Mejoras**:
- Agregar `push_screen("home")` en `on_mount`.

**Verificación**:
- `pytest tests/test_tui_screens.py::TestTuiApp::test_app_instantiates -v`

**Rollback**:
- Eliminar `lupe/tui/app.py`.

### Task 6.3: Crear `lupe/tui/theme.py` con paleta de colores

**PR**: PR-6
**Depende de**: 6.2
**Bloquea**: 6.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiApp::test_theme_colors_defined`
- Verifica que `theme.py` tiene constantes `MATRIX_GREEN = "#00FF41"`, `CYAN_ACCENT = "#00FFFF"`, etc.

**GREEN — Implementación mínima**:
- Crear `lupe/tui/theme.py`:
  - `MATRIX_GREEN = "#00FF41"`
  - `CYAN = "#00FFFF"`
  - `DARK_BG = "#0d1117"`
  - `ERROR_RED = "#ff5555"`

**REFACTOR — Mejoras**:
- Definir dataclass `LupeTheme` con todos los tokens.

**Verificación**:
- `pytest tests/test_tui_screens.py::TestTuiApp::test_theme_colors_defined -v`

**Rollback**:
- Eliminar `theme.py`.

### Task 6.4: Crear `HomeScreen` básica

**PR**: PR-6
**Depende de**: 6.3
**Bloquea**: 6.5
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiScreens::test_home_screen_renders`
- Montar `HomeScreen` y verificar que contiene `Static("Lupe CTI Dashboard")`.

**GREEN — Implementación mínima**:
- Crear `lupe/tui/screens/home.py`:
  - `class HomeScreen(Screen): def compose(self): yield Static("Lupe CTI Dashboard"); yield Button("Enrich", id="btn-enrich")`

**REFACTOR — Mejoras**:
- Agregar logo ASCII al header.

**Verificación**:
- `pytest tests/test_tui_screens.py::TestTuiScreens::test_home_screen_renders -v`

**Rollback**:
- Eliminar screen.

### Task 6.5: Crear navegación entre screens (Tab / key bindings)

**PR**: PR-6
**Depende de**: 6.4
**Bloquea**: 6.6
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiScreens::test_navigation_switches_screens`
- Simular key press `Tab` o binding y verificar `app.screen.name` cambia.

**GREEN — Implementación mínima**:
- En `lupe/tui/app.py`:
  - `BINDINGS += [("1", "push_screen('home')", "Home"), ("2", "push_screen('enrich')", "Enrich"), ...]`
- Crear placeholders `lupe/tui/screens/enrich.py`, `settings.py`, `misp.py`, `plugins.py`, `cases.py`.

**REFACTOR — Mejoras**:
- Usar `TabbedContent` o `Screen` stack según UX.

**Verificación**:
- `pytest tests/test_tui_screens.py::TestTuiScreens::test_navigation_switches_screens -v`

**Rollback**:
- Revertir bindings y placeholders.

### Task 6.6: Entry point `lupe-desktop` lanza TUI

**PR**: PR-6
**Depende de**: 6.5
**Bloquea**: 6.7
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiApp::test_lupe_desktop_entrypoint`
- `subprocess.run(["lupe-desktop", "--help"])` o import de `main()`.

**GREEN — Implementación mínima**:
- En `lupe/tui/app.py`: `def run(): LupeTuiApp().run()`.
- En `pyproject.toml`: `lupe-desktop = "lupe.tui.app:run"`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `lupe-desktop --help` (smoke)
- `pytest tests/test_tui_screens.py::TestTuiApp::test_lupe_desktop_entrypoint -v`

**Rollback**:
- Revertir entry point.

### Task 6.7: Tests de renderizado de TUI screens (snapshot)

**PR**: PR-6
**Depende de**: 6.6
**Bloquea**: none
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiScreens::test_all_screens_mount`
- Itera over screen names y verifica que cada screen se puede montar sin excepción.

**GREEN — Implementación mínima**:
- Completar tests con `app.push_screen(name)` para cada screen.

**REFACTOR — Mejoras**:
- Usar `textual.snapshot` si está disponible (v1.0+).

**Verificación**:
- `pytest tests/test_tui_screens.py -v`

**Rollback**:
- Revertir tests.

---

## PR-7: TUI Settings Panel

**Goal**: Settings screen con API keys, validación en vivo, signup links, persistencia chmod 600.
**Acceptance Criteria**: Campo OpenAI key muestra rojo si no empieza con `sk-`; signup link visible; archivo config tiene permiso 600 en Linux.
**Verificación**: `pytest tests/test_tui_settings.py -v`
**Estimación Total**: 8h

### Task 7.1: Crear `SettingsScreen` con campos de API keys

**PR**: PR-7
**Depende de**: PR-6 (merge)
**Bloquea**: 7.2, 7.3, 7.4, 7.5, 7.6
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_settings.py::TestTuiSettings::test_settings_screen_has_input_fields`
- Montar `SettingsScreen` y contar `Input` widgets >= N (uno por provider/keyed plugin).

**GREEN — Implementación mínima**:
- Crear `lupe/tui/screens/settings.py`:
  - `class SettingsScreen(Screen):`
  - Compose con `Grid` o `VerticalScroll`.
  - Inputs: `ollama_base_url`, `openai_key`, `anthropic_key`, `openrouter_key`, `virustotal_key`, `abuseipdb_key`, `shodan_key`, `otx_key`, `urlscan_key`, `hibp_key`, `greynoise_key`, `ipqs_key`, `numverify_key`, `misp_url`, `misp_key`, `hybrid_analysis_key`, `censys_id`, `censys_secret`.

**REFACTOR — Mejoras**:
- Extraer lista de campos a dataclass/config.

**Verificación**:
- `pytest tests/test_tui_settings.py::TestTuiSettings::test_settings_screen_has_input_fields -v`

**Rollback**:
- Revertir screen.

### Task 7.2: Implementar validación en vivo de formatos (`sk-` prefix, etc.)

**PR**: PR-7
**Depende de**: 7.1
**Bloquea**: 7.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_settings.py::TestTuiSettings::test_openai_key_validation_live`
- Ingresar `"bad-key"` en input OpenAI → borde rojo; ingresar `"sk-abc"` → borde verde.

**GREEN — Implementación mínima**:
- En `SettingsScreen`:
  - `@on(Input.Changed, "#input-openai-key") def on_openai_changed(self, event): ...`
  - Validar regex `^sk-[a-zA-Z0-9]+$`.
  - Aplicar `event.input.styles.border = ("solid", "red")` o `"green"`.

**REFACTOR — Mejoras**:
- Crear `validators.py` con funciones puras para reutilizar en CLI y TUI.

**Verificación**:
- `pytest tests/test_tui_settings.py::TestTuiSettings::test_openai_key_validation_live -v`

**Rollback**:
- Revertir handlers.

### Task 7.3: Agregar signup links por provider en sidebar/help text

**PR**: PR-7
**Depende de**: 7.2
**Bloquea**: 7.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_settings.py::TestTuiSettings::test_signup_link_visible`
- Verificar que al enfocar input de VT, `Static` con `https://www.virustotal.com/gui/join-us` existe.

**GREEN — Implementación mínima**:
- En `SettingsScreen`: diccionario `SIGNUP_URLS = {"virustotal": "...", ...}`.
- Al enfocar input, actualizar `self.query_one("#signup-link").update(url)`.

**REFACTOR — Mejoras**:
- Mover `SIGNUP_URLS` a `lupe/config.py` o JSON constante.

**Verificación**:
- `pytest tests/test_tui_settings.py::TestTuiSettings::test_signup_link_visible -v`

**Rollback**:
- Revertir URLs y handlers.

### Task 7.4: Implementar persistencia segura: escritura a `~/.config/lupe/lupe.toml` con `chmod 600`

**PR**: PR-7
**Depende de**: 7.3
**Bloquea**: 7.5
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_settings.py::TestTuiSettings::test_save_creates_config_file`
- Simular click en "Save" → archivo `lupe.toml` existe en `user_config_dir`.

**GREEN — Implementación mínima**:
- En `SettingsScreen`:
  - `def action_save(self): ...`
  - Leer valores de inputs.
  - Escribir `tomli_w` (o `toml`) a `platformdirs.user_config_dir("lupe") / "lupe.toml"`.
  - `os.chmod(path, 0o600)` en Linux.

**REFACTOR — Mejoras**:
- Usar `tempfile.atomic_write` para evitar corrupción.

**Verificación**:
- `pytest tests/test_tui_settings.py::TestTuiSettings::test_save_creates_config_file -v`
- `bandit -r lupe/tui/screens/settings.py`

**Rollback**:
- Revertir save logic.

### Task 7.5: Fallback de permisos en Windows

**PR**: PR-7
**Depende de**: 7.4
**Bloquea**: 7.6
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_settings.py::TestTuiSettings::test_windows_no_chmod_crash`
- En Windows, `os.chmod` con 600 no lanza excepción (o se ignora gracefully).

**GREEN — Implementación mínima**:
- `if sys.platform != "win32": os.chmod(path, 0o600)`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_tui_settings.py::TestTuiSettings::test_windows_no_chmod_crash -v`

**Rollback**:
- Revertir fallback.

### Task 7.6: Tests de `SettingsScreen` y persistencia

**PR**: PR-7
**Depende de**: 7.5
**Bloquea**: none
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_settings.py::TestTuiSettings::test_load_populates_inputs`
- Crear `lupe.toml` fake; montar screen; verificar inputs cargan valores.

**GREEN — Implementación mínima**:
- Implementar `action_load(self)` en `SettingsScreen`.
- Tests de round-trip save/load.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_tui_settings.py -v`

**Rollback**:
- Revertir tests/load.

---

## PR-8: Multi-LLM Strategy Pattern

**Goal**: `LLMProvider` ABC + 4 providers + registry + refactor de `analysis.py`.
**Acceptance Criteria**: `LUPE_LLM_PROVIDER=openai` usa OpenAI; vacío → skip AI; provider inválido → warning.
**Verificación**: `pytest tests/test_llm_base.py tests/test_llm_providers.py -v`
**Estimación Total**: 10h

### Task 8.1: Crear `LLMProvider` ABC en `lupe/llm/base.py`

**PR**: PR-8
**Depende de**: PR-4 (merge)
**Bloquea**: 8.2–8.9
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_base.py::TestLLMBase::test_abc_cannot_instantiate`
- `LLMProvider()` lanza `TypeError`.

**GREEN — Implementación mínima**:
- Crear `lupe/llm/base.py`:
  - `class LLMProvider(ABC): ...` con `name`, `requires_api_key`.
  - `@abstractmethod async def generate(self, prompt: str, *, system: str | None = None) -> str`
  - `@abstractmethod async def stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]`
  - `@abstractmethod async def validate_key(self) -> bool`
  - `@abstractmethod def list_models(self) -> list[ModelInfo]`

**REFACTOR — Mejoras**:
- Agregar `from_settings()` classmethod en ABC para factory uniforme.

**Verificación**:
- `pytest tests/test_llm_base.py::TestLLMBase::test_abc_cannot_instantiate -v`
- `mypy lupe/llm/base.py`

**Rollback**:
- Eliminar `lupe/llm/base.py`.

### Task 8.2: Crear registry + factory en `lupe/llm/registry.py`

**PR**: PR-8
**Depende de**: 8.1
**Bloquea**: 8.3
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_base.py::TestLLMBase::test_registry_factory_returns_provider`
- `get_provider("ollama", settings)` retorna instancia de `OllamaProvider`.

**GREEN — Implementación mínima**:
- Crear `lupe/llm/registry.py`:
  - `_PROVIDERS: dict[str, type[LLMProvider]] = {}`
  - `register_provider(cls)` decorator.
  - `get_provider(name: str, settings: Settings) -> LLMProvider | None`.

**REFACTOR — Mejoras**:
- Auto-registro con `__init_subclass__` en lugar de decorator manual.

**Verificación**:
- `pytest tests/test_llm_base.py::TestLLMBase::test_registry_factory_returns_provider -v`

**Rollback**:
- Eliminar `registry.py`.

### Task 8.3: Implementar `OllamaProvider`

**PR**: PR-8
**Depende de**: 8.2
**Bloquea**: 8.7
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_providers.py::TestOllamaProvider::test_generate_success`
- Mockear `POST /v1/chat/completions` con respx; `generate("analyze 8.8.8.8")` retorna texto.

**GREEN — Implementación mínima**:
- Crear `lupe/llm/ollama.py`:
  - `class OllamaProvider(LLMProvider): name = "ollama"; requires_api_key = False`
  - `generate()` usa `httpx.AsyncClient` a `settings.ollama_base_url`.

**REFACTOR — Mejoras**:
- Reutilizar client pool.

**Verificación**:
- `pytest tests/test_llm_providers.py::TestOllamaProvider::test_generate_success -v`

**Rollback**:
- Eliminar `ollama.py`.

### Task 8.4: Implementar `OpenAIProvider`

**PR**: PR-8
**Depende de**: 8.2
**Bloquea**: 8.7
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_providers.py::TestOpenAIProvider::test_generate_success`
- Mockear `api.openai.com/v1/chat/completions`.

**GREEN — Implementación mínima**:
- Crear `lupe/llm/openai.py`:
  - `class OpenAIProvider(LLMProvider): name = "openai"`
  - Header `Authorization: Bearer {key}`.

**REFACTOR — Mejoras**:
- Extraer helper `_chat_completion_payload`.

**Verificación**:
- `pytest tests/test_llm_providers.py::TestOpenAIProvider -v`

**Rollback**:
- Eliminar `openai.py`.

### Task 8.5: Implementar `AnthropicProvider`

**PR**: PR-8
**Depende de**: 8.2
**Bloquea**: 8.7
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_providers.py::TestAnthropicProvider::test_generate_success`
- Mockear `api.anthropic.com/v1/messages`.

**GREEN — Implementación mínima**:
- Crear `lupe/llm/anthropic.py`:
  - `class AnthropicProvider(LLMProvider): name = "anthropic"`
  - Header `x-api-key: {key}`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_llm_providers.py::TestAnthropicProvider -v`

**Rollback**:
- Eliminar `anthropic.py`.

### Task 8.6: Implementar `OpenRouterProvider`

**PR**: PR-8
**Depende de**: 8.2
**Bloquea**: 8.7
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_providers.py::TestOpenRouterProvider::test_generate_success`
- Mockear `openrouter.ai/api/v1/chat/completions`.

**GREEN — Implementación mínima**:
- Crear `lupe/llm/openrouter.py`:
  - `class OpenRouterProvider(LLMProvider): name = "openrouter"`
  - Usa `settings.openrouter_base_url` default.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_llm_providers.py::TestOpenRouterProvider -v`

**Rollback**:
- Eliminar `openrouter.py`.

### Task 8.7: Refactorizar `analysis.py` para delegar a `LLMProvider`

**PR**: PR-8
**Depende de**: 8.3–8.6
**Bloquea**: 8.8, 8.9
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_base.py::TestLLMBase::test_analysis_delegates_to_provider`
- `analyze_ioc(..., settings)` llama a `provider.generate()` si provider configurado.

**GREEN — Implementación mínima**:
- Modificar `lupe/analysis.py`:
  - `from lupe.llm.registry import get_provider`
  - `async def analyze_ioc(ioc: IOC, results: list[EnrichmentResult], settings: Settings) -> str | None:`
  - Si `settings.llm_provider` vacío: return None.
  - `provider = get_provider(settings.llm_provider, settings)`; si None: log warning; return None.
  - `return await provider.generate(prompt=...)`.

**REFACTOR — Mejoras**:
- Eliminar código Ollama hardcoded anterior.

**Verificación**:
- `pytest tests/test_llm_base.py::TestLLMBase::test_analysis_delegates_to_provider -v`

**Rollback**:
- Revertir `analysis.py`.

### Task 8.8: Tests de contrato ABC y de cada provider con respx

**PR**: PR-8
**Depende de**: 8.7
**Bloquea**: 8.9
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_providers.py::TestAllProviders::test_validate_key_false_on_401`
- Cada provider con respx mock 401 → `validate_key()` retorna `False`.

**GREEN — Implementación mínima**:
- Completar tests de error handling en cada provider.

**REFACTOR — Mejoras**:
- Fixture `provider_settings` parametrizada.

**Verificación**:
- `pytest tests/test_llm_providers.py -v`

**Rollback**:
- Revertir tests.

### Task 8.9: Tests de selección de provider por `LUPE_LLM_PROVIDER`

**PR**: PR-8
**Depende de**: 8.8
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_llm_base.py::TestLLMBase::test_invalid_provider_logs_warning`
- `settings.llm_provider = "unknown"` → warning en logs.

**GREEN — Implementación mínima**:
- Completar tests de selección.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_llm_base.py -v`

**Rollback**:
- Revertir tests.

---

## PR-9: Logo + Branding Assets

**Goal**: SVG primario, PNGs 256/128/64/32/16, mono variant, integración TUI y `.desktop`.
**Acceptance Criteria**: `assets/logo/lupe-logo.svg` existe; PNGs renderizan; TUI splash muestra ASCII art derivado.
**Verificación**: Smoke visual + `pytest tests/test_logo_assets.py -v`
**Estimación Total**: 6h

### Task 9.1: Crear `assets/logo/lupe-logo.svg`

**PR**: PR-9
**Depende de**: none
**Bloquea**: 9.2, 9.3, 9.4, 9.5, 9.6
**Estimación**: M
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_logo_assets.py::TestLogoAssets::test_svg_exists`
- `Path("assets/logo/lupe-logo.svg").exists()`.

**GREEN — Implementación mínima**:
- Crear `assets/logo/lupe-logo.svg` con lupa abstracta, binario matrix verde (#00FF41), auriculares cruzados, fondo oscuro.

**REFACTOR — Mejoras**:
- Optimizar con `svgo`.

**Verificación**:
- `pytest tests/test_logo_assets.py::TestLogoAssets::test_svg_exists -v`

**Rollback**:
- `git rm assets/logo/lupe-logo.svg`.

### Task 9.2: Exportar PNGs en 256/128/64/32/16

**PR**: PR-9
**Depende de**: 9.1
**Bloquea**: 9.4, 9.6
**Estimación**: M
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_logo_assets.py::TestLogoAssets::test_png_sizes_exist`
- `Path(f"assets/logo/lupe-logo-{size}.png").exists()` para cada tamaño.

**GREEN — Implementación mínima**:
- Exportar PNGs desde SVG usando `cairosvg` o Inkscape CLI en build step.
- O generar manualmente y versionar.

**REFACTOR — Mejoras**:
- Script `scripts/render_logos.py` para regenerar.

**Verificación**:
- `pytest tests/test_logo_assets.py::TestLogoAssets::test_png_sizes_exist -v`

**Rollback**:
- Eliminar PNGs.

### Task 9.3: Crear `lupe-logo-mono.svg`

**PR**: PR-9
**Depende de**: 9.1
**Bloquea**: 9.5
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_logo_assets.py::TestLogoAssets::test_mono_svg_exists`
- `assets/logo/lupe-logo-mono.svg` existe.

**GREEN — Implementación mínima**:
- Crear versión monocromática del SVG (solo paths, sin fills de color).

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_logo_assets.py::TestLogoAssets::test_mono_svg_exists -v`

**Rollback**:
- Eliminar mono SVG.

### Task 9.4: Integrar logo en TUI splash/header

**PR**: PR-9
**Depende de**: 9.2
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_tui_screens.py::TestTuiApp::test_splash_contains_lupe_text`
- Verificar que `HomeScreen` contiene texto/ASCII "Lupe" o referencia al logo.

**GREEN — Implementación mínima**:
- En `lupe/tui/screens/home.py`: agregar `Static(logo_ascii, id="logo")`.

**REFACTOR — Mejoras**:
- Cargar ASCII desde archivo para no ensuciar código.

**Verificación**:
- `pytest tests/test_tui_screens.py::TestTuiApp::test_splash_contains_lupe_text -v`

**Rollback**:
- Revertir splash.

### Task 9.5: Referenciar logo en `pyproject.toml` URLs

**PR**: PR-9
**Depende de**: 9.3
**Bloquea**: none
**Estimación**: S
**Tipo**: docs

**RED — Test que debe fallar**: N/A

**GREEN — Implementación mínima**:
- `pyproject.toml`: `[project.urls]` → `Logo = "https://raw.githubusercontent.com/.../assets/logo/lupe-logo.svg"`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['urls'])"`

**Rollback**:
- Revertir URLs.

### Task 9.6: Actualizar `.desktop` con `Icon=`

**PR**: PR-9
**Depende de**: 9.2
**Bloquea**: none
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_logo_assets.py::TestLogoAssets::test_desktop_icon_points_to_logo`
- Parsear `lupe.desktop` y verificar `Icon=` no está vacío.

**GREEN — Implementación mínima**:
- Crear/actualizar `lupe.desktop`:
  - `Icon=/usr/share/pixmaps/lupe-logo.svg` (o path relativo si aplica).

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_logo_assets.py::TestLogoAssets::test_desktop_icon_points_to_logo -v`

**Rollback**:
- Revertir `.desktop`.

---

## PR-10: MISP Client + Comandos CLI

**Goal**: `MISPClient` con httpx raw + `lupe misp pull/push`.
**Acceptance Criteria**: `lupe misp pull --tag osint --days 7` imprime tabla; push sube IOC.
**Verificación**: `pytest tests/test_misp_client.py -v`
**Estimación Total**: 8h

### Task 10.1: Crear `MISPClient` en `lupe/integrations/misp.py` (httpx raw)

**PR**: PR-10
**Depende de**: PR-8 (merge)
**Bloquea**: 10.2–10.6
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_misp_client.py::TestMISPClient::test_client_instantiates`
- `MISPClient(url="https://misp.example.com", api_key="key")`.

**GREEN — Implementación mínima**:
- Crear `lupe/integrations/misp.py`:
  - `class MISPClient:`
  - `__init__(self, url: str, api_key: str, timeout: float = 30.0)`
  - `self._client = httpx.AsyncClient(base_url=url, headers={"Authorization": api_key, "Accept": "application/json"})`

**REFACTOR — Mejoras**:
- Agregar `__aenter__` / `__aexit__`.

**Verificación**:
- `pytest tests/test_misp_client.py::TestMISPClient::test_client_instantiates -v`

**Rollback**:
- Eliminar `misp.py`.

### Task 10.2: Implementar `get_indicators` con filtros

**PR**: PR-10
**Depende de**: 10.1
**Bloquea**: 10.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_misp_client.py::TestMISPClient::test_get_indicators_returns_iocs`
- Mockear `GET /attributes/restSearch` con respx; retorna lista de `IOC`.

**GREEN — Implementación mínima**:
- `async def get_indicators(self, *, tags: list[str] | None = None, days: int = 7, ioc_type: str | None = None) -> list[IOC]:`
- Parsear JSON MISP y mapear a `lupe.models.IOC`.

**REFACTOR — Mejoras**:
- Extraer parser a función pura.

**Verificación**:
- `pytest tests/test_misp_client.py::TestMISPClient::test_get_indicators_returns_iocs -v`

**Rollback**:
- Revertir `get_indicators`.

### Task 10.3: Implementar `add_indicator` (push)

**PR**: PR-10
**Depende de**: 10.2
**Bloquea**: 10.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_misp_client.py::TestMISPClient::test_add_indicator_returns_uuid`
- Mockear `POST /events/restSearch` + `POST /attributes/add`; retorna UUID.

**GREEN — Implementación mínima**:
- `async def add_indicator(self, ioc: IOC, tags: list[str] | None = None, info: str = "") -> str:`
- Crear evento si no existe; agregar atributo.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_misp_client.py::TestMISPClient::test_add_indicator_returns_uuid -v`

**Rollback**:
- Revertir `add_indicator`.

### Task 10.4: Agregar subcomandos `lupe misp pull` y `lupe misp push`

**PR**: PR-10
**Depende de**: 10.3
**Bloquea**: 10.5, 10.6
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_misp_client.py::TestMISPCLI::test_pull_command_exists`
- `subprocess.run(["lupe", "misp", "pull", "--help"])` exit 0.

**GREEN — Implementación mínima**:
- En `lupe/cli.py`:
  - `misp_app = typer.Typer(name="misp")`
  - `@misp_app.command("pull") def misp_pull(tag: str | None = None, days: int = 7): ...`
  - `@misp_app.command("push") def misp_push(ioc_value: str, tags: list[str] | None = None): ...`
  - `app.add_typer(misp_app)`

**REFACTOR — Mejoras**:
- Extraer CLI MISP a `lupe/cli_misp.py`.

**Verificación**:
- `pytest tests/test_misp_client.py::TestMISPCLI::test_pull_command_exists -v`
- `lupe misp pull --help`

**Rollback**:
- Revertir CLI.

### Task 10.5: Tests de `MISPClient` con respx

**PR**: PR-10
**Depende de**: 10.4
**Bloquea**: 10.6
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_misp_client.py::TestMISPClient::test_timeout_handling`
- Mockear timeout en respx; verifica que no crashea pipeline.

**GREEN — Implementación mínima**:
- Completar tests de error handling (401, 500, timeout).

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_misp_client.py -v`

**Rollback**:
- Revertir tests.

### Task 10.6: Tests de CLI `misp pull/push`

**PR**: PR-10
**Depende de**: 10.5
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_misp_client.py::TestMISPCLI::test_push_cli_runs`
- `subprocess.run(["lupe", "misp", "push", "8.8.8.8"])` con mocks.

**GREEN — Implementación mínima**:
- Completar CLI tests con `TyperRunner` o subprocess.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_misp_client.py::TestMISPCLI -v`

**Rollback**:
- Revertir tests.

---

## PR-11: Plugin Blocklist.de

**Goal**: `BlocklistDePlugin` para IPs (gratis, sin key).
**Acceptance Criteria**: Enriquece IPv4; retorna `None` si limpio; rate limit interno.
**Verificación**: `pytest tests/test_blocklist_de.py -v`
**Estimación Total**: 3h

### Task 11.1: Crear `BlocklistDePlugin`

**PR**: PR-11
**Depende de**: PR-8 (merge)
**Bloquea**: 11.2, 11.3, 11.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_blocklist_de.py::TestBlocklistDePlugin::test_plugin_name`
- `plugin.name == "blocklist.de"`.

**GREEN — Implementación mínima**:
- Crear `lupe/enrichment/blocklist_de.py`:
  - `class BlocklistDePlugin(EnrichmentPlugin): name = "blocklist.de"; supported_ioc_types = {IOCType.ipv4}; requires_api_key = False`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_blocklist_de.py::TestBlocklistDePlugin::test_plugin_name -v`

**Rollback**:
- Eliminar archivo.

### Task 11.2: Implementar query para IPv4

**PR**: PR-11
**Depende de**: 11.1
**Bloquea**: 11.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_blocklist_de.py::TestBlocklistDePlugin::test_enrich_ipv4_listed`
- Mockear `https://api.blocklist.de/api.php?ip=...` (o endpoint real según docs) con respx.

**GREEN — Implementación mínima**:
- `async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:`
- Parsear respuesta; retornar `EnrichmentResult` con `categories`, `report_counts`, `source_url`.

**REFACTOR — Mejoras**:
- Extraer URL base a constante.

**Verificación**:
- `pytest tests/test_blocklist_de.py::TestBlocklistDePlugin::test_enrich_ipv4_listed -v`

**Rollback**:
- Revertir `enrich`.

### Task 11.3: Manejar respuesta vacía (return `None`)

**PR**: PR-11
**Depende de**: 11.2
**Bloquea**: 11.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_blocklist_de.py::TestBlocklistDePlugin::test_enrich_clean_ip_returns_none`
- IP no listada → `assert result is None`.

**GREEN — Implementación mínima**:
- Si respuesta está vacía o indica no listado, retornar `None`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_blocklist_de.py::TestBlocklistDePlugin::test_enrich_clean_ip_returns_none -v`

**Rollback**:
- Revertir lógica.

### Task 11.4: Tests con respx (listed, clean, rate limit)

**PR**: PR-11
**Depende de**: 11.3
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_blocklist_de.py::TestBlocklistDePlugin::test_rate_limit_respected`
- Verificar que el plugin usa el rate limiter interno (si ya existe de PR-16; si no, skip hasta PR-16).

**GREEN — Implementación mínima**:
- Tests de rate limit usando mock de tiempo o del limiter.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_blocklist_de.py -v`

**Rollback**:
- Revertir tests.

---

## PR-12: Plugin Spamhaus

**Goal**: `SpamhausPlugin` IP/domain (gratis con key).
**Acceptance Criteria**: Gating por `LUPE_SPAMHAUS_KEY`; retorna categoría/confianza.
**Verificación**: `pytest tests/test_spamhaus.py -v`
**Estimación Total**: 4h

### Task 12.1: Crear `SpamhausPlugin`

**PR**: PR-12
**Depende de**: PR-8 (merge)
**Bloquea**: 12.2–12.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_spamhaus.py::TestSpamhausPlugin::test_plugin_name`
- `plugin.name == "spamhaus"`.

**GREEN — Implementación mínima**:
- Crear `lupe/enrichment/spamhaus.py`:
  - `class SpamhausPlugin(EnrichmentPlugin): name = "spamhaus"; supported_ioc_types = {IOCType.ipv4, IOCType.domain}; requires_api_key = True`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_spamhaus.py::TestSpamhausPlugin::test_plugin_name -v`

**Rollback**:
- Eliminar archivo.

### Task 12.2: Implementar lookup IPv4

**PR**: PR-12
**Depende de**: 12.1
**Bloquea**: 12.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_spamhaus.py::TestSpamhausPlugin::test_enrich_ipv4_malicious`
- Mockear Spamhaus API; retorna `EnrichmentResult` con `threat_category`, `confidence`, `reason`.

**GREEN — Implementación mínima**:
- `async def enrich(self, ioc, client):` → query Spamhaus intel API v2.

**REFACTOR — Mejoras**:
- Extraer auth header.

**Verificación**:
- `pytest tests/test_spamhaus.py::TestSpamhausPlugin::test_enrich_ipv4_malicious -v`

**Rollback**:
- Revertir lookup.

### Task 12.3: Implementar lookup domain

**PR**: PR-12
**Depende de**: 12.2
**Bloquea**: 12.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_spamhaus.py::TestSpamhausPlugin::test_enrich_domain_listed`
- Domain query retorna datos.

**GREEN — Implementación mínima**:
- En `enrich()`: branch según `ioc.ioc_type`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_spamhaus.py::TestSpamhausPlugin::test_enrich_domain_listed -v`

**Rollback**:
- Revertir branch.

### Task 12.4: Gating por `LUPE_SPAMHAUS_KEY`

**PR**: PR-12
**Depende de**: 12.3
**Bloquea**: 12.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_spamhaus.py::TestSpamhausPlugin::test_missing_key_excludes_plugin`
- Si `settings.spamhaus_key` es None, el plugin no se registra en `run_enrichment`.

**GREEN — Implementación mínima**:
- En `lupe/enrichment/__init__.py`: `_build_plugins(settings)` filtra `requires_api_key and not key`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_spamhaus.py::TestSpamhausPlugin::test_missing_key_excludes_plugin -v`

**Rollback**:
- Revertir gating.

### Task 12.5: Tests con respx

**PR**: PR-12
**Depende de**: 12.4
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_spamhaus.py::TestSpamhausPlugin::test_enrich_unsupported_type_returns_none`
- Hash/URL → `None`.

**GREEN — Implementación mínima**:
- Completar tests.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_spamhaus.py -v`

**Rollback**:
- Revertir tests.

---

## PR-13: Plugin crt.sh

**Goal**: `CrtShPlugin` certificado transparency para dominios (gratis, sin key).
**Acceptance Criteria**: Enriquece dominios; retorna `None` para IPv4/hash.
**Verificación**: `pytest tests/test_crtsh.py -v`
**Estimación Total**: 3h

### Task 13.1: Crear `CrtShPlugin`

**PR**: PR-13
**Depende de**: PR-8 (merge)
**Bloquea**: 13.2–13.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_crtsh.py::TestCrtShPlugin::test_plugin_name`
- `plugin.name == "crt.sh"`.

**GREEN — Implementación mínima**:
- `lupe/enrichment/crtsh.py`: `class CrtShPlugin(EnrichmentPlugin): name = "crt.sh"; supported_ioc_types = {IOCType.domain}; requires_api_key = False`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_crtsh.py::TestCrtShPlugin::test_plugin_name -v`

**Rollback**:
- Eliminar archivo.

### Task 13.2: Implementar query domain → certificados

**PR**: PR-13
**Depende de**: 13.1
**Bloquea**: 13.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_crtsh.py::TestCrtShPlugin::test_enrich_domain_returns_certs`
- Mockear `https://crt.sh/?q=...&output=json`; retorna lista de certificados.

**GREEN — Implementación mínima**:
- `async def enrich(self, ioc, client):` → GET `https://crt.sh/?q={domain}&output=json`.
- Parsear: `issuer`, `subject`, `san`, `entry_timestamp`.

**REFACTOR — Mejoras**:
- Extraer parser a función pura.

**Verificación**:
- `pytest tests/test_crtsh.py::TestCrtShPlugin::test_enrich_domain_returns_certs -v`

**Rollback**:
- Revertir `enrich`.

### Task 13.3: Return `None` para IPv4/hash

**PR**: PR-13
**Depende de**: 13.2
**Bloquea**: 13.4
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_crtsh.py::TestCrtShPlugin::test_unsupported_type_returns_none`
- `ioc.ioc_type == IOCType.ipv4` → `assert result is None`.

**GREEN — Implementación mínima**:
- Early return si `ioc.ioc_type not in supported_ioc_types`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_crtsh.py::TestCrtShPlugin::test_unsupported_type_returns_none -v`

**Rollback**:
- Revertir guard.

### Task 13.4: Tests con respx

**PR**: PR-13
**Depende de**: 13.3
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_crtsh.py::TestCrtShPlugin::test_empty_response_returns_none`
- `[]` JSON → `None`.

**GREEN — Implementación mínima**:
- Completar tests.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_crtsh.py -v`

**Rollback**:
- Revertir tests.

---

## PR-14: Plugin Hybrid Analysis

**Goal**: `HybridAnalysisPlugin` hash/URL sandbox (freemium).
**Acceptance Criteria**: Lookup SHA256 y URL; quota exceeded → warning + `None`.
**Verificación**: `pytest tests/test_hybrid_analysis.py -v`
**Estimación Total**: 5h

### Task 14.1: Crear `HybridAnalysisPlugin`

**PR**: PR-14
**Depende de**: PR-8 (merge)
**Bloquea**: 14.2–14.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_plugin_name`
- `plugin.name == "hybrid_analysis"`.

**GREEN — Implementación mínima**:
- `lupe/enrichment/hybrid_analysis.py`: `class HybridAnalysisPlugin(EnrichmentPlugin): name = "hybrid_analysis"; supported_ioc_types = {IOCType.sha256, IOCType.url}; requires_api_key = True`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_plugin_name -v`

**Rollback**:
- Eliminar archivo.

### Task 14.2: Implementar hash lookup

**PR**: PR-14
**Depende de**: 14.1
**Bloquea**: 14.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_enrich_hash`
- Mockear `https://www.hybrid-analysis.com/api/v2/search/hash`.

**GREEN — Implementación mínima**:
- `async def enrich(self, ioc, client):` → query hash endpoint.
- Retornar `verdict`, `threat_score`, `behavioral_indicators`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_enrich_hash -v`

**Rollback**:
- Revertir lookup.

### Task 14.3: Implementar URL analysis endpoint

**PR**: PR-14
**Depende de**: 14.2
**Bloquea**: 14.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_enrich_url`
- Mockear URL scan endpoint.

**GREEN — Implementación mínima**:
- Branch `IOCType.url` → query URL analysis/submit.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_enrich_url -v`

**Rollback**:
- Revertir branch.

### Task 14.4: Manejar quota exceeded

**PR**: PR-14
**Depende de**: 14.3
**Bloquea**: 14.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_quota_exceeded_returns_none`
- Mockear HTTP 429 → retorna `None`, log warning.

**GREEN — Implementación mínima**:
- En `enrich()`: catch 429 → `logger.warning(...); return None`.

**REFACTOR — Mejoras**:
- Usar exception personalizada `QuotaExceededError`.

**Verificación**:
- `pytest tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_quota_exceeded_returns_none -v`

**Rollback**:
- Revertir handling.

### Task 14.5: Tests con respx

**PR**: PR-14
**Depende de**: 14.4
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_hybrid_analysis.py::TestHybridAnalysisPlugin::test_unsupported_type_returns_none`
- IPv4/domain → `None`.

**GREEN — Implementación mínima**:
- Completar tests.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_hybrid_analysis.py -v`

**Rollback**:
- Revertir tests.

---

## PR-15: Plugin Censys

**Goal**: `CensysPlugin` IP/domain/certificates (freemium, id+secret).
**Acceptance Criteria**: Usa `LUPE_CENSYS_ID` y `LUPE_CENSYS_SECRET`; auth básica HTTP.
**Verificación**: `pytest tests/test_censys.py -v`
**Estimación Total**: 6h

### Task 15.1: Crear `CensysPlugin`

**PR**: PR-15
**Depende de**: PR-8 (merge)
**Bloquea**: 15.2–15.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_censys.py::TestCensysPlugin::test_plugin_name`
- `plugin.name == "censys"`.

**GREEN — Implementación mínima**:
- `lupe/enrichment/censys.py`: `class CensysPlugin(EnrichmentPlugin): name = "censys"; supported_ioc_types = {IOCType.ipv4, IOCType.domain, IOCType.sha256}; requires_api_key = True`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_censys.py::TestCensysPlugin::test_plugin_name -v`

**Rollback**:
- Eliminar archivo.

### Task 15.2: Implementar IP host data

**PR**: PR-15
**Depende de**: 15.1
**Bloquea**: 15.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_censys.py::TestCensysPlugin::test_enrich_ipv4`
- Mockear `https://search.censys.io/api/v2/hosts/{ip}`.

**GREEN — Implementación mínima**:
- `async def enrich(self, ioc, client):` → auth básica con `id:secret`.
- Parsear `services`, `open_ports`, `certificates`, `autonomous_system`.

**REFACTOR — Mejoras**:
- Extraer auth a helper.

**Verificación**:
- `pytest tests/test_censys.py::TestCensysPlugin::test_enrich_ipv4 -v`

**Rollback**:
- Revertir lookup.

### Task 15.3: Implementar certificate lookup

**PR**: PR-15
**Depende de**: 15.2
**Bloquea**: 15.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_censys.py::TestCensysPlugin::test_enrich_domain_certificate`
- Mockear certificates endpoint.

**GREEN — Implementación mínima**:
- Branch `domain` o `sha256` → query certificates API v1/v2 según corresponda.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_censys.py::TestCensysPlugin::test_enrich_domain_certificate -v`

**Rollback**:
- Revertir branch.

### Task 15.4: Manejar credenciales inválidas

**PR**: PR-15
**Depende de**: 15.3
**Bloquea**: 15.5
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_censys.py::TestCensysPlugin::test_invalid_credentials_returns_none`
- Mockear 401 → retorna `None`, log warning.

**GREEN — Implementación mínima**:
- Catch 401 en `enrich()`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_censys.py::TestCensysPlugin::test_invalid_credentials_returns_none -v`

**Rollback**:
- Revertir handling.

### Task 15.5: Tests con respx

**PR**: PR-15
**Depende de**: 15.4
**Bloquea**: none
**Estimación**: S
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_censys.py::TestCensysPlugin::test_unsupported_type_returns_none`
- Email/phone → `None`.

**GREEN — Implementación mínima**:
- Completar tests.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_censys.py -v`

**Rollback**:
- Revertir tests.

---

## PR-16: Security Hardening

**Goal**: Redaction, validation, HTTPS-only, rate limit, pre-commit, bandit, pip-audit.
**Acceptance Criteria**: `bandit -r lupe/` 0 high; `pip-audit` 0 CVE; pre-commit rechaza secrets.
**Verificación**: `pytest tests/test_security.py -v && bandit -r lupe/ && pip-audit`
**Estimación Total**: 8h

### Task 16.1: Crear `lupe/security/redaction.py`

**PR**: PR-16
**Depende de**: PR-10 (merge)
**Bloquea**: 16.2–16.8
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_redact_secrets_replaces_keys`
- `redact_secrets("Authorization: Bearer sk-123")` → contiene `"***"`.

**GREEN — Implementación mínima**:
- Crear `lupe/security/redaction.py`:
  - `def redact_secrets(text: str) -> str:`
  - Regex para `sk-...`, `Bearer ...`, `api_key=...`, etc.
  - Reemplazar con `***`.

**REFACTOR — Mejoras**:
- Integrar en log formatter custom.

**Verificación**:
- `pytest tests/test_security.py::TestSecurity::test_redact_secrets_replaces_keys -v`
- `bandit -r lupe/security/redaction.py`

**Rollback**:
- Eliminar archivo.

### Task 16.2: Crear `lupe/security/validation.py`

**PR**: PR-16
**Depende de**: 16.1
**Bloquea**: 16.3
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_validate_ioc_rejects_overlong`
- `validate_ioc("a" * 4097)` lanza `ValueError`.

**GREEN — Implementación mínima**:
- Crear `lupe/security/validation.py`:
  - `MAX_IOC_LENGTH = 4096`
  - `def validate_ioc(value: str) -> None:`
  - Rechazar si `len(value) > MAX_IOC_LENGTH` o no matchea ningún regex de `ioc_detect`.

**REFACTOR — Mejoras**:
- Reutilizar `detect_ioc` en vez de duplicar regexes.

**Verificación**:
- `pytest tests/test_security.py::TestSecurity::test_validate_ioc_rejects_overlong -v`

**Rollback**:
- Eliminar archivo.

### Task 16.3: Crear `lupe/security/https_only.py`

**PR**: PR-16
**Depende de**: 16.2
**Bloquea**: 16.4
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_https_only_rejects_http`
- `HttpsOnlyTransport` o wrapper rechaza URL con scheme `http`.

**GREEN — Implementación mínima**:
- Crear `lupe/security/https_only.py`:
  - Subclass de `httpx.HTTPTransport` o middleware que inspeccione `request.url.scheme`.
  - Si `http`, raise `SecurityError("HTTP is not allowed")`.

**REFACTOR — Mejoras**:
- Aplicar globalmente en `httpx.AsyncClient` usado por plugins.

**Verificación**:
- `pytest tests/test_security.py::TestSecurity::test_https_only_rejects_http -v`

**Rollback**:
- Eliminar archivo.

### Task 16.4: Crear `lupe/security/rate_limit.py`

**PR**: PR-16
**Depende de**: 16.3
**Bloquea**: 16.5
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_rate_limiter_allows_under_limit`
- `RateLimiter(max_rate=5).acquire()` no bloquea las primeras 5 veces.

**GREEN — Implementación mínima**:
- Crear `lupe/security/rate_limit.py`:
  - `class RateLimiter:` basado en token bucket o sliding window.
  - `async def acquire(self):` sleep si excede rate.

**REFACTOR — Mejoras**:
- Usar `asyncio.Semaphore` por host o `aiolimiter` si se agrega dependencia.

**Verificación**:
- `pytest tests/test_security.py::TestSecurity::test_rate_limiter_allows_under_limit -v`

**Rollback**:
- Eliminar archivo.

### Task 16.5: Configurar `.pre-commit-config.yaml`

**PR**: PR-16
**Depende de**: 16.4
**Bloquea**: 16.6
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_precommit_config_exists`
- `.pre-commit-config.yaml` existe y tiene hooks de gitleaks, ruff, bandit.

**GREEN — Implementación mínima**:
- Crear `.pre-commit-config.yaml`:
  - `repo: https://github.com/gitleaks/gitleaks` → `id: gitleaks`
  - `repo: https://github.com/astral-sh/ruff-pre-commit` → `id: ruff`, `id: ruff-format`
  - `repo: https://github.com/PyCQA/bandit` → `id: bandit`

**REFACTOR — Mejoras**:
- Agregar `mypy` hook si es rápido.

**Verificación**:
- `pre-commit run --all-files` (smoke)
- `pytest tests/test_security.py::TestSecurity::test_precommit_config_exists -v`

**Rollback**:
- `git rm .pre-commit-config.yaml`.

### Task 16.6: Configurar bandit en `pyproject.toml`

**PR**: PR-16
**Depende de**: 16.5
**Bloquea**: 16.7
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_bandit_config_exists`
- `[tool.bandit]` en `pyproject.toml` excluye `tests/`.

**GREEN — Implementación mínima**:
- `pyproject.toml`:
  - `[tool.bandit]`
  - `exclude_dirs = ["tests", ".venv", "venv"]`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `bandit -c pyproject.toml -r lupe/`

**Rollback**:
- Revertir `pyproject.toml`.

### Task 16.7: Integrar pip-audit en CI (prerequisite para PR-17)

**PR**: PR-16
**Depende de**: 16.6
**Bloquea**: 16.8
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_pip_audit_passes`
- `pip-audit` no reporta vulnerabilidades conocidas.

**GREEN — Implementación mínima**:
- Agregar `pip-audit` a `requirements-dev.txt` / `pyproject.toml` opcional deps.
- Script `scripts/security-check.sh` o anotar para CI en PR-17.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pip-audit --desc`

**Rollback**:
- Revertir deps.

### Task 16.8: Tests de redaction, validation, HTTPS-only, rate limiting

**PR**: PR-16
**Depende de**: 16.7
**Bloquea**: none
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**:
- Path: `tests/test_security.py::TestSecurity::test_config_show_redacts_keys`
- `lupe config show` output contiene `"***"` para keys.

**GREEN — Implementación mínima**:
- Integrar `redact_secrets` en CLI output de `config show`.
- Completar tests en `tests/test_security.py`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_security.py -v`
- `bandit -r lupe/security/`

**Rollback**:
- Revertir tests e integración.

---

## PR-17: CI/CD Workflows

**Goal**: Matrix CI (Ubuntu/Debian/Windows), release PyPI, CodeQL, dependency review.
**Acceptance Criteria**: `act` o push a PR dispara jobs verdes; tag dispara release.
**Verificación**: `pytest` local + revisar YAML sintaxis con `actionlint`
**Estimación Total**: 6h

### Task 17.1: Crear `.github/workflows/ci.yml`

**PR**: PR-17
**Depende de**: PR-16 (merge)
**Bloquea**: 17.2–17.5
**Estimación**: M
**Tipo**: setup

**RED — Test que debe fallar**:
- Path: `tests/test_ci.py::TestCI::test_ci_yaml_syntax_valid` (opcional)
- YAML parsea sin errores.

**GREEN — Implementación mínima**:
- `.github/workflows/ci.yml`:
  - `strategy.matrix`: `os: [ubuntu-22.04, ubuntu-24.04, debian-12, windows-10, windows-11]` (nota: GitHub no tiene `debian-12` nativo; usar container `debian:12` en `ubuntu-latest`).
  - Jobs: `lint` (ruff), `type-check` (mypy), `test` (pytest), `security` (pip-audit + bandit).

**REFACTOR — Mejoras**:
- Cache de pip.

**Verificación**:
- `actionlint .github/workflows/ci.yml`

**Rollback**:
- `git rm .github/workflows/ci.yml`.

### Task 17.2: Crear `.github/workflows/release.yml`

**PR**: PR-17
**Depende de**: 17.1
**Bloquea**: 17.3
**Estimación**: M
**Tipo**: setup

**RED — Test que debe fallar**: N/A

**GREEN — Implementación mínima**:
- `.github/workflows/release.yml`:
  - Trigger: `on.push.tags: ["v*"]`
  - Jobs: `build` (manylinux wheel + sdist con `cibuildwheel` o `build`), `publish` (PyPI via `pypa/gh-action-pypi-publish`), `release` (GitHub Release con assets).

**REFACTOR — Mejoras**:
- Firmar artifacts con Sigstore.

**Verificación**:
- `actionlint .github/workflows/release.yml`

**Rollback**:
- `git rm .github/workflows/release.yml`.

### Task 17.3: Crear `.github/workflows/codeql.yml`

**PR**: PR-17
**Depende de**: 17.2
**Bloquea**: 17.4
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**: N/A

**GREEN — Implementación mínima**:
- `.github/workflows/codeql.yml`:
  - `on.schedule.cron: "0 9 * * 1"` (lunes 9am)
  - `on.pull_request`
  - Lenguaje: `python`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `actionlint .github/workflows/codeql.yml`

**Rollback**:
- `git rm .github/workflows/codeql.yml`.

### Task 17.4: Crear `.github/workflows/dependency-review.yml`

**PR**: PR-17
**Depende de**: 17.3
**Bloquea**: 17.5
**Estimación**: S
**Tipo**: setup

**RED — Test que debe fallar**: N/A

**GREEN — Implementación mínima**:
- `.github/workflows/dependency-review.yml`:
  - Usar `actions/dependency-review-action@v4`.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `actionlint .github/workflows/dependency-review.yml`

**Rollback**:
- `git rm .github/workflows/dependency-review.yml`.

### Task 17.5: Validar que CI pasa en el repo actual

**PR**: PR-17
**Depende de**: 17.4
**Bloquea**: none
**Estimación**: M
**Tipo**: TDD

**RED — Test que debe fallar**: N/A (validación manual/CI)

**GREEN — Implementación mínima**:
- Correr localmente los pasos que CI correría:
  - `ruff check lupe/ tests/`
  - `mypy lupe/`
  - `pytest tests/`
  - `bandit -r lupe/`
  - `pip-audit`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/ -q`
- `ruff check .`

**Rollback**:
- Revertir fixes si rompen algo.

---

## PR-18: Docs (README, CONTRIBUTING, CHANGELOG, Packaging Final)

**Goal**: Documentación completa del rebrand y packaging final.
**Acceptance Criteria**: README renderiza en PyPI; CHANGELOG lista breaking changes; CLAUDE.md actualizado.
**Verificación**: `twine check dist/*` + lectura manual
**Estimación Total**: 5h

### Task 18.1: Escribir `README.md` profesional

**PR**: PR-18
**Depende de**: PR-17 (merge)
**Bloquea**: 18.2–18.5
**Estimación**: M
**Tipo**: docs

**RED — Test que debe fallar**:
- Path: `tests/test_docs.py::TestDocs::test_readme_exists`
- `Path("README.md").exists()`.

**GREEN — Implementación mínima**:
- `README.md`:
  - Título: Lupe CTI
  - Install: `pipx install lupe-cti`
  - Usage: `lupe enrich 8.8.8.8`, `lupe-desktop`, `lupe migrate-from-centinela`
  - Env vars table (LUPE_*)
  - Badges: CI, PyPI, CodeQL

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_docs.py::TestDocs::test_readme_exists -v`
- `markdownlint README.md` (si disponible)

**Rollback**:
- Revertir README.

### Task 18.2: Escribir `CONTRIBUTING.md`

**PR**: PR-18
**Depende de**: 18.1
**Bloquea**: 18.3
**Estimación**: S
**Tipo**: docs

**RED — Test que debe fallar**:
- Path: `tests/test_docs.py::TestDocs::test_contributing_exists`
- `CONTRIBUTING.md` existe.

**GREEN — Implementación mínima**:
- `CONTRIBUTING.md`:
  - Setup dev: `pip install -e ".[dev]"`
  - Pre-commit: `pre-commit install`
  - Tests: `pytest`
  - PR process: feature-branch-chain

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_docs.py::TestDocs::test_contributing_exists -v`

**Rollback**:
- Revertir.

### Task 18.3: Escribir `CHANGELOG.md`

**PR**: PR-18
**Depende de**: 18.2
**Bloquea**: 18.4
**Estimación**: S
**Tipo**: docs

**RED — Test que debe fallar**:
- Path: `tests/test_docs.py::TestDocs::test_changelog_exists`
- `CHANGELOG.md` existe.

**GREEN — Implementación mínima**:
- `CHANGELOG.md`:
  - Keep a Changelog format.
  - v1.0.0: rebrand, multi-LLM, TUI, 6 plugins nuevos, security hardening, distro packaging.
  - Breaking: package name, CLI name, env vars, DB path.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_docs.py::TestDocs::test_changelog_exists -v`

**Rollback**:
- Revertir.

### Task 18.4: Actualizar `CLAUDE.md`

**PR**: PR-18
**Depende de**: 18.3
**Bloquea**: 18.5
**Estimación**: S
**Tipo**: docs

**RED — Test que debe fallar**:
- Path: `tests/test_docs.py::TestDocs::test_claude_md_updated`
- `CLAUDE.md` no contiene "centinela" (o contiene en contexto histórico solo).

**GREEN — Implementación mínima**:
- Reemplazar referencias a `centinela` por `lupe` donde aplique.
- Agregar sección de LLM providers, TUI, MISP, plugins nuevos.

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `pytest tests/test_docs.py::TestDocs::test_claude_md_updated -v`

**Rollback**:
- Revertir `CLAUDE.md`.

### Task 18.5: Packaging final (revisar `pyproject.toml`)

**PR**: PR-18
**Depende de**: 18.4
**Bloquea**: none
**Estimación**: S
**Tipo**: docs

**RED — Test que debe fallar**:
- Path: `tests/test_docs.py::TestDocs::test_pyproject_classifiers_complete`
- `pyproject.toml` tiene classifiers de OS, license, Python versions.

**GREEN — Implementación mínima**:
- `pyproject.toml`:
  - `classifiers`: `Development Status :: 4 - Beta`, `Intended Audience :: Information Technology`, `License :: OSI Approved :: MIT License`, `Operating System :: POSIX :: Linux`, `Operating System :: Microsoft :: Windows`, `Programming Language :: Python :: 3.10`, `3.11`, `3.12`.
  - `keywords`: `cti, osint, threat-intelligence, ioc, enrichment`

**REFACTOR — Mejoras**:
- N/A.

**Verificación**:
- `python -m build` (smoke)
- `twine check dist/*`

**Rollback**:
- Revertir `pyproject.toml`.

---

## Estimación Global

| Métrica | Valor |
|---|---|
| **Total de tasks** | 95 |
| **Total de PRs** | 19 (PR-0 a PR-18) |
| **Total de horas estimadas** | ~95h |
| **PRs con `size:exception` estimada** | PR-1 (~500 líneas), PR-8 (~350 líneas), PR-16 (~250 líneas) |

### PRs con estimación total

| PR | Horas | Tamaño estimado (líneas) |
|---|---|---|
| PR-0 | 4h | 150 |
| PR-1 | 6h | **500** |
| PR-2 | 4h | 200 |
| PR-3 | 4h | 150 |
| PR-4 | 5h | 200 |
| PR-5 | 4h | 180 |
| PR-6 | 8h | 400 |
| PR-7 | 8h | 350 |
| PR-8 | 10h | **350** |
| PR-9 | 6h | 200 |
| PR-10 | 8h | 300 |
| PR-11 | 3h | 120 |
| PR-12 | 4h | 150 |
| PR-13 | 3h | 120 |
| PR-14 | 5h | 180 |
| PR-15 | 6h | 220 |
| PR-16 | 8h | **300** |
| PR-17 | 6h | 250 |
| PR-18 | 5h | 200 |

---

## Top 3 PRs Más Riesgosos

1. **PR-1 (Package Rename)**: Toca ~100% del código existente. Cualquier import faltante rompe todo el sistema. Requiere validación exhaustiva con `grep` y `pytest`.
2. **PR-8 (Multi-LLM Strategy)**: 4 providers async con APIs distintas, errores de red, auth, rate limits. Refactor de `analysis.py` puede introducir regresiones silenciosas si el fallback no funciona.
3. **PR-6/PR-7 (TUI Scaffold + Settings)**: Textual es nueva dependencia en el proyecto. Riesgo de incompatibilidad en Windows/Debian 12, y la lógica de permisos 600 cross-platform es propensa a errores sutiles.

## Top 3 PRs Paralelizables

1. **PR-9 (Logo + Branding)**: 100% independiente del código. Puede ejecutarse en cualquier momento.
2. **PR-0 (Coverage Baseline)**: Solo agrega tests a código existente. No bloquea funcionalidad nueva.
3. **PR-4 (XDG Paths)**: Puede desarrollarse en paralelo al rename si se trabaja en archivos nuevos (`lupe/config.py` ya renombrado), aunque idealmente se mergea después de PR-1.

## Forecast de Review Workload

| Métrica | Valor |
|---|---|
| **PR más grande (est. líneas)** | PR-1 (~500 líneas cambiadas: rename de todo) |
| **Total de líneas estimadas en el change** | ~3,800 líneas |
| **¿Necesita `size:exception`?** | Sí — PR-1 excede el presupuesto de 400 líneas por diseño (rename global). Los demás PRs están diseñados para estar bajo 400 excepto PR-6 y PR-8 que pueden necesitar excepción o subdivisión. |
| **¿Chained PRs o single-PR?** | **Chained PRs obligatorio**. Single-PR sería imposible de revisar efectivamente (>3,800 líneas). |

---

## Issues / Assumptions

1. **Cisco Talos eliminado**: El usuario confirmó que Cisco Talos NO se implementa en este change (no tiene API pública). Se omitieron las tasks de `cisco_talos.py` y `test_cisco_talos.py`.
2. **Censys credenciales**: El usuario especifica `LUPE_CENSYS_ID` + `LUPE_CENSYS_SECRET`, pero la spec original de plugin-censys menciona `LUPE_CENSYS_KEY`. Se asume el criterio del usuario: dos variables separadas.
3. **Debian 12 runner en GitHub Actions**: No existe runner nativo `debian-12`. Se asume uso de container `debian:12` sobre `ubuntu-latest` en CI.
4. **Textual en Python 3.11 (Debian 12)**: Se asume que `textual>=0.50` es compatible. Si falla, se evaluará downgrade o reemplazo.
5. **Logo generation**: Se asume que los assets SVG/PNG se generan manualmente o con herramienta externa; no hay generación automática en CI.
6. **MISP consumer + export**: Se implementa como raw REST (sin `pymisp`), según design AD-4.
7. **No backward compat**: Sin alias de env vars ni imports. El usuario lo confirmó explícitamente.

---

## Status

- **Status**: `ready`
- **Decision needed before apply**: Yes (confirmar que PR-1 puede tener `size:exception` por rename global)
- **Chained PRs recommended**: Yes
- **Chain strategy**: `feature-branch-chain`
- **400-line budget risk**: High

**Skill Resolution**: `injected` (contexto de sesión proporcionado por orchestrator)
