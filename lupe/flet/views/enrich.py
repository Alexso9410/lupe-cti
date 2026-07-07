"""Enrich view — IOC enrichment interface connected to run_enrichment."""

from __future__ import annotations

import flet as ft

from lupe.case import add_ioc_to_case, create_case, list_cases
from lupe.config import get_settings
from lupe.db import Database
from lupe.enrichment import run_enrichment
from lupe.flet.theme import CYAN, MATRIX_GREEN
from lupe.flet.utils import show_snackbar
from lupe.ioc_detect import detect_ioc
from lupe.llm.registry import get_provider


def _save_enrichment_to_db(ioc_value: str, ioc_type: str, results: list) -> None:
    """Persist enrichment results to the SQLite database."""
    settings = get_settings()
    db = Database(settings.db_path)
    ioc_id = db.upsert_ioc(ioc_type, ioc_value)
    for r in results:
        try:
            db.save_enrichment(ioc_id, r.source, r.severity.value, r.summary, r.raw_data)
        except Exception:
            pass


def _save_ai_analysis_to_db(ioc_value: str, ioc_type: str, model: str, summary: str) -> None:
    """Persist AI analysis result to the SQLite database."""
    settings = get_settings()
    db = Database(settings.db_path)
    ioc_id = db.upsert_ioc(ioc_type, ioc_value)
    try:
        db.save_analysis(ioc_id, model, summary)
    except Exception:
        pass


def build_enrich_view(page: ft.Page) -> ft.Control:
    """Build the enrich view with IOC enrichment functionality.

    Args:
        page: The Flet page (for snack_bar and run_task).

    Returns:
        A Flet Column control for the enrich view.
    """
    # --- Input ---
    ioc_field = ft.TextField(
        label="IOC Value",
        hint_text="e.g. 8.8.8.8, example.com, d41d8cd98f00b204e9800998ecf8427e",
        border_color=MATRIX_GREEN,
        focused_border_color=CYAN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        label_style=ft.TextStyle(color=ft.Colors.WHITE70),
        expand=True,
    )

    # --- Results ---
    results_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Source", color=CYAN)),
            ft.DataColumn(ft.Text("Finding", color=CYAN)),
            ft.DataColumn(ft.Text("Severity", color=CYAN)),
        ],
        rows=[],
        visible=False,
    )
    progress_ring = ft.ProgressRing(visible=False, width=20, height=20)
    status_text = ft.Text("", color=ft.Colors.WHITE70, size=13)

    # --- State ---
    _enrichment_results: list = []
    _ioc_value: dict[str, str] = {"value": ""}
    _ioc_type: dict[str, str] = {"value": ""}

    # --- Button ---
    enrich_btn = ft.ElevatedButton(
        "Enrich",
        icon=ft.Icons.SEARCH,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
    )

    def _show_snackbar(msg: str, color: str = MATRIX_GREEN) -> None:
        show_snackbar(page, msg, color)

    async def _enrich(e: ft.ControlEvent):
        ioc_value = ioc_field.value.strip() if ioc_field.value else ""
        if not ioc_value:
            _show_snackbar("Enter an IOC value to enrich", "#ff5555")
            return

        # Detect IOC type
        ioc = detect_ioc(ioc_value)
        if ioc is None:
            msg = "IOC not recognized — enter a valid IP, domain, hash, URL, or email"
            _show_snackbar(msg, "#ff5555")
            return

        # Loading state
        enrich_btn.disabled = True
        progress_ring.visible = True
        status_text.value = f"Enriching {ioc.type.value}: {ioc_value}..."
        results_table.visible = False
        results_table.rows.clear()
        page.update()

        try:
            settings = get_settings()
            results = await run_enrichment(ioc, settings)

            # Populate results table
            for r in results:
                severity_color = _severity_color(r.severity)
                results_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(r.source, color=ft.Colors.WHITE)),
                            ft.DataCell(ft.Text(r.summary, color=ft.Colors.WHITE)),
                            ft.DataCell(ft.Text(r.severity.value, color=severity_color)),
                        ]
                    )
                )
            results_table.visible = True
            status_text.value = f"{len(results)} plugin(s) responded"
            _show_snackbar(f"{len(results)} plugins responded for {ioc_value}")

            # Store results for AI analysis and case linking
            _enrichment_results.clear()
            _enrichment_results.extend(results)
            _ioc_value["value"] = ioc_value
            _ioc_type["value"] = ioc.type.value

            # Persist enrichment results to DB for case history
            _save_enrichment_to_db(ioc_value, ioc.type.value, results)

            # Show AI Analysis and Investigation panels
            ai_panel.visible = True
            case_panel.visible = True

            # Refresh case dropdown
            _refresh_cases()

        except Exception as exc:
            status_text.value = f"Error: {exc}"
            _show_snackbar(f"Enrichment failed: {exc}", "#ff5555")
        finally:
            enrich_btn.disabled = False
            progress_ring.visible = False
            page.update()

    enrich_btn.on_click = _enrich

    # ======================================================================
    # AI Analysis Panel
    # ======================================================================

    provider_dropdown = ft.Dropdown(
        label="AI Provider",
        options=[
            ft.dropdown.Option("ollama"),
            ft.dropdown.Option("openai"),
            ft.dropdown.Option("anthropic"),
            ft.dropdown.Option("openrouter"),
            ft.dropdown.Option("gemini"),
        ],
        value=getattr(get_settings(), "llm_provider", "") or "ollama",
        width=180,
        border_color=MATRIX_GREEN,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70),
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
    )

    ai_progress_ring = ft.ProgressRing(visible=False, width=20, height=20)
    ai_status_text = ft.Text("", color=ft.Colors.WHITE70, size=13)

    ai_output = ft.Markdown(
        value="*Run enrichment first, then click Analyze with AI.*",
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
    )

    ai_btn = ft.ElevatedButton(
        "Analyze with AI",
        icon=ft.Icons.PSYCHOLOGY,
        bgcolor=CYAN,
        color=ft.Colors.BLACK,
    )

    async def _analyze_with_ai(e: ft.ControlEvent):
        if not _enrichment_results:
            _show_snackbar("Run enrichment first before AI analysis", "#ff5555")
            return

        provider_name = provider_dropdown.value or "ollama"

        # Loading state
        ai_btn.disabled = True
        ai_progress_ring.visible = True
        ai_status_text.value = "Analyzing with AI..."
        ai_output.value = "*Analyzing...*"
        page.update()

        try:
            settings = get_settings()
            provider = get_provider(provider_name, settings)

            # Build results table for prompt
            results_lines = ["Source | Finding | Severity", "--- | --- | ---"]
            for r in _enrichment_results:
                results_lines.append(f"{r.source} | {r.summary} | {r.severity.value}")
            results_text = "\n".join(results_lines)

            # Build raw data dict for prompt
            import json

            raw_data: dict = {}
            for r in _enrichment_results:
                if r.raw_data:
                    try:
                        raw_data[r.source] = json.loads(r.raw_data.json())
                    except Exception:
                        raw_data[r.source] = str(r.raw_data)
            raw_data_json = json.dumps(raw_data, indent=2, default=str)

            system_prompt = _build_ai_system_prompt()
            user_prompt = _build_ai_prompt(
                _ioc_value["value"],
                _ioc_type["value"],
                results_text,
                raw_data_json,
            )

            response = await provider.generate(user_prompt, system=system_prompt)
            if response:
                ai_output.value = response
                ai_status_text.value = "AI analysis complete"
                _show_snackbar("AI analysis complete")

                # Persist AI analysis to DB for case history
                _save_ai_analysis_to_db(
                    _ioc_value["value"],
                    _ioc_type["value"],
                    provider.model if hasattr(provider, "model") else provider_name,
                    response,
                )
            else:
                ai_output.value = "*No response from AI provider. Check your configuration.*"
                ai_status_text.value = "No response"
                _show_snackbar("AI provider returned no response", "#ff9800")
        except Exception as exc:
            ai_output.value = f"*Error: {exc}*"
            ai_status_text.value = f"Error: {exc}"
            _show_snackbar(f"AI analysis failed: {exc}", "#ff5555")
        finally:
            ai_btn.disabled = False
            ai_progress_ring.visible = False
            page.update()

    ai_btn.on_click = _analyze_with_ai

    ai_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Divider(color=ft.Colors.WHITE24),
                ft.Text("AI Analysis", size=18, color=CYAN, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[provider_dropdown, ai_btn, ai_progress_ring],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.START,
                ),
                ai_status_text,
                ft.Container(
                    content=ai_output,
                    padding=ft.Padding(top=8, bottom=8),
                ),
            ],
            spacing=8,
        ),
        visible=False,
    )

    # ======================================================================
    # Investigation (Add to Case) Panel
    # ======================================================================

    case_dropdown = ft.Dropdown(
        label="Case",
        options=[],
        width=250,
        border_color=MATRIX_GREEN,
        label_style=ft.TextStyle(color=ft.Colors.WHITE70),
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
    )

    new_case_field = ft.TextField(
        label="New case name",
        hint_text="e.g. Incident-2026-001",
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        label_style=ft.TextStyle(color=ft.Colors.WHITE70),
        expand=True,
    )

    add_case_btn = ft.ElevatedButton(
        "Add to Case",
        icon=ft.Icons.ADD_CIRCLE,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
    )

    def _refresh_cases():
        """Refresh the case dropdown with current cases."""
        try:
            cases = list_cases()
            case_dropdown.options = [ft.dropdown.Option(key=str(c.id), text=c.name) for c in cases]
        except Exception:
            case_dropdown.options = []

    async def _add_to_case(e: ft.ControlEvent):
        if not _enrichment_results:
            _show_snackbar("Run enrichment first before adding to case", "#ff5555")
            return

        new_name = new_case_field.value.strip() if new_case_field.value else ""
        selected = case_dropdown.value

        if not new_name and not selected:
            _show_snackbar("Select a case or enter a new case name", "#ff5555")
            return

        try:
            if new_name:
                # Create new case and add IOC
                new_case = create_case(new_name)
                case_id = new_case.id
            else:
                case_id = int(selected)

            add_ioc_to_case(
                case_id,
                _ioc_value["value"],
                _ioc_type["value"],
            )
            case_name = new_name or f"Case #{case_id}"
            _show_snackbar(f"IOC added to {case_name}")

            # Clear new case field and refresh dropdown
            new_case_field.value = ""
            _refresh_cases()
            page.update()
        except Exception as exc:
            _show_snackbar(f"Failed to add IOC to case: {exc}", "#ff5555")

    add_case_btn.on_click = _add_to_case

    case_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Divider(color=ft.Colors.WHITE24),
                ft.Text("Investigation", size=18, color=CYAN, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[case_dropdown, new_case_field],
                    spacing=12,
                ),
                add_case_btn,
            ],
            spacing=8,
        ),
        visible=False,
    )

    return ft.Column(
        controls=[
            ft.Text(
                "Enrich IOC",
                size=24,
                color=CYAN,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Enter an IP, domain, hash, URL, or email to enrich.",
                color=ft.Colors.WHITE70,
                size=14,
            ),
            ioc_field,
            ft.Row(controls=[enrich_btn, progress_ring], spacing=12),
            status_text,
            results_table,
            ai_panel,
            case_panel,
        ],
        spacing=16,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )


def _build_ai_system_prompt() -> str:
    """Build the system prompt for AI threat intel analysis."""
    return (
        "Sos un analista senior de threat intelligence con experiencia "
        "en respuesta a incidentes. "
        "Tu trabajo es analizar los datos de enrichment de un IOC "
        "— INCLUYENDO los datos crudos de cada fuente — "
        "y producir un reporte ejecutivo en español con "
        "4 secciones OBLIGATORIAS:\n\n"
        "1. **Puntuación de riesgo**: X/10 "
        "(Bajo/Moderado/Alto/Crítico). "
        "CITÁ los datos específicos que justifican el número "
        "(ej: '27/59 detecciones en VirusTotal, "
        "familia TrickBot en MalwareBazaar'). NO inventes.\n"
        "2. **Técnicas MITRE ATT&CK relevantes**: "
        "códigos Txxxx con nombre y descripción. "
        "Solo si hay evidencia clara. Si no hay info suficiente, "
        "decí 'Información insuficiente para MITRE'.\n"
        "3. **Evaluación**: análisis consolidado usando "
        "los datos crudos de cada fuente. "
        "CITÁ campos específicos: signature/familia "
        "(MalwareBazaar), detections/reputation (VirusTotal), "
        "pulse names (OTX), first_seen, tags, etc.\n"
        "4. **Acciones recomendadas**: específicas y técnicas "
        "— incluye comandos de hunting "
        "para EDR/SIEM, queries Splunk/KQL/Sigma, "
        "reglas YARA, IOCs relacionados.\n\n"
        "REGLAS:\n"
        "- NO inventes datos que no estén en el contexto.\n"
        "- Si una fuente no devolvió info, "
        "mencionalo explícitamente ('OTX: sin datos').\n"
        "- Usá formato markdown con headers, "
        "bullets y tablas si aplica.\n"
        "- Sé conciso pero accionable. "
        "Un analista SOC debe poder ejecutar tus recomendaciones."
    )


def _build_ai_prompt(
    ioc_value: str,
    ioc_type: str,
    results_table: str,
    raw_data_json: str = "{}",
) -> str:
    """Build the user prompt for AI analysis.

    Args:
        ioc_value: The IOC value that was enriched.
        ioc_type: The IOC type string.
        results_table: Markdown table of enrichment results.
        raw_data_json: JSON string with raw_data from each plugin.

    Returns:
        The formatted user prompt.
    """
    return (
        f"## IOC a analizar\n\n"
        f"- **Valor**: `{ioc_value}`\n"
        f"- **Tipo**: {ioc_type}\n\n"
        f"## Tabla resumen de Enrichment\n\n"
        f"{results_table}\n\n"
        f"## Datos crudos por fuente (USAR ESTOS DATOS para el análisis)\n\n"
        f"```json\n{raw_data_json}\n```\n\n"
        f"Analizá este IOC basándote en los datos crudos. "
        f"Citá campos específicos en tu justificación. No inventes información."
    )


def _severity_color(severity) -> str:
    """Return a color string for the given severity level."""
    from lupe.models import Severity

    colors = {
        Severity.info: ft.Colors.WHITE54,
        Severity.low: "#4caf50",
        Severity.medium: "#ff9800",
        Severity.high: "#f44336",
        Severity.critical: "#d50000",
    }
    return colors.get(severity, ft.Colors.WHITE)


# Class alias for import compatibility
EnrichView = type("EnrichView", (), {"build": staticmethod(build_enrich_view)})
