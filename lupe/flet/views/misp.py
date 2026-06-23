"""MISP view — pull/push indicators connected to MISPClient."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN, MATRIX_GREEN
from lupe.flet.utils import show_snackbar
from lupe.flet.views.settings import load_settings
from lupe.integrations.misp import MISPClient


def build_misp_view(page: ft.Page) -> ft.Control:
    """Build the MISP view with pull/push functionality.

    Args:
        page: The Flet page (for snack_bar and run_task).

    Returns:
        A Flet Column control for the MISP view.
    """
    # --- Input fields ---
    tag_field = ft.TextField(
        label="Tag filter",
        hint_text="e.g. osint",
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
    )
    days_field = ft.TextField(
        label="Days to look back",
        hint_text="7",
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
    )
    ioc_field = ft.TextField(
        label="IOC value to push",
        hint_text="e.g. 8.8.8.8",
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
    )

    # --- Results area ---
    results_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Type", color=CYAN)),
            ft.DataColumn(ft.Text("Value", color=CYAN)),
            ft.DataColumn(ft.Text("Tags", color=CYAN)),
            ft.DataColumn(ft.Text("First Seen", color=CYAN)),
        ],
        rows=[],
        visible=False,
    )
    progress_ring = ft.ProgressRing(visible=False, width=20, height=20)

    # --- Buttons ---
    pull_btn = ft.ElevatedButton(
        "Pull Indicators",
        icon=ft.Icons.CLOUD_DOWNLOAD,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
    )
    push_btn = ft.ElevatedButton(
        "Push IOC",
        icon=ft.Icons.CLOUD_UPLOAD,
        bgcolor=CYAN,
        color=ft.Colors.BLACK,
    )

    def _show_snackbar(msg: str, color: str = MATRIX_GREEN) -> None:
        show_snackbar(page, msg, color)
        page.update()

    def _check_misp_config() -> dict | None:
        settings = load_settings()
        misp_url = settings.get("misp_url", "")
        misp_key = settings.get("misp_key", "")
        if not misp_url or not misp_key:
            _show_snackbar("MISP not configured — set MISP URL and API Key in Settings", "#ff5555")
            return None
        return settings

    async def _pull_indicators(e: ft.ControlEvent) -> None:
        settings = _check_misp_config()
        if settings is None:
            return

        # Loading state
        pull_btn.disabled = True
        progress_ring.visible = True
        page.update()

        try:
            tag = tag_field.value.strip() if tag_field.value else None
            days = int(days_field.value) if days_field.value and days_field.value.strip() else 7

            async with MISPClient(settings["misp_url"], settings["misp_key"]) as client:
                indicators = await client.get_indicators(tags=[tag] if tag else None, days=days)

            # Populate results table
            results_table.rows.clear()
            for ind in indicators:
                results_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(ind.get("type", ""), color=ft.Colors.WHITE)),
                            ft.DataCell(ft.Text(ind.get("value", ""), color=ft.Colors.WHITE)),
                            ft.DataCell(ft.Text(str(ind.get("tags", "")), color=ft.Colors.WHITE)),
                            ft.DataCell(ft.Text(ind.get("timestamp", ""), color=ft.Colors.WHITE)),
                        ]
                    )
                )
            results_table.visible = True
            _show_snackbar(f"Pulled {len(indicators)} indicators from MISP")
        except Exception as exc:
            _show_snackbar(f"Pull failed: {exc}", "#ff5555")
        finally:
            pull_btn.disabled = False
            progress_ring.visible = False
            page.update()

    async def _push_ioc(e: ft.ControlEvent) -> None:
        settings = _check_misp_config()
        if settings is None:
            return

        ioc_value = ioc_field.value.strip() if ioc_field.value else ""
        if not ioc_value:
            _show_snackbar("Enter an IOC value to push", "#ff5555")
            return

        # Loading state
        push_btn.disabled = True
        progress_ring.visible = True
        page.update()

        try:
            async with MISPClient(settings["misp_url"], settings["misp_key"]) as client:
                uuid = await client.add_indicator(
                    indicator={
                        "type": "ip-dst",
                        "value": ioc_value,
                        "category": "Network activity",
                    },
                    tags=["lupe-cti"],
                )
            _show_snackbar(f"IOC pushed to MISP — UUID: {uuid}")
        except Exception as exc:
            _show_snackbar(f"Push failed: {exc}", "#ff5555")
        finally:
            push_btn.disabled = False
            progress_ring.visible = False
            page.update()

    pull_btn.on_click = _pull_indicators
    push_btn.on_click = _push_ioc

    return ft.Column(
        controls=[
            ft.Text(
                "MISP Integration",
                size=24,
                color=CYAN,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Pull and push indicators to/from MISP instances.",
                color=ft.Colors.WHITE70,
                size=14,
            ),
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Text("Pull Indicators", size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
            tag_field,
            days_field,
            ft.Row(controls=[pull_btn, progress_ring], spacing=12),
            results_table,
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Text("Push to MISP", size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
            ioc_field,
            ft.Row(
                controls=[push_btn, ft.ProgressRing(visible=False, width=20, height=20)],
                spacing=12,
            ),
        ],
        spacing=12,
        expand=True,
    )


# Class alias for import compatibility
MISPView = type("MISPView", (), {"build": staticmethod(build_misp_view)})
