"""Main Flet application for Lupe CTI desktop app."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import (
    DARK_BG,
    MATRIX_GREEN,
    SURFACE,
    THEME_MODE,
)
from lupe.flet.views.cases import build_cases_view
from lupe.flet.views.enrich import build_enrich_view
from lupe.flet.views.home import build_home_view
from lupe.flet.views.misp import build_misp_view
from lupe.flet.views.plugins import build_plugins_view
from lupe.flet.views.settings import build_settings_view

_NAV_ITEMS = [
    ("home", "Home", ft.Icons.HOME),
    ("enrich", "Enrich", ft.Icons.SEARCH),
    ("settings", "Settings", ft.Icons.SETTINGS),
    ("misp", "MISP", ft.Icons.SYNC),
    ("plugins", "Plugins", ft.Icons.EXTENSION),
    ("cases", "Cases", ft.Icons.FOLDER_SPECIAL),
]


class LupeFletApp:
    """Lupe CTI — Flet Desktop Application.

    A modern desktop interface for cyber threat intelligence
    investigation and enrichment, built with Flet (Material Design 3).
    """

    @staticmethod
    def main(page: ft.Page) -> None:
        """Main entry point for the Flet application.

        Args:
            page: The Flet page object.
        """
        page.title = "Lupe CTI"
        page.theme_mode = THEME_MODE
        page.theme = ft.Theme(
            color_scheme_seed=MATRIX_GREEN,
            visual_density=ft.VisualDensity.COMPACT,
        )
        page.bgcolor = DARK_BG
        page.padding = 0

        # Window settings (desktop mode)
        if hasattr(page, "window"):
            page.window.width = 1100
            page.window.height = 700
            page.window.min_width = 900
            page.window.min_height = 600

        # Current view name
        current_view = {"name": "home"}

        # Content area
        content_area = ft.Container(expand=True, padding=24)

        def navigate_to(view_name: str) -> None:
            """Switch the displayed view."""
            current_view["name"] = view_name
            content_area.content = _build_view(view_name, page)
            # Update rail selected index
            for i, (name, _, _) in enumerate(_NAV_ITEMS):
                if name == view_name:
                    rail.selected_index = i
                    break
            page.update()

        def _build_view(name: str, pg: ft.Page) -> ft.Control:
            """Build the view control for the given name."""
            builders = {
                "home": lambda: build_home_view(navigate_to),
                "enrich": lambda: build_enrich_view(pg),
                "settings": lambda: build_settings_view(pg),
                "misp": lambda: build_misp_view(pg),
                "plugins": lambda: build_plugins_view(pg),
                "cases": lambda: build_cases_view(pg),
            }
            builder = builders.get(name, builders["home"])
            return builder()

        def on_rail_change(e: ft.ControlEvent) -> None:
            """Handle NavigationRail selection change."""
            idx = e.control.selected_index
            if idx is not None and 0 <= idx < len(_NAV_ITEMS):
                navigate_to(_NAV_ITEMS[idx][0])

        # NavigationRail
        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            bgcolor=SURFACE,
            indicator_color=MATRIX_GREEN,
            selected_label_text_style=ft.TextStyle(color=MATRIX_GREEN),
            unselected_label_text_style=ft.TextStyle(color=ft.Colors.WHITE54),
            leading=ft.Container(
                content=ft.Text(
                    "LUPE",
                    color=MATRIX_GREEN,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                padding=ft.Padding.only(top=16, bottom=8),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=icon,
                    selected_icon=icon,
                    label=label,
                )
                for _, label, icon in _NAV_ITEMS
            ],
            on_change=on_rail_change,
        )

        # Initial view
        content_area.content = _build_view("home", page)

        # Layout: NavigationRail + Content
        page.add(
            ft.Row(
                controls=[
                    rail,
                    ft.VerticalDivider(width=1, color=ft.Colors.WHITE24),
                    content_area,
                ],
                expand=True,
                spacing=0,
            )
        )


def main() -> None:
    """Entry point for the lupe-desktop command."""
    ft.app(target=LupeFletApp.main)


if __name__ == "__main__":
    main()
