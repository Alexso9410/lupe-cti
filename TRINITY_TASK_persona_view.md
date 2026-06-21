# Task — Centinela Desktop: Vista "Persona OSINT"

## Objetivo

Agregar una 5ta vista **"Persona OSINT"** a la app de escritorio de centinela.
La vista permite investigar una persona por teléfono y/o username, mostrando resultados
de phone enrichment y búsqueda en redes sociales en una sola pantalla.

## Proyecto
`c:\Users\usuario\Documents\proyectos IA aplicada\centinela`

---

## Archivos a modificar

1. `centinela/desktop/bridge.py` — agregar método `enrich_person()`
2. `centinela/desktop/frontend/index.html` — agregar nav item + sección view

---

## PARTE 1 — `bridge.py`: Nuevo método `enrich_person`

### Leer primero
Lee el archivo completo para entender los imports y los patrones existentes antes de modificar.

### Patrón a replicar
Todos los métodos siguen este contrato exacto:
```python
def method_name(self, arg: str) -> dict[str, Any]:
    try:
        # lógica
        return {"success": True, "data": ..., "error": None}
    except Exception:
        return {"success": False, "data": None, "error": traceback.format_exc(limit=3)}
```

### Método a agregar

Agregá este método a la clase `CentinelaAPI`, después del método `enrich_ioc` existente:

```python
def enrich_person(
    self,
    phone: str = "",
    username: str = "",
    name: str = "",
    no_ai: bool = False,
    case_id: int | None = None,
) -> dict[str, Any]:
    """Enrich a person by phone and/or username.

    Args:
        phone: Phone number in international format (e.g. +54 9 2954 123456)
        username: Username to search across social platforms
        name: Full name (reference only, not enriched)
        no_ai: Skip AI analysis if True
        case_id: Link results to this case ID

    Returns:
        dict with success, phone_results, username_results, analysis, error
    """
    try:
        if not phone.strip() and not username.strip():
            return {
                "success": False,
                "phone_results": [],
                "username_results": [],
                "analysis": None,
                "error": "Debés proveer al menos un teléfono o username.",
            }

        settings = get_settings()
        phone_results: list[dict] = []
        username_results: list[dict] = []
        all_enrichments: list = []

        # --- Phone enrichment ---
        if phone.strip():
            phone_ioc = detect_ioc(phone.strip())
            if phone_ioc is None or phone_ioc.type.value != "phone":
                return {
                    "success": False,
                    "phone_results": [],
                    "username_results": [],
                    "analysis": None,
                    "error": f"'{phone}' no es un número válido. Usá formato +XX...",
                }
            enrichments = asyncio.run(run_enrichment(phone_ioc, settings))
            phone_results = [_enrichment_to_dict(e) for e in enrichments]
            all_enrichments.extend(enrichments)

            if case_id:
                ioc_id = self._db.upsert_ioc(phone_ioc)
                for e in enrichments:
                    self._db.save_enrichment(ioc_id, e)
                self._db.link_ioc_to_case(ioc_id, case_id)

        # --- Username enrichment ---
        if username.strip():
            from centinela.models import IOC, IOCType
            user_ioc = IOC(type=IOCType.username, value=username.strip())
            enrichments = asyncio.run(run_enrichment(user_ioc, settings))
            username_results = [_enrichment_to_dict(e) for e in enrichments]
            all_enrichments.extend(enrichments)

            if case_id:
                ioc_id = self._db.upsert_ioc(user_ioc)
                for e in enrichments:
                    self._db.save_enrichment(ioc_id, e)
                self._db.link_ioc_to_case(ioc_id, case_id)

        # --- AI analysis ---
        analysis: str | None = None
        if not no_ai and all_enrichments:
            # Use phone IOC as reference for AI if available, else username
            ref_ioc = detect_ioc(phone.strip()) if phone.strip() else IOC(type=IOCType.username, value=username.strip())
            analysis = asyncio.run(analyze_ioc(ref_ioc, all_enrichments, settings))

        return {
            "success": True,
            "phone_results": phone_results,
            "username_results": username_results,
            "analysis": analysis,
            "error": None,
        }
    except Exception:
        return {
            "success": False,
            "phone_results": [],
            "username_results": [],
            "analysis": None,
            "error": traceback.format_exc(limit=3),
        }
```

**IMPORTANTE**: verificá que `detect_ioc`, `run_enrichment`, `analyze_ioc`, `get_settings`,
`_enrichment_to_dict` ya están importados/disponibles en el scope de `bridge.py`.
Si `IOC` o `IOCType` no están importados al inicio del archivo, agregálos en la sección
de imports junto a los existentes.

---

## PARTE 2 — `index.html`: Nav item + View section

### Leer primero
Lee el archivo completo para entender la estructura antes de modificar.
Buscá las secciones de navegación y de vistas para insertar en el lugar correcto.

### 2a — Nav item (sidebar)

En la sección `<nav class="nav-menu">`, agregá este botón **después del botón de email**:

```html
<button class="nav-item" onclick="navigateTo('persona')">
    <span class="nav-icon">&#128100;</span>
    <span>Persona OSINT</span>
</button>
```

### 2b — Actualizar `navigateTo()`

En la función `navigateTo(viewName)`, agregá el caso para `'persona'`:

```javascript
if (viewName === 'persona') navItems[4].classList.add('active');
```

### 2c — View section

Agregá esta sección **antes de la etiqueta de cierre `</main>`** o después del último `</section>` de views existente:

```html
<!-- Vista 5: Persona OSINT -->
<section id="view-persona" class="view">
    <div class="view-header">
        <h2 class="view-title">&#128100; Persona OSINT</h2>
        <p class="view-subtitle">Investigá una persona por teléfono y/o username en fuentes abiertas</p>
    </div>

    <!-- Formulario de búsqueda -->
    <div class="card" style="margin-bottom: 20px;">
        <div class="card-header" style="background: var(--bg-tertiary);">
            <span style="font-weight: 600;">Datos del objetivo</span>
        </div>
        <div style="padding: 16px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;">
            <div class="form-group">
                <label class="form-label">Nombre (referencia)</label>
                <input type="text" id="persona-name" class="form-input" placeholder="Juan Pérez">
            </div>
            <div class="form-group">
                <label class="form-label">Teléfono</label>
                <input type="text" id="persona-phone" class="form-input" placeholder="+54 9 2954 123456">
            </div>
            <div class="form-group">
                <label class="form-label">Username</label>
                <input type="text" id="persona-username" class="form-input" placeholder="jperez">
            </div>
        </div>
        <div style="padding: 0 16px 16px; display: flex; align-items: center; gap: 24px; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <label class="form-label" style="margin: 0;">Caso (opcional)</label>
                <select id="persona-case-select" class="form-input" style="width: auto; min-width: 160px;">
                    <option value="">Sin caso</option>
                </select>
            </div>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-left: auto;">
                <input type="checkbox" id="persona-no-ai" style="accent-color: var(--accent-cyan);">
                <span style="font-size: 13px; color: var(--text-secondary);">Sin análisis IA</span>
            </label>
            <button id="btn-persona-enrich" class="btn btn-primary" style="padding: 10px 28px;" onclick="enrichPerson()">
                Investigar
            </button>
        </div>
    </div>

    <!-- Estado: sin resultados -->
    <div id="persona-empty" style="text-align: center; padding: 48px; color: var(--text-secondary);">
        <div style="font-size: 48px; margin-bottom: 16px;">&#128100;</div>
        <p>Ingresá un teléfono, username o ambos para comenzar la investigación.</p>
    </div>

    <!-- Estado: loading -->
    <div id="persona-loading" style="display: none; text-align: center; padding: 48px;">
        <div class="spinner" style="margin: 0 auto 16px;"></div>
        <p style="color: var(--text-secondary);">Investigando...</p>
    </div>

    <!-- Resultados -->
    <div id="persona-results" style="display: none;">

        <!-- Dos columnas: Teléfono | Redes sociales -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">

            <!-- Columna teléfono -->
            <div class="card" id="persona-phone-card">
                <div class="card-header" style="background: var(--bg-tertiary); display: flex; align-items: center; gap: 8px;">
                    <span>&#128222;</span>
                    <span style="font-weight: 600;">Teléfono</span>
                    <span id="persona-phone-badge" style="margin-left: auto; font-size: 11px; padding: 2px 8px; border-radius: 4px; background: var(--bg-secondary); color: var(--text-secondary);"></span>
                </div>
                <div id="persona-phone-content" style="padding: 16px;">
                    <p style="color: var(--text-secondary); font-size: 13px;">No se consultó teléfono.</p>
                </div>
            </div>

            <!-- Columna redes sociales -->
            <div class="card" id="persona-social-card">
                <div class="card-header" style="background: var(--bg-tertiary); display: flex; align-items: center; gap: 8px;">
                    <span>&#127760;</span>
                    <span style="font-weight: 600;">Redes Sociales</span>
                    <span id="persona-social-badge" style="margin-left: auto; font-size: 11px; padding: 2px 8px; border-radius: 4px; background: var(--bg-secondary); color: var(--text-secondary);"></span>
                </div>
                <div id="persona-social-content" style="padding: 16px;">
                    <p style="color: var(--text-secondary); font-size: 13px;">No se consultó username.</p>
                </div>
            </div>

        </div>

        <!-- Análisis IA -->
        <div class="card" id="persona-ai-card" style="display: none; margin-bottom: 20px;">
            <div class="card-header" style="background: var(--bg-tertiary);">
                <span style="font-weight: 600;">&#129302; Análisis IA</span>
            </div>
            <div id="persona-ai-content" style="padding: 16px; white-space: pre-wrap; font-size: 13px; line-height: 1.6;"></div>
        </div>

    </div>
</section>
```

### 2d — JavaScript: función `enrichPerson()`

Agregá esta función en el bloque de funciones JS del documento (cerca de `analyzeEmail()` o al final antes del cierre `</script>`):

```javascript
async function enrichPerson() {
    const phone = document.getElementById('persona-phone').value.trim();
    const username = document.getElementById('persona-username').value.trim();
    const name = document.getElementById('persona-name').value.trim();
    const noAi = document.getElementById('persona-no-ai').checked;
    const caseId = document.getElementById('persona-case-select').value;

    if (!phone && !username) {
        showToast('Ingresá al menos un teléfono o username', 'error');
        return;
    }

    // Show loading
    document.getElementById('persona-empty').style.display = 'none';
    document.getElementById('persona-results').style.display = 'none';
    document.getElementById('persona-loading').style.display = 'block';
    document.getElementById('btn-persona-enrich').disabled = true;

    try {
        const result = await window.pywebview.api.enrich_person(
            phone, username, name, noAi, caseId ? parseInt(caseId) : null
        );

        document.getElementById('persona-loading').style.display = 'none';
        document.getElementById('btn-persona-enrich').disabled = false;

        if (!result.success) {
            showToast(result.error || 'Error desconocido', 'error');
            document.getElementById('persona-empty').style.display = 'block';
            return;
        }

        // Render phone results
        const phoneContent = document.getElementById('persona-phone-content');
        const phoneBadge = document.getElementById('persona-phone-badge');
        if (result.phone_results && result.phone_results.length > 0) {
            phoneBadge.textContent = result.phone_results.length + ' fuentes';
            phoneBadge.style.background = 'rgba(0,180,216,0.1)';
            phoneBadge.style.color = 'var(--accent-cyan)';
            phoneContent.innerHTML = result.phone_results.map(r => `
                <div style="padding: 8px 0; border-bottom: 1px solid var(--border-subtle);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-family: monospace; font-size: 12px; color: var(--accent-cyan);">${escapeHtml(r.source)}</span>
                        <span class="severity-badge severity-${r.severity}">${r.severity}</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary); white-space: pre-wrap;">${escapeHtml(r.summary)}</div>
                </div>
            `).join('');
        } else if (phone) {
            phoneBadge.textContent = 'sin datos';
            phoneContent.innerHTML = '<p style="color: var(--text-secondary); font-size: 13px;">No se obtuvieron resultados para este número.</p>';
        }

        // Render username/social results
        const socialContent = document.getElementById('persona-social-content');
        const socialBadge = document.getElementById('persona-social-badge');
        if (result.username_results && result.username_results.length > 0) {
            // Find whats_my_name result for the found accounts list
            const wmnResult = result.username_results.find(r => r.source === 'whats_my_name');
            const foundCount = wmnResult ? (wmnResult.raw_data?.found_count || 0) : 0;

            socialBadge.textContent = foundCount + ' cuentas encontradas';
            socialBadge.style.background = foundCount > 0 ? 'rgba(0,180,216,0.1)' : 'var(--bg-secondary)';
            socialBadge.style.color = foundCount > 0 ? 'var(--accent-cyan)' : 'var(--text-secondary)';

            if (wmnResult && wmnResult.raw_data?.accounts?.length > 0) {
                const accounts = wmnResult.raw_data.accounts;
                socialContent.innerHTML = `
                    <div style="margin-bottom: 8px; font-size: 12px; color: var(--text-secondary);">
                        ${foundCount} cuentas encontradas para <strong style="color: var(--text-primary);">${escapeHtml(username)}</strong>
                    </div>
                    <div style="max-height: 320px; overflow-y: auto;">
                        ${accounts.map(a => `
                            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--border-subtle);">
                                <span style="font-size: 13px; color: var(--text-primary);">${escapeHtml(a.site)}</span>
                                <a href="${escapeHtml(a.url)}" target="_blank" style="font-size: 11px; color: var(--accent-cyan); font-family: monospace; text-decoration: none;"
                                   onclick="event.preventDefault(); window.pywebview.api.open_url && window.pywebview.api.open_url('${escapeHtml(a.url)}')">
                                    ver ↗
                                </a>
                            </div>
                        `).join('')}
                    </div>
                `;
            } else {
                socialContent.innerHTML = '<p style="color: var(--text-secondary); font-size: 13px;">No se encontraron cuentas para este username.</p>';
            }
        } else if (username) {
            socialBadge.textContent = 'sin datos';
            socialContent.innerHTML = '<p style="color: var(--text-secondary); font-size: 13px;">No se obtuvieron resultados para este username.</p>';
        }

        // Render AI analysis
        if (result.analysis) {
            document.getElementById('persona-ai-card').style.display = 'block';
            document.getElementById('persona-ai-content').textContent = result.analysis;
        } else {
            document.getElementById('persona-ai-card').style.display = 'none';
        }

        document.getElementById('persona-results').style.display = 'block';

        if (caseId) {
            showToast('Investigación guardada en el caso', 'success');
        }

    } catch (err) {
        document.getElementById('persona-loading').style.display = 'none';
        document.getElementById('btn-persona-enrich').disabled = false;
        document.getElementById('persona-empty').style.display = 'block';
        showToast('Error: ' + err.message, 'error');
    }
}
```

### 2e — Cargar casos en el select al navegar

En la función `navigateTo(viewName)`, donde ya se cargan casos para otras vistas, agregá:

```javascript
if (viewName === 'persona') { navItems[4].classList.add('active'); loadPersonaCases(); }
```

Y agregá la función auxiliar:

```javascript
async function loadPersonaCases() {
    try {
        const result = await window.pywebview.api.get_cases();
        const select = document.getElementById('persona-case-select');
        if (result.success && result.cases) {
            const existing = select.innerHTML;
            select.innerHTML = '<option value="">Sin caso</option>' +
                result.cases.map(c => `<option value="${c.id}">#${c.id} — ${escapeHtml(c.name)}</option>`).join('');
        }
    } catch (e) {}
}
```

---

## Verificación final

Después de implementar, hacé lo siguiente:

1. Lanzá la app:
```bash
cd "c:\Users\usuario\Documents\proyectos IA aplicada\centinela"
python centinela-desktop.py
```

2. Verificá que:
   - La 5ta pestaña "Persona OSINT" aparece en el sidebar
   - El formulario tiene los 3 campos (Nombre, Teléfono, Username)
   - Al poner `+54 9 11 5555 5555` y hacer clic en "Investigar", aparecen resultados en la columna Teléfono
   - Al poner un username como `admin` y buscar, aparecen cuentas en la columna Redes Sociales
   - Sin teléfono ni username, muestra error en toast

3. Si hay errores de Python (bridge), van a aparecer en el toast rojo con el traceback.

---

## Notas importantes

- `escapeHtml()` ya existe en el frontend — no la redefinas
- `showToast()` ya existe — úsala para mensajes de error/éxito
- `.severity-badge` y `.severity-{level}` ya tienen estilos definidos — úsalos
- La clase `.spinner` ya existe en el CSS
- NO modifiques la lógica de ninguna otra vista
- El link "ver ↗" en cuentas: si `open_url` no existe en el bridge, el onclick simplemente no hace nada — está protegido con `&&`
