"""Plugins view — list enrichment plugins and their status."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN, MATRIX_GREEN


def _discover_plugins() -> list[dict]:
    """Discover all available enrichment plugins."""
    from lupe.enrichment.base import EnrichmentPlugin

    plugins: list[dict] = []
    for cls in EnrichmentPlugin.__subclasses__():
        plugins.append({
            "name": cls.name,
            "types": ", ".join(sorted(t.value for t in cls.supported_ioc_types)),
            "requires_key": "Yes" if cls.requires_api_key else "No",
        })
    plugins.sort(key=lambda p: p["name"])
    return plugins


def build_plugins_view(page: ft.Page) -> ft.Control:
    """Build the plugins view listing all enrichment plugins.

    Args:
        page: The Flet page.

    Returns:
        A Flet Column control for the plugins view.
    """
    discovered = _discover_plugins()

    if not discovered:
        rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text("No plugins discovered", color=ft.Colors.WHITE54)),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                ]
            ),
        ]
    else:
        rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(p["name"], color=ft.Colors.WHITE)),
                    ft.DataCell(ft.Text(p["types"], color=ft.Colors.WHITE70)),
                    ft.DataCell(
                        ft.Text(
                            p["requires_key"],
                            color=MATRIX_GREEN if p["requires_key"] == "No" else CYAN,
                        )
                    ),
                    ft.DataCell(
                        ft.Text(
                            "Available" if p["requires_key"] == "No" else "Needs API Key",
                            color=MATRIX_GREEN if p["requires_key"] == "No" else ft.Colors.WHITE54,
                        )
                    ),
                ]
            )
            for p in discovered
        ]

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Plugin", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("IOC Types", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Key Required", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", color=CYAN, weight=ft.FontWeight.BOLD)),
        ],
        rows=rows,
        border=ft.Border.all(1, ft.Colors.WHITE24),
        bgcolor="#141414",
    )

    return ft.Column(
        controls=[
            ft.Text("Plugins", size=24, color=CYAN, weight=ft.FontWeight.BOLD),
            ft.Text(
                f"{len(discovered)} enrichment plugins discovered.",
                color=ft.Colors.WHITE70,
                size=14,
            ),
            ft.Container(
                content=ft.Column(
                    controls=[table],
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=ft.Padding(top=12, bottom=12),
                expand=True,
            ),
        ],
        spacing=8,
        expand=True,
    )


# Class alias for import compatibility
PluginsView = type("PluginsView", (), {"build": staticmethod(build_plugins_view)})
