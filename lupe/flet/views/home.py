"""Home view — landing page with LUPE banner and navigation cards."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN, MATRIX_GREEN

LUPE_BANNER = r"""
 ██╗     ██╗   ██╗██████╗ ███████╗
 ██║     ██║   ██║██╔══██╗██╔════╝
 ██║     ██║   ██║██████╔╝█████╗
 ██║     ██║   ██║██╔═══╝ ██╔══╝
 ███████╗╚██████╔╝██║     ███████╗
 ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝
             L U P E
"""

_SUBTITLE = "Cyber Threat Intelligence for OSINT, Forensics & Incident Response"

_NAV_ITEMS = [
    ("Enrich", ft.Icons.SEARCH, "enrich"),
    ("Settings", ft.Icons.SETTINGS, "settings"),
    ("MISP", ft.Icons.SYNC, "misp"),
    ("Plugins", ft.Icons.EXTENSION, "plugins"),
    ("Cases", ft.Icons.FOLDER_SPECIAL, "cases"),
]


def build_home_view(on_navigate: object) -> ft.Control:
    """Build the home view with banner and navigation cards.

    Args:
        on_navigate: Callable[[str], None] — receives view name to navigate to.

    Returns:
        A Flet Column control containing the home view.
    """
    banner_text = ft.Text(
        LUPE_BANNER,
        color=MATRIX_GREEN,
        size=14,
        font_family="monospace",
        text_align=ft.TextAlign.CENTER,
        selectable=False,
    )

    subtitle_text = ft.Text(
        _SUBTITLE,
        color=CYAN,
        size=16,
        text_align=ft.TextAlign.CENTER,
        weight=ft.FontWeight.W_300,
    )

    nav_cards = []
    for label, icon, view_name in _NAV_ITEMS:
        card = ft.Card(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, color=MATRIX_GREEN, size=28),
                        ft.Text(label, size=16, color=ft.Colors.WHITE),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                ),
                padding=ft.Padding.symmetric(horizontal=24, vertical=16),
                on_click=lambda e, vn=view_name: on_navigate(vn),
                ink=True,
            ),
            bgcolor="#1a1a1a",
            elevation=2,
        )
        nav_cards.append(card)

    return ft.Column(
        controls=[
            ft.Container(content=banner_text, alignment=ft.alignment.Alignment.CENTER),
            ft.Container(
                content=subtitle_text,
                alignment=ft.alignment.Alignment.CENTER,
                padding=ft.Padding.only(bottom=24),
            ),
            ft.Container(
                content=ft.GridView(
                    controls=nav_cards,
                    runs_count=3,
                    max_extent=280,
                    spacing=12,
                    run_spacing=12,
                    child_aspect_ratio=3.0,
                ),
                padding=ft.Padding.symmetric(horizontal=40),
                expand=True,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
        expand=True,
    )


# Class alias for import compatibility
HomeView = type("HomeView", (), {"build": staticmethod(build_home_view)})
