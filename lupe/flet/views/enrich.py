"""Enrich view — IOC enrichment interface connected to run_enrichment."""

from __future__ import annotations

import flet as ft

from lupe.config import get_settings
from lupe.enrichment import run_enrichment
from lupe.flet.theme import CYAN, MATRIX_GREEN
from lupe.ioc_detect import detect_ioc


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

    # --- Button ---
    enrich_btn = ft.ElevatedButton(
        "Enrich",
        icon=ft.Icons.SEARCH,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
    )

    def _show_snackbar(msg: str, color: str = MATRIX_GREEN):
        page.show_snack_bar(ft.SnackBar(ft.Text(msg), bgcolor=color))
        page.update()

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
        except Exception as exc:
            status_text.value = f"Error: {exc}"
            _show_snackbar(f"Enrichment failed: {exc}", "#ff5555")
        finally:
            enrich_btn.disabled = False
            progress_ring.visible = False
            page.update()

    enrich_btn.on_click = _enrich

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
        ],
        spacing=16,
        expand=True,
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
