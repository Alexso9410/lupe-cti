# Proposal: Lupe CTI v1 — Rebrand + Multi-LLM + Security Hardening + Distro Packaging

**Status**: `done` — Archived 2026-06-23 (538 tests pass, 0 ruff, v1.0.0, judgment-day ABSUELTO)

## TL;DR

- Rename completo del ecosistema: paquete **`lupe-cti`** en PyPI, CLI **`lupe`**, env vars **`LUPE_*`** (hard cut, sin backward compat — no hay usuarios públicos)
- **Multi-LLM Strategy pattern**: Ollama (default local), OpenAI, Anthropic Claude, OpenRouter — selección por config, fallback automático
- **Vue 3 Settings Panel** vía CDN para gestión interactiva de API keys con validación en vivo, links a signup, persistencia segura (600)
- **Security hardening integral**: pip-audit, bandit, CodeQL, gitleaks, rate limiting interno, API key redaction, HTTPS-only, input validation
- **Packaging Linux-first**: XDG paths, `.desktop`, manpage `lupe.1`, systemd unit, manylinux wheels, pipx, headless mode obligatorio

## Why

Centinela fue un prototipo interno para Heimdall Security. El relanzamiento como **Lupe CTI** responde a tres drivers: (1) integrarse como herramienta nativa en una **distro Linux forense basada en Debian 12+**, (2) eliminar el vendor lock-in de Ollama con **multi-proveedor LLM**, y (3) alcanzar **production-grade security** antes de cualquier release público. El nombre "Lupe" (lupa en alemán) refuerza la metáfora de investigación e inspección del ecosistema CTI, y evita conflictos de trademark.

## Goals

1. **Rebrand completo**: 100% de ocurrencias `centinela`/`CENTINELA` migradas a `lupe`/`LUPE` — código, docs, paths, assets
2. **Multi-LLM production-ready**: 4 proveedores con Strategy pattern, streaming, model listing, key validation, default inteligente a Ollama
3. **API key panel interactivo**: Vue 3 settings UI con validación en vivo, enlaces de obtención de keys, almacenamiento seguro con permisos 600
4. **Security pipeline**: pip-audit + bandit + CodeQL + gitleaks integrados en CI, rate limiting interno, redacción de secrets en logs
5. **Linux-distro packaging**: XDG Base Directory compliance, `.desktop` file, manpage groff, systemd unit opcional, wheels manylinux, pipx-ready
6. **Headless-first operation**: la distro forense no garantiza GUI — CLI debe ser completamente funcional sin dependencia de pywebview
7. **CI/CD multi-plataforma**: GitHub Actions matrix con Ubuntu 22.04/24.04 + Debian 12 + Windows 10/11, CodeQL, release automation a PyPI
8. **Identidad visual**: logo lupa abstracta + código matrix + auriculares/alas, paleta verde #00FF41 + gris oscuro + cyan, tipografía JetBrains Mono + Inter

## Non-Goals

- NO API REST (FastAPI) — queda para v2
- NO STIX/TAXII export — queda para v2
- NO graph visualization de relaciones IOCs
- NO webhooks ni daemon/scheduler automático
- NO dark web monitoring plugins
- NO backward compatibility aliases para `CENTINELA_*`
- NO migración automática de DB legacy (manual vía `lupe migrate-from-centinela`)
- NO bulk enrichment desde archivo

## Scope In

| # | Item | Category |
|---|------|----------|
| 1 | Package rename: `centinela` → `lupe-cti` (PyPI), directorio `lupe/` | Rebrand |
| 2 | CLI rename: `centinela` → `lupe`, entry point `lupe-desktop` | Rebrand |
| 3 | Env prefix hard cut: `CENTINELA_*` → `LUPE_*` | Rebrand |
| 4 | XDG-compliant paths: `~/.local/share/lupe/`, `~/.config/lupe/`, `~/.cache/lupe/` | Packaging |
| 5 | Windows paths: `%LOCALAPPDATA%\Lupe\lupe.db` | Packaging |
| 6 | LLMProvider ABC + Ollama, OpenAI, Anthropic, OpenRouter implementations | Multi-LLM |
| 7 | Provider selection por config (env var `LUPE_LLM_PROVIDER`), default Ollama | Multi-LLM |
| 8 | Vue 3 CDN Settings Panel: campos por API key + links + validación en vivo | Frontend |
| 9 | Secure persistence: archivo config con permisos 600 en Linux | Security |
| 10 | pip-audit en CI + bandit SAST + CodeQL analysis + gitleaks pre-commit | Security |
| 11 | API key redaction en logs (`***`), HTTPS-only en todas las llamadas externas | Security |
| 12 | IOC input validation + internal rate limiting por plugin | Security |
| 13 | Logo SVG + PNG (256, 128, 64, 32, 16px) + monochrome variant | Branding |
| 14 | `.desktop` file, manpage `lupe.1` (groff), systemd unit `lupe-watch.service` | Packaging |
| 15 | Manylinux wheels build + `pipx install lupe-cti` compatibility | Packaging |
| 16 | `--headless` flag: CLI fully functional sin pywebview/GUI | Packaging |
| 17 | CI/CD: `ci.yml` (PRs), `release.yml` (tags), `codeql.yml` (security) | CI/CD |
| 18 | `lupe migrate-from-centinela` comando manual de migración legacy DB | Rebrand |
| 19 | 7 plugins nuevos: Hybrid Analysis, Censys, crt.sh, MISP (consumer), Cisco Talos, Spamhaus, Blocklist.de | Enrichment |
| 20 | Paleta de colores CSS custom properties + tipografía JetBrains Mono/Inter | Branding |

## Scope Out

| # | Item | Target |
|---|------|--------|
| 1 | API REST (FastAPI) | v2 |
| 2 | STIX/TAXII export | v2 |
| 3 | IOC relationship graph (D3/NetworkX) | v2 |
| 4 | Webhooks para alerts | v2 |
| 5 | Daemon/scheduler para re-enrichment | v2 |
| 6 | Dark web monitoring plugins | v2+ |
| 7 | Backward compat aliases `CENTINELA_*` | Never |
| 8 | Automatic DB migration (manual only) | Never |
| 9 | GeoIP/ASN avanzado (MaxMind, BGPView) | v2 |
| 10 | Playbooks/workflows engine | v2+ |
| 11 | Bulk enrichment from file | v2 |
| 12 | IOC tagging/taxonomies UI | v2 |
| 13 | Caching layer (TTL por plugin) | v1.1 |
| 14 | Circuit breaker para plugins fallidos | v1.1 |

## Approach

**Fase 1 — Foundation (PRs 1-2):** Hard cut del rename. `centinela/` → `lupe/`, todas las referencias internas, `pyproject.toml`, entry points. Sin backward compat. Luego, LLMProvider ABC + 4 implementaciones. El config system se expande con `LUPE_LLM_PROVIDER` y settings específicos por proveedor.

**Fase 2 — UI + Security (PRs 3-4):** Vue 3 settings panel vía CDN (sin build step, compatible con pywebview). Security hardening como PR independiente para no bloquear features. Gitleaks en pre-commit, bandit + pip-audit en CI, CodeQL en GitHub Actions.

**Fase 3 — Linux Distro (PRs 5-6):** XDG directory creation en startup. `.desktop` + manpage + systemd unit. Manylinux wheels en CI. Headless mode flag. CI/CD workflows completos con matrix testing.

**Fase 4 — Polish (PRs 7-8):** Logo assets generados con SVG primario. Frontend rebrand completo. Comando `migrate-from-centinela`. Docs finales (CLAUDE.md, CHANGELOG).

## User-Facing Changes (Breaking)

| # | Change | Impact |
|---|--------|--------|
| 1 | `pip install centinela` → `pip install lupe-cti` | Todo script/CI debe actualizar |
| 2 | `centinela enrich` → `lupe enrich` | Comando CLI cambia |
| 3 | `CENTINELA_VIRUSTOTAL_KEY` → `LUPE_VIRUSTOTAL_KEY` | Todas las env vars requieren rename |
| 4 | DB path `~/.centinela/` → `~/.local/share/lupe/` | Migración manual vía `lupe migrate-from-centinela` |
| 5 | `centinela-desktop` → `lupe-desktop` | Entry point desktop cambia |
| 6 | `centinela/config.py` ya no existe | Imports en código externo (Heimdall bridge) deben actualizarse |
| 7 | Nuevo provider LLM por defecto: Ollama → configurable | Si Ollama no está disponible, el feature se silencia (comportamiento existente) |

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `lupe` ya tomado en PyPI | Confirmed | Medium | Usar `lupe-cti` como package name; CLI mantiene `lupe` |
| pywebview inestable en Debian 12 (WebKitGTK) | Medium | Medium | Headless mode es obligatorio; GUI es opcional. Si falla, explorar Textual/Rich TUI |
| Ollama no disponible en distro forense | Medium | Low | Fallback automático a OpenAI/OpenRouter; headless mode no depende de Ollama |
| Rate limits de 7 nuevos plugins gratuitos | High | Low | Rate limiting interno por plugin; caching layer planeado para v1.1 |
| `lupe migrate-from-centinela` pierde datos | Low | High | Tests exhaustivos de migración; backup automático del DB legacy antes de migrar |
| Conflictos de marca con "Lupe" existente | Low | Medium | Verificar trademark search antes de publicar assets; el nombre completo es "Lupe CTI" |
| CI matrix (5 OS × 3 Python versions) lento/costoso | Medium | Low | Usar GitHub Actions free tier; cache de pip; jobs paralelos |

## Success Metrics

- [ ] `pip install lupe-cti` instala sin errores en Debian 12, Ubuntu 22.04+, Windows 10+
- [ ] `lupe enrich 8.8.8.8` ejecuta enrichment con ≥1 plugin exitoso
- [ ] `lupe --help` muestra "Lupe CTI — Cyber Threat Intelligence for OSINT & Forensics"
- [ ] `LUPE_LLM_PROVIDER=openai LUPE_OPENAI_KEY=sk-xxx lupe enrich 1.2.3.4` usa OpenAI para AI analysis
- [ ] `pytest` pasa 100% sin regresiones (tests existentes + nuevos)
- [ ] CI verde en matrix: Ubuntu 22.04, 24.04, Debian 12, Windows 10, Windows 11
- [ ] `pipx install lupe-cti` funcional en Debian 12 limpio
- [ ] Settings Panel GUI muestra validación en vivo de API keys
- [ ] `lupe migrate-from-centinela` migra DB de ~/.centinela/ exitosamente
- [ ] `pip-audit` → 0 vulnerabilidades conocidas; `bandit` → 0 high severity
- [ ] CodeQL scan → 0 alerts en default branch
- [ ] Logo SVG renderiza correctamente en 16×16 a 256×256 sin pérdida de legibilidad

## Chained PR Stack

> **Strategy**: feature-branch-chain. Cada PR es autovalorable, con tests propios, mergeable a `main` sin dependencias circulares. Stack order designed so each PR extends the previous one.

```
PR-1: breaking/rename-to-lupe            (foundation)
  ↓
PR-2: feat/multi-llm-provider             (extends config from PR-1)
  ↓
PR-3: feat/vue3-api-key-panel             (depends on multi-LLM config)
  ↓
PR-4: feat/security-hardening             (cross-cutting, can parallel with 2-3)
  ↓
PR-5: feat/linux-distro-packaging         (XDG paths from PR-1)
  ↓
PR-6: feat/ci-cd-workflows                (validates all above)
  ↓
PR-7: feat/lupe-branding-and-logo         (cosmetic, independent)
  ↓
PR-8: feat/headless-mode-and-migration    (final integration + docs)
```

| PR | Nombre | Archivos (~) | Scope |
|----|--------|-------------|-------|
| **PR-1** | `breaking/rename-to-lupe` | ~20 | Package `lupe-cti`, directorio `lupe/`, CLI `lupe`, env `LUPE_*`, XDG paths, `pyproject.toml` |
| **PR-2** | `feat/multi-llm-provider` | ~8 | `LLMProvider` ABC, Ollama/OpenAI/Anthropic/OpenRouter, config expansion, tests |
| **PR-3** | `feat/vue3-api-key-panel` | ~5 | Vue 3 CDN settings UI, live validation, secure persistence (600), provider signup links |
| **PR-4** | `feat/security-hardening` | ~8 | pip-audit CI, bandit config, CodeQL workflow, gitleaks pre-commit, key redaction, rate limiting, input validation |
| **PR-5** | `feat/linux-distro-packaging` | ~7 | XDG directory init, `.desktop`, `lupe.1` manpage, `lupe-watch.service`, manylinux wheel config, pipx test |
| **PR-6** | `feat/ci-cd-workflows` | ~3 | `.github/workflows/ci.yml` (matrix), `release.yml` (PyPI), `codeql.yml` |
| **PR-7** | `feat/lupe-branding-and-logo` | ~12 | Logo SVG + PNG (6 sizes) + monochrome, CSS palette, typography, frontend rebrand |
| **PR-8** | `feat/headless-mode-and-migration` | ~5 | `--headless` flag, `migrate-from-centinela` command, CLAUDE.md, CHANGELOG |

## Capabilities

### New Capabilities

- **`multi-llm-provider`**: LLMProvider ABC with Strategy pattern. Ollama (local), OpenAI, Anthropic Claude, OpenRouter implementations. Streaming, model listing, key validation. Provider selection via `LUPE_LLM_PROVIDER` env var.
- **`api-key-panel`**: Vue 3 CDN-based settings UI. Per-provider API key fields with descriptions, signup links, live format validation. Secure file persistence with 600 permissions on Linux.
- **`lupe-branding`**: Logo assets (SVG + PNG multi-size + monochrome). Color palette (matrix green #00FF41 + dark gray + cyan accents). Typography (JetBrains Mono for IOCs, Inter for UI).
- **`security-scanning`**: pip-audit dependency scanning, bandit SAST, CodeQL analysis, gitleaks secret detection. API key redaction in logs/errors. HTTPS-only external calls. IOC input validation. Internal per-plugin rate limiting.
- **`linux-distro-support`**: XDG Base Directory compliance. `.desktop` file for app launchers. `lupe.1` groff manpage. `lupe-watch.service` systemd unit (optional). Manylinux wheel builds. pipx installation compatibility.
- **`headless-mode`**: `--headless` CLI flag. Operation without pywebview/GUI dependency. Required for forensic distro deployments where GUI is unavailable.
- **`ci-cd-workflows`**: GitHub Actions CI matrix (5 OS). Release automation to PyPI + GitHub Releases. CodeQL security analysis on schedule + PRs.
- **`enrichment-plugins-v1`**: 7 new enrichment plugins: Hybrid Analysis, Censys, crt.sh, MISP (consumer), Cisco Talos, Spamhaus, Blocklist.de. Follow existing `EnrichmentPlugin` ABC pattern.

### Modified Capabilities

- **`config-system`**: Env prefix `CENTINELA_*` → `LUPE_*` (hard cut). New settings: `LUPE_LLM_PROVIDER`, per-provider API keys (`LUPE_OPENAI_KEY`, `LUPE_ANTHROPIC_KEY`, `LUPE_OPENROUTER_KEY`), `LUPE_OPENROUTER_BASE_URL`. XDG path derivation.
- **`cli-entrypoints`**: CLI name `centinela` → `lupe`. New subcommand `lupe migrate-from-centinela`. Desktop entry `centinela-desktop` → `lupe-desktop`. Help text and banners rebranded.
- **`db-persistence`**: DB path `~/.centinela/centinela.db` → `~/.local/share/lupe/lupe.db` (Linux XDG) / `%LOCALAPPDATA%\Lupe\lupe.db` (Windows). Migration command for legacy DB.
- **`desktop-gui`**: Window title, branding, CSS, JS variables rebranded. Frontend rebuilt with Vue 3 CDN (replaces monolithic HTML). New API key settings panel.

## Open Questions

1. **¿pywebview funciona en Debian 12 con WebKitGTK?** Si no, ¿migramos GUI a Textual (TUI) o Electron? — La spec debe definir un fallback.
2. **¿MISP en v1 es consumer (lectura) o solo export?** El explore recomendó export-only. La decisión del usuario fue "consumer". Resolver en spec.
3. **¿La distro forense incluye Ollama?** Si no, el default provider debe ser configurable (OpenRouter como fallback razonable). La spec debe definir el orden de fallback.
4. **¿7 plugins nuevos entran todos en PR-2 o se dividen?** Si son independientes, podrían ser PRs separados para facilitar review. La spec lo define.
5. **¿Tests para plugins legacy sin cobertura se agregan en PR-4 (security) o en PRs separados?** La spec debe asignar ownership.
