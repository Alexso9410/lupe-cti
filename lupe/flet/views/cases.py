"""Cases view — investigation case management (placeholder)."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN, MATRIX_GREEN


def build_cases_view() -> ft.Control:
    """Build the cases view placeholder.

    Returns:
        A Flet Column control for the cases view.
    """
    rows = [
        ft.DataRow(
            cells=[
                ft.DataCell(ft.Text("---", color=ft.Colors.WHITE54)),
                ft.DataCell(ft.Text("No cases loaded", color=ft.Colors.WHITE54)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
            ]
        ),
    ]

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Name", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("IOCs", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Created", color=CYAN, weight=ft.FontWeight.BOLD)),
        ],
        rows=rows,
        border=ft.border.all(1, ft.Colors.WHITE24),
        bgcolor="#141414",
    )

    return ft.Column(
        controls=[
            ft.Text(
                "Cases",
                size=24,
                color=CYAN,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Investigation case management.",
                color=ft.Colors.WHITE70,
                size=14,
            ),
            ft.Row(
                controls=[
                    ft.TextField(
                        label="New case name",
                        hint_text="e.g. Incident-2026-001",
                        border_color=MATRIX_GREEN,
                        text_style=ft.TextStyle(color=ft.Colors.WHITE),
                        expand=True,
                    ),
                    ft.ElevatedButton(
                        "Create Case",
                        icon=ft.Icons.ADD,
                        bgcolor=MATRIX_GREEN,
                        color=ft.Colors.BLACK,
                    ),
                ],
                spacing=12,
            ),
            ft.Container(
                content=table,
                padding=ft.padding.only(top=12),
                expand=True,
            ),
        ],
        spacing=12,
        expand=True,
    )


# Class alias for import compatibility
CasesView = type("CasesView", (), {"build": staticmethod(build_cases_view)})
