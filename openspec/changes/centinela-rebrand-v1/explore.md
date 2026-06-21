# SDD Explore: Centinela Rebrand v1

**Fecha:** 2026-06-20
**Cambio:** `centinela-rebrand-v1`
**Scope:** Rebrand completo de nombre, identidad visual, y expansión de capabilities

---

## 1. Inventario del proyecto actual

### 1.1 Arquitectura general

Centinela es un CLI de enriquecimiento e investigación de IOCs (Indicadores de Compromiso) para Heimdall Security. Arquitectura modular con plugin system async.

```
centinela/
├── cli.py                 # Typer CLI (config, case, person, enrich, email)
├── desktop/
│   ├── app.py             # pywebview wrapper
│   └── bridge.py          # JS-Python bridge
├── enrichment/
│   ├── base.py            # EnrichmentPlugin ABC
│   ├── __init__.py        # run_enrichment() concurrente (semaphore=5)
│   └── plugins/           # 20+ plugins individuales
├── export/
│   ├── obsidian.py        # Markdown + frontmatter + MITRE ATT&CK
│   ├── json_export.py     # Raw JSON
│   └── pdf_report.py      # ReportLab PDF
├── email_parser.py        # Parser de .eml
├── email_analyzer.py      # Análisis de phishing + score
├── analysis.py            # AI analysis vía Ollama
├── ioc_detect.py          # Regex-based auto-detection
├── db.py                  # SQLite + auto-migration
├── config.py              # pydantic-settings
└── models.py              # IOC, EnrichmentResult, IOCType
```

### 1.2 IOC Types soportados

| IOC Type | Detección | Plugins compatibles |
|----------|-----------|---------------------|
| SHA256 | Regex (64 hex) | VirusTotal, MalwareBazaar, ThreatFox |
| SHA1 | Regex (40 hex) | VirusTotal, MalwareBazaar, ThreatFox |
| MD5 | Regex (32 hex) | VirusTotal, MalwareBazaar, ThreatFox |
| URL | Regex compuesto | URLhaus, URLScan, VirusTotal, IPQS |
| Email | Regex RFC 5322 | HaveIBeenPwned |
| Phone | Regex E.164 | NumVerify, IPQS (phone), PhoneStatic |
| IPv4 | Regex + validación | AbuseIPDB, VirusTotal, Shodan, GreyNoise, IPinfo, Whois, ThreatFox, OTX |
| IPv6 | Regex + validación | AbuseIPDB, VirusTotal, Shodan, IPinfo, Whois |
| Domain | Regex + TLD check | Whois, VirusTotal, Shodan, OTX, ThreatFox, URLScan, IPQS |
| Username | Heurística | WhatsMyName |

### 1.3 Plugins existentes (20+)

**Plugins gratuitos (sin API key):**

| Plugin | Fuente | IOC Types | Rate Limit |
|--------|--------|-----------|------------|
| WhoisPlugin | whois | domain, IPv4, IPv6 | N/A |
| IpInfoPlugin | ipinfo.io (free tier) | IPv4, IPv6 | 50k/mes |
| ThreatFoxPlugin | abuse.ch/ThreatFox | hash, URL, IPv4, domain | N/A |
| URLhausPlugin | abuse.ch/URLhaus | URL, domain | N/A |
| MalwareBazaarPlugin | abuse.ch/MalwareBazaar | hash | N/A |
| PhoneStaticPlugin | Datos estáticos | phone | N/A |
| WhatsMyNamePlugin | whatsmyname.app | username | N/A |

**Plugins con API key (condicionalmente cargados):**

| Plugin | Fuente | IOC Types | Pricing |
|--------|--------|-----------|---------|
| AbuseIPDB | abuseipdb.com | IPv4, IPv6 | Freemium (1k/día gratis) |
| VirusTotal | virustotal.com | hash, URL, domain, IPv4 | Freemium (4 lookups/min) |
| Shodan | shodan.io | IPv4, IPv6, domain | Freemium (100 créditos/mes) |
| OTX (AlienVault) | otx.alienvault.com | hash, IPv4, domain, URL | Free (sin límite declarado) |
| URLScan | urlscan.io | URL, domain | Freemium (5k/mes) |
| HaveIBeenPwned | haveibeenpwned.com | email | Freemium (rate limited) |
| GreyNoise | greynoise.io | IPv4 | Freemium (10k/mes) |
| IPQS | ipqualityscore.com | IPv4, URL, email, phone | Freemium (5k/mes) |
| NumVerify | numverify.com | phone | Freemium (100/mes) |

### 1.4 Capacidades actuales

- **Detección automática** de IOCs por regex con prioridad jerárquica
- **Enriquecimiento concurrente** con semaphore de 5 conexiones paralelas
- **Persistencia** en SQLite con schema auto-migrado
- **Casos de investigación** (tablas: cases, case_iocs, case_notes)
- **Análisis de emails** (.eml): headers, SPF/DKIM/DMARC, attachments, IOCs, phishing score
- **Exportación**: Obsidian (Markdown + frontmatter), JSON, PDF
- **AI Analysis** vía Ollama (silently no-ops si no está disponible)
- **Desktop GUI** vía pywebview (HTML/JS frontend embebido)
- **Integración opcional** con Heimdall dashboard (`agent_writer_bridge.py`)

### 1.5 Capa de configuración

- `pydantic-settings` con prefix `CENTINELA_`
- `.env` file support
- Settings clave: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `DB_PATH`, y una variable por API key

---

## 2. Mapa de gaps

### 2.1 Plugins: lo que tenemos vs. lo que tiene el ecosistema

**Cobertura completa (tenemos alternativas):**
- IP reputation: ✅ AbuseIPDB, GreyNoise, IPQS, IPinfo, Shodan
- Hash lookup: ✅ VirusTotal, MalwareBazaar, ThreatFox
- URL scanning: ✅ URLScan, URLhaus, VirusTotal
- Domain/Whois: ✅ Whois, VirusTotal, Shodan
- Email breach: ✅ HaveIBeenPwned
- Phone: ✅ NumVerify, IPQS, PhoneStatic
- Username: ✅ WhatsMyName

**Cobertura parcial o ausente:**

| Capacidad | Plugins faltantes | Impacto |
|-----------|-------------------|---------|
| Sandbox analysis | Hybrid Analysis, AnyRun, Joe Sandbox | Alto — análisis dinámico de malware |
| Threat intel feeds MISP | MISP, Intel471, Recorded Future | Alto — intel contextualizada |
| Passive DNS | Farsight DNSDB, SecurityTrails, Spyse | Medio — histórico de resoluciones |
| SSL/TLS cert analysis | Censys, BinaryEdge, crt.sh | Medio — fingerprinting de infraestructura |
| Dark web monitoring | None | Alto — no hay integración |
| Geolocation avanzada | IP2Location, MaxMind GeoIP2 | Medio — geolocalización más precisa |
| Reputation de ASN/BGP | BGPView, Hurricane Electric | Bajo — contexto de infraestructura |
| IoT/ICS scanning | Shodan (exploits), Censys | Medio — para infra crítica |
| Threat hunting | Cisco Talos, FortiGuard, Kaspersky TIP | Medio — feeds de vendors |
| Abuse reporting | Abuse.ch (ya tenemos 3), Spamhaus | Bajo — reporting automático |

### 2.2 Features ausentes vs. herramientas similares

| Feature | Herramienta de referencia | Estado en Centinela |
|---------|---------------------------|---------------------|
| Correlación entre IOCs | MISP, TheHive | ❌ No existe |
| Timelines de incidentes | TheHive, Velociraptor | ❌ No existe |
| Playbooks/Workflows | Shuffle, n8n, Splunk SOAR | ❌ No existe |
| IOC sharing (TAXII/STIX) | MISP, OpenCTI | ❌ No existe |
| Visualización de relaciones | Maltego, OpenCTI | ❌ No existe |
| Webhooks para alerts | Custom | ❌ No existe |
| API REST propia | Any modern tool | ❌ Solo CLI |
| Bulk enrichment | Mature tools | ⚠️ Parcial (CLI batch?) |
| IOC expiration / freshness | MISP, ThreatFox | ⚠️ No gestionado explícitamente |
| Tagging/colaboración | TheHive, DFIR-IRIS | ⚠️ Cases existen pero sin tags |

### 2.3 Gaps técnicos

- **No hay tests para ~50% de los plugins** — solo plugins clave tienen tests (VirusTotal, AbuseIPDB)
- **No hay health checks** de los servicios externos
- **No hay circuit breaker** — si un plugin falla, puede bloquear todo el enrichment
- **No hay caching** de respuestas de plugins
- **No hay métricas** de uso/rate limits
- **Frontend desktop es un solo HTML monolítico** (`centinela_kimi_frontend.html`) — sin framework JS, difícil de mantener

---

## 3. Oportunidades de mejora concretas

### 3.1 Plugins nuevos candidatos (priorizados)

**Alta prioridad (gratis/freemium, alta utilidad):**

| Plugin | API | IOC Types | Costo | Por qué |
|--------|-----|-----------|-------|---------|
| **Hybrid Analysis** | hybrid-analysis.com/api | hash, URL | Free (con registro) | Sandbox dinámico de malware. Complementa hash estáticos |
| **Censys** | search.censys.io/api | IPv4, IPv6, domain, cert | Freemium (250/mes) | SSL/TLS, banners, infra. Más profundo que Shodan en certs |
| **crt.sh** | crt.sh (scraping/JSON) | domain | Free | Passive SSL cert transparency logs. Zero cost |
| **MISP** | MISP instance REST | hash, IPv4, domain, URL | Self-hosted/Free | Threat intel contextualizada, correlación |
| **Cisco Talos** | talosintelligence.com | IPv4, domain | Free (sin API key formal) | Reputación de IPs, categorización |
| **Spamhaus** | Spamhaus DQS | IPv4, domain, hash | Free tier | Reputación anti-spam, blocklists |
| **Blocklist.de** | api.blocklist.de | IPv4 | Free | IPs reportadas por fail2ban |

**Media prioridad:**

| Plugin | API | IOC Types | Costo | Por qué |
|--------|-----|-----------|-------|---------|
| **SecurityTrails** | securitytrails.com | domain, IPv4 | Freemium | Passive DNS, WHOIS history |
| **BinaryEdge** | binaryedge.io | IPv4, domain | Freemium | Similar a Shodan, complementa |
| **Spyse** | spyse.com | domain, IPv4 | Freemium | OSINT aggregator |
| **Fofa** | fofa.info | IPv4, domain, cert | Freemium (china) | Motor de búsqueda de ciberespacio |
| **ONYPHE** | onyphe.io | IPv4, domain | Freemium | OSINT aggregator francés |
| **AnyRun** | any.run/api | hash, URL | Freemium | Sandbox interactivo (mejor UX que HA) |

**Baja prioridad / Enterprise:**

| Plugin | API | IOC Types | Costo | Nota |
|--------|-----|-----------|-------|------|
| Recorded Future | api.recordedfuture.com | All | Pago | Enterprise TIP |
| Intel471 | api.intel471.com | All | Pago | Enterprise TIP |
| Flashpoint | api.flashpoint.io | All | Pago | Dark web intel |
| Kaspersky TIP | tip.kaspersky.com | hash, URL, IPv4 | Freemium | Vendor-specific |
| FortiGuard | fortiguard.com | IPv4, URL, domain | Free (scraping) | Categorización web |

### 3.2 Features nuevos candidatos

| Feature | Complejidad | Valor | Notas técnicas |
|---------|-------------|-------|----------------|
| **Caching layer** para plugins | Medio | Alto | TTL por plugin (ej. VT 1h, Whois 24h). Evita rate limits |
| **Circuit breaker** por plugin | Medio | Alto | Si un plugin falla N veces, skip por X minutos |
| **Health checks / métricas** | Medio | Medio | Endpoint o comando para ver estado de plugins |
| **Bulk enrichment desde archivo** | Bajo | Medio | `centinela enrich --file iocs.txt` |
| **Webhooks** | Medio | Medio | Notificar cuando un enrichment encuentra un IOC malicioso |
| **API REST (FastAPI)** | Alto | Alto | Convertir el core en servicio API para integraciones |
| **STIX/TAXII export** | Alto | Medio | Compatibilidad con MISP, OpenCTI |
| **Visualización de relaciones** | Alto | Medio | Graph de relaciones entre IOCs (NetworkX + D3) |
| **Tags y taxonomías** | Bajo | Medio | Tags en IOCs, cases, enrichments. Taxonomía MITRE ATT&CK |
| **Modo daemon/scheduler** | Medio | Medio | Re-enrichment periódico de IOCs almacenados |

### 3.3 Mejoras de DX (Developer Experience)

- **Pytest coverage** para todos los plugins (actualmente ~50% sin tests)
- **Plugin generator template** — scaffolding de nuevo plugin con un comando
- **Documentación de plugins** auto-generada desde los metadatos de clase
- **Pre-commit hooks** para linting, formatting, type checking
- **Dockerfile** para deployment containerizado

---

## 4. Lista exhaustiva de lugares donde aparece "centinela"

### 4.1 Código fuente y configuración

| Path | Líneas afectadas | Contexto | Severidad |
|------|-----------------|----------|-----------|
| `pyproject.toml` | `name`, entry points `[project.scripts]`, `packages` | Nombre del paquete, comandos CLI | **Crítico** |
| `centinela/` | Directorio completo | Nombre del paquete Python | **Crítico** |
| `centinela/__init__.py` | `__version__`, `__app_name__` | Metadata del paquete | **Crítico** |
| `centinela/config.py` | `Settings` class, env var prefix | `CENTINELA_*` prefix en todas las variables | **Crítico** |
| `centinela/cli.py` | `app = typer.Typer(name="centinela")`, help text, commands | Nombre del CLI y subcomandos | **Crítico** |
| `centinela/db.py` | `Database` class, schema, path default | `~/.centinela/centinela.db` path por defecto | **Crítico** |
| `centinela/desktop/app.py` | Título de ventana, nombre de app, tray icon | `title="Centinela"` en pywebview | **Alto** |
| `centinela/desktop/bridge.py` | Nombre de app en JS bridge | Referencias en métodos bridge | **Medio** |
| `centinela/integrations/agent_writer_bridge.py` | Referencias al nombre del producto | Texto/labels para dashboard | **Medio** |
| `centinela/analysis.py` | System prompt para Ollama | Puede mencionar "Centinela" en el contexto | **Medio** |

### 4.2 Frontend y assets

| Path | Contexto | Severidad |
|------|----------|-----------|
| `centinela/desktop/centinela_kimi_frontend.html` | Título HTML, branding, CSS classes, JS variables | **Crítico** |
| `centinela/desktop/frontend/index.html` | Título, branding | **Crítico** |
| `centinela_kimi_frontend.html` (root) | Copia del frontend | **Crítico** |

### 4.3 Documentación y metadata

| Path | Contexto | Severidad |
|------|----------|-----------|
| `CLAUDE.md` | Título, descripción, comandos | **Medio** |
| `README.md` (si existe) | Título, badges, instrucciones | **Medio** |
| `.env.example` | Variables `CENTINELA_*` | **Alto** |
| `.env` | Variables `CENTINELA_*` (no versionado, pero mencionar) | **Bajo** |
| `tests/` | Fixtures, paths, nombres de test | **Medio** |

### 4.4 Scripts y entry points

| Path | Contexto | Severidad |
|------|----------|-----------|
| `centinela-desktop.py` (root) | Entry point standalone para desktop | **Alto** |
| `setup.py` / `setup.cfg` (si existen) | Nombre del paquete | **Crítico** |

### 4.5 Notas sobre el rebrand

- **Total estimado de archivos a tocar:** ~15-20 archivos directamente
- **Total estimado de ocurrencias:** ~80-120 referencias textuales
- **Patrón de búsqueda recomendado:** `(?i)centinela` (case-insensitive) para no perder "Centinela" o "CENTINELA"
- **Consideración especial:** Las variables de entorno `CENTINELA_*` son breaking change para usuarios existentes. Se necesita periodo de deprecación o backward compatibility.
- **Base de datos existente:** El path `~/.centinela/centinela.db` contendrá datos históricos. Migración o notificación al usuario requerida.

---

## 5. Identidad visual

### 5.1 Naming analysis

**Nombre actual:** "Centinela"
- Pros: En español, claro, corto, memorable
- Cons: Genérico, conflictos de trademark posibles, no único en el espacio de ciberseguridad

**Candidatos de rename (si aplica):**

| Nombre | Dominio probable | Trademark risk | SEO | Notas |
|--------|-----------------|---------------|-----|-------|
| **Centinela** (mantener) | N/A | Medio | Difícil | Ya establecido internamente |
| **Sentinel** (inglés) | sentinel-osint.xyz | Alto | Muy difícil | Saturado (Redis Sentinel, HashiCorp) |
| **Vigía** | vigia-intel.dev | Bajo | Medio | Corto, en español, único |
| **Almena** | almena-security.io | Bajo | Medio | Metáfora arquitectónica de vigilancia |
| **Faro** | faro-osint.io | Medio | Medio | Metáfora de guía/iluminación |
| **Heimdall Intel** | heimdall-intel.dev | Medio-Alto | Medio | Conexión con Heimdall Security (empresa matriz) |

**Recomendación:** Si el rebrand es solo modernización visual, **mantener "Centinela"** pero con identidad visual fuerte. Si el rebrand incluye estrategia de producto/open source, considerar **"Vigía"** o **"Almena"** para evitar colisiones.

### 5.2 Paleta de colores sugerida

Tema actual: Desconocido (frontend es HTML monolítico con estilos inline/embebidos).

**Paleta propuesta (ciberseguridad / threat intel):**

| Rol | Color | Hex | Uso |
|-----|-------|-----|-----|
| Primary | Deep Indigo | `#1a1a2e` | Fondos principales, navbar |
| Secondary | Cyan Alert | `#00d4ff` | Acentos, botones primarios, highlights |
| Accent | Threat Red | `#ff3860` | IOCs maliciosos, alertas, score alto |
| Accent 2 | Safe Green | `#2ecc71` | IOCs limpios, verificaciones OK |
| Accent 3 | Warning Amber | `#f1c40f` | Suspicious, medium risk |
| Background | Dark Void | `#0f0f1a` | Fondo general (dark mode) |
| Surface | Panel Dark | `#16213e` | Cards, panels, modales |
| Text Primary | White | `#ffffff` | Texto principal |
| Text Secondary | Muted Gray | `#a0a0b0` | Labels, metadata |

**Inspiración:** Similar a Splunk Phantom, MISP, y TheHive — dark theme por defecto porque operadores SOC trabajan de noche.

### 5.3 Logo concept

**Concepto:** Un ojo estilizado con elementos de red/circuito.
- **Forma:** Ojo minimalista donde la pupila es un nodo de red con conexiones
- **Icono favicon:** Simplificación a solo el nodo+pupila (16x16 y 32x32)
- **Variantes:** Color (Cyan), monocromo blanco, monocromo negro

**Formatos necesarios:**
- SVG (para web/frontend)
- PNG 32x32, 64x64, 128x128, 256x256, 512x512
- ICO (para desktop app Windows)
- ICNS (para desktop app macOS, si aplica)

### 5.4 Tipografía

| Uso | Fuente | Fallback |
|-----|--------|----------|
| Headings / Brand | Inter o JetBrains Mono | system-ui, sans-serif |
| Body / UI | Inter | system-ui, sans-serif |
| Monospace (IOCs, hashes) | JetBrains Mono | Consolas, monospace |

**Nota:** JetBrains Mono tiene ligaduras y distinción clara entre `0`/`O`, `1`/`l`/`I` — crítico para hashes hexadecimales.

---

## 6. Riesgos y blockers

### 6.1 Breaking changes

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| **Rename de variables de entorno** `CENTINELA_*` → `NEWNAME_*` | Alto | Periodo de deprecación: leer ambas variables por 2 versiones. Warning en CLI |
| **Rename del paquete Python** `centinela` → `newname` | Alto | Soft migration: mantener `centinela` como alias package por 1-2 versiones |
| **Path de base de datos** `~/.centinela/` cambia | Medio | Copiar/Mover db automáticamente al nuevo path en primera ejecución post-update |
| **Entry points del CLI** cambian | Medio | `pip install` reinstala entry points. Documentar en CHANGELOG |
| **Imports en código externo** (Heimdall bridge) | Medio | Heimdall usa import dinámico — verificar que no hardcodee el nombre |

### 6.2 Dependencias y vulnerabilidades

**Estado de análisis de vulnerabilidades:**
- ❌ **No se realizó análisis de vulnerabilidades en dependencias durante esta exploración**
- ❌ **No se ejecutó `pip-audit`, `safety check`, ni `bandit`**
- ⚠️ Recomendación: Antes de cualquier release post-rebrand, ejecutar:
  ```bash
  pip install pip-audit bandit safety
  pip-audit .
  bandit -r centinela/
  safety check
  ```

**Dependencias externas críticas:**

| Dependencia | Uso | Riesgo |
|-------------|-----|--------|
| `httpx` | Todas las llamadas a APIs externas | Baja (muy mantenido) |
| `typer` | CLI framework | Baja |
| `pydantic-settings` | Configuración | Baja |
| `pywebview` | Desktop GUI | Medio — depende de WebView del SO, menos mantenido |
| `reportlab` | PDF generation | Medio — legacy, menos activo |
| `ollama` (via HTTP) | AI analysis | Baja (HTTP API, no dependencia fuerte) |

### 6.3 Infraestructura externa

| Dependencia | Tipo | Riesgo |
|-------------|------|--------|
| Ollama (local) | AI analysis | Si no está corriendo, feature se silencia. No es blocker |
| Heimdall dashboard | Integración opcional | Si no existe path, se deshabilita silenciosamente. No es blocker |
| ~20 APIs externas | Enrichment | Rate limits, cambios de API, deprecación. Ninguna es blocker individual |

### 6.4 Riesgos técnicos del proyecto

| Riesgo | Probabilidad | Impacto | Descripción |
|--------|-------------|---------|-------------|
| Frontend monolítico sin framework | Alta | Medio | `centinela_kimi_frontend.html` es unmaintainable a mediano plazo |
| Falta de tests en plugins | Alta | Medio | Cambios en plugins pueden romper sin detectarse |
| No hay CI/CD | Medio | Medio | Releases manuales, sin tests automáticos en PRs |
| No hay logging estructurado | Medio | Bajo | `print()` o logging básico. Difícil debug en producción |
| SQLite sin backup | Medio | Alto | Datos de investigación en riesgo. No hay backup automático |

### 6.5 Blockers identificados

**Ningún blocker crítico que impida el rebrand.**

Los únicos items que podrían bloquear son:
1. **Decisión de nombre final** — debe resolverse antes de tocar código
2. **Aprobación de paleta/logo** — si incluye assets gráficos
3. **Estrategia de migración de variables de entorno** — acordar si se hace hard cut o graceful deprecation

---

## 7. Recomendación de encadenamiento (PRs)

### Estrategia general

Dado que el rebrand afecta **nomenclatura, branding, paths, y configuración**, la estrategia es encadenar PRs pequeños, autovalorables, y sin dependencias cíclicas. Cada PR debe tener sus propios tests.

### Secuencia de PRs propuesta

#### PR-1: `chore/rename-python-package`
**Scope:** Renombrar el paquete Python internamente (directorio `centinela/` y todos los imports)
**Tamaño estimado:** ~15 archivos, ~200 líneas
**Tests:**
- Todos los tests existentes deben pasar con los nuevos imports
- Verificar que `pip install -e .` instala el paquete correctamente
**Notas:**
- NO cambiar variables de entorno ni entry points todavía
- Mantener compatibilidad: crear `centinela/__init__.py` como re-export si es posible
- Cambiar solo los imports internos y el nombre del directorio del paquete

#### PR-2: `feat/rename-cli-and-entrypoints`
**Scope:** Renombrar entry points (`pyproject.toml` scripts), nombre del CLI Typer, y comandos
**Tamaño estimado:** ~5 archivos
**Tests:**
- Verificar que el comando CLI nuevo funciona (`newname --version`, `newname enrich`)
- Verificar que el entry point del desktop funciona (`newname-desktop`)
**Notas:**
- Deprecar el entry point viejo con warning (ej. `centinela` comando imprime "Use `newname`")
- Actualizar `pyproject.toml` scripts section

#### PR-3: `feat/rename-environment-variables`
**Scope:** Cambiar prefix `CENTINELA_*` → `NEWNAME_*` en `config.py`, `.env.example`, docs
**Tamaño estimado:** ~3-5 archivos
**Tests:**
- Unit tests de Settings con nuevos nombres
- Unit tests de backward compatibility (leer variable vieja también)
**Notas:**
- Implementar graceful fallback: leer `NEWNAME_*` primero, si no existe leer `CENTINELA_*` con deprecation warning
- Actualizar `.env.example` y CLAUDE.md

#### PR-4: `feat/rename-db-path-and-migration`
**Scope:** Cambiar path default de `~/.centinela/` a `~/.newname/`
**Tamaño estimado:** ~2-3 archivos
**Tests:**
- Test de migración automática: si existe `~/.centinela/centinela.db`, copiar a nuevo path
- Test de primera instalación limpia
**Notas:**
- No eliminar el directorio viejo, solo copiar
- Logging informativo al usuario sobre la migración

#### PR-5: `feat/rebrand-frontend-and-assets`
**Scope:** Renombrar títulos, branding, CSS en frontend HTML. Agregar logo SVG.
**Tamaño estimado:** ~3-5 archivos
**Tests:**
- Tests visuales manuales (screenshots del desktop app)
- Verificar que el título de ventana es correcto
**Notas:**
- NO reescribir el frontend completamente — solo rebrand superficial
- Agregar logo SVG inline o como asset estático

#### PR-6: `docs/update-documentation-and-branding`
**Scope:** Actualizar CLAUDE.md, README, comentarios, docstrings
**Tamaño estimado:** ~5-10 archivos
**Tests:**
- N/A (solo docs)
**Notas:**
- Último PR de la cadena
- Incluye actualización de CHANGELOG

### Diagrama de dependencias

```
PR-1 (package rename)
  └── PR-2 (CLI rename)
        └── PR-3 (env vars)
              └── PR-4 (db path)
                    └── PR-5 (frontend)
                          └── PR-6 (docs)
```

**Reglas:**
- Cada PR es **autovalorable** — puede mergearse a `main` sin depender de los siguientes
- Los PRs pueden apilarse o hacerse en paralelo si se usan feature flags
- Si se usa feature flag (config `USE_NEW_BRANDING`), los PRs 1-5 podrían hacerse en paralelo

### Alternativa: Big-bang PR

| Approach | Pros | Cons | Recomendación |
|----------|------|------|---------------|
| **Chain PRs** (propuesta) | Reviewable, rollback fácil, tests por PR, menor riesgo | Más trabajo de orchestración | ✅ **Recomendado** |
| **Big-bang single PR** | Menos overhead de git, un solo review | Difícil de reviewar, rollback todo o nada, más riesgo | ❌ No recomendado para este scope |

---

## Resumen ejecutivo para el orchestrator

- **Plugins analizados:** 20 plugins existentes documentados, 15+ candidatos nuevos identificados
- **Plugins nuevos candidatos:** 7 de alta prioridad (Hybrid Analysis, Censys, crt.sh, MISP, Cisco Talos, Spamhaus, Blocklist.de)
- **Archivos donde hay que tocar "centinela":** ~20 archivos directamente, ~80-120 ocurrencias textuales
- **Vulnerabilidades detectadas:** Ninguna — **no se ejecutó análisis de seguridad en esta fase**. Recomendación: hacer `pip-audit` + `bandit` antes del release
- **PRs encadenados recomendados:** 6 PRs autovalorables (package → CLI → env → db → frontend → docs)
- **Status:** `ready` — No hay blockers técnicos. Solo depende de decisión de nombre y aprobación de diseño visual
- **Skill resolution:** `injected` — Skill `sdd-explore` cargado y seguido
