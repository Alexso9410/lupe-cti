"""Enrich view — IOC enrichment interface (placeholder)."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN, MATRIX_GREEN


def build_enrich_view(page: ft.Page) -> ft.Control:
    """Build the enrich view placeholder.

    Args:
        page: The Flet page (for future use).

    Returns:
        A Flet Column control for the enrich view.
    """
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
            ft.TextField(
                label="IOC Value",
                hint_text="e.g. 8.8.8.8, example.com, d41d8cd98f00b204e9800998ecf8427e",
                border_color=MATRIX_GREEN,
                focused_border_color=CYAN,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
                label_style=ft.TextStyle(color=ft.Colors.WHITE70),
                expand=True,
            ),
            ft.ElevatedButton(
                "Enrich",
                icon=ft.Icons.SEARCH,
                bgcolor=MATRIX_GREEN,
                color=ft.Colors.BLACK,
            ),
            ft.Container(
                content=ft.Text(
                    "Results will appear here.",
                    color=ft.Colors.WHITE38,
                    italic=True,
                ),
                padding=ft.Padding(top=16, bottom=16),
                expand=True,
            ),
        ],
        spacing=16,
        expand=True,
    )


# Class alias for import compatibility
EnrichView = type("EnrichView", (), {"build": staticmethod(build_enrich_view)})
