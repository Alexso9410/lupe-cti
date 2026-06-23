"""Plugins view — list enrichment plugins and their status (placeholder)."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN


def build_plugins_view(page: ft.Page) -> ft.Control:
    """Build the plugins view placeholder.

    Args:
        page: The Flet page (for future use).

    Returns:
        A Flet Column control for the plugins view.
    """
    # Placeholder table rows
    rows = [
        ft.DataRow(
            cells=[
                ft.DataCell(ft.Text("Loading plugins...", color=ft.Colors.WHITE54)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
            ]
        ),
    ]

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Plugin", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Type", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Key Required", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", color=CYAN, weight=ft.FontWeight.BOLD)),
        ],
        rows=rows,
        border=ft.Border.all(1, ft.Colors.WHITE24),
        bgcolor="#141414",
    )

    return ft.Column(
        controls=[
            ft.Text(
                "Plugins",
                size=24,
                color=CYAN,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Enrichment plugin status and configuration.",
                color=ft.Colors.WHITE70,
                size=14,
            ),
            ft.Container(
                content=table,
                padding=ft.Padding(top=12, bottom=12),
                expand=True,
            ),
        ],
        spacing=8,
        expand=True,
    )


# Class alias for import compatibility
PluginsView = type("PluginsView", (), {"build": staticmethod(build_plugins_view)})
