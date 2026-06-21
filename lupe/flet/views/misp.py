"""MISP view — pull/push indicators (placeholder)."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN, MATRIX_GREEN


def build_misp_view(page: ft.Page) -> ft.Control:
    """Build the MISP view placeholder.

    Args:
        page: The Flet page (for future use).

    Returns:
        A Flet Column control for the MISP view.
    """
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
            ft.TextField(
                label="Tag filter",
                hint_text="e.g. osint",
                border_color=MATRIX_GREEN,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
            ),
            ft.TextField(
                label="Days to look back",
                hint_text="7",
                border_color=MATRIX_GREEN,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
            ),
            ft.ElevatedButton(
                "Pull Indicators",
                icon=ft.Icons.CLOUD_DOWNLOAD,
                bgcolor=MATRIX_GREEN,
                color=ft.Colors.BLACK,
            ),
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Text("Push to MISP", size=16, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
            ft.TextField(
                label="IOC value to push",
                hint_text="e.g. 8.8.8.8",
                border_color=MATRIX_GREEN,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
            ),
            ft.ElevatedButton(
                "Push IOC",
                icon=ft.Icons.CLOUD_UPLOAD,
                bgcolor=CYAN,
                color=ft.Colors.BLACK,
            ),
        ],
        spacing=12,
        expand=True,
    )


# Class alias for import compatibility
MISPView = type("MISPView", (), {"build": staticmethod(build_misp_view)})
