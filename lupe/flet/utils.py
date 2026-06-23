"""Flet UI utilities for Lupe CTI."""

from __future__ import annotations

import flet as ft


def show_snackbar(page: ft.Page, message: str, color: str = "#00ff41") -> None:
    """Show a snackbar in Flet 0.85.3+.

    Args:
        page: The Flet page.
        message: The text to display.
        color: The background color (default: matrix green).
    """
    snack = ft.SnackBar(
        content=ft.Text(message, color=ft.Colors.BLACK),
        bgcolor=color,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()
