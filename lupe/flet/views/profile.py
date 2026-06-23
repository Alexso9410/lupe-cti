"""Profile view — multi-user profile management (PR-32)."""

from __future__ import annotations

import flet as ft

from lupe.flet.theme import CYAN, ERROR_RED, MATRIX_GREEN
from lupe.flet.utils import show_snackbar
from lupe.profile import (
    create_profile,
    delete_profile,
    get_active_profile,
    list_profiles,
    set_active_profile,
)


def build_profile_view(page: ft.Page) -> ft.Control:
    """Build the profile management view.

    Args:
        page: The Flet page.

    Returns:
        A Flet Column control for the profile view.
    """
    # --- State ---
    profiles_state: dict = {"active": "default", "all": []}

    def _refresh() -> None:
        profiles_state["active"] = get_active_profile()
        profiles_state["all"] = list_profiles()
        _update_dropdown()
        page.update()

    def _update_dropdown() -> None:
        profiles = profiles_state["all"]
        active = profiles_state["active"]
        profile_dropdown.options = [
            ft.dropdown.Option(key=p, text=f"{p} {'(active)' if p == active else ''}")
            for p in profiles
        ]
        profile_dropdown.value = (
            active if active in profiles else (profiles[0] if profiles else None)
        )
        active_label.value = f"Active profile: {active}"

    # --- Active profile label ---
    active_label = ft.Text(
        f"Active profile: {profiles_state['active']}",
        color=MATRIX_GREEN,
        size=16,
        weight=ft.FontWeight.BOLD,
    )

    # --- Profile dropdown ---
    profile_dropdown = ft.Dropdown(
        label="Select profile",
        border_color=CYAN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        bgcolor="#1a1a1a",
        width=300,
        options=[],
    )

    # --- Switch profile ---
    async def _switch_profile(e: ft.ControlEvent) -> None:
        selected = profile_dropdown.value
        if not selected:
            show_snackbar(page, "Select a profile first", "#ff5555")
            return
        if selected == profiles_state["active"]:
            show_snackbar(page, f"'{selected}' is already active", "#ff5555")
            return
        try:
            set_active_profile(selected)
            show_snackbar(
                page,
                f"Switched to '{selected}'. Restart the app for changes to take effect.",
            )
            _refresh()
        except Exception as exc:
            show_snackbar(page, f"Failed to switch profile: {exc}", "#ff5555")

    switch_btn = ft.FilledButton(
        "Switch",
        icon=ft.Icons.SWAP_HORIZ,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
        on_click=lambda e: page.run_task(_switch_profile, e),
    )

    # --- Create new profile ---
    new_profile_field = ft.TextField(
        label="New profile name",
        hint_text="e.g. analyst1",
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        width=250,
    )

    async def _create_profile(e: ft.ControlEvent) -> None:
        name = (new_profile_field.value or "").strip()
        if not name:
            show_snackbar(page, "Enter a profile name", "#ff5555")
            return
        try:
            create_profile(name)
            show_snackbar(page, f"Profile '{name}' created")
            new_profile_field.value = ""
            _refresh()
        except ValueError as exc:
            show_snackbar(page, str(exc), "#ff5555")
        except Exception as exc:
            show_snackbar(page, f"Failed to create profile: {exc}", "#ff5555")

    create_btn = ft.FilledButton(
        "Create",
        icon=ft.Icons.ADD,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
        on_click=lambda e: page.run_task(_create_profile, e),
    )

    # --- Delete profile ---
    async def _confirm_delete(e: ft.ControlEvent) -> None:
        name = profile_dropdown.value
        if not name:
            show_snackbar(page, "Select a profile to delete", "#ff5555")
            return
        if name == "default":
            show_snackbar(page, "Cannot delete the 'default' profile", "#ff5555")
            return

        async def _do_delete(ev: ft.ControlEvent) -> None:
            try:
                delete_profile(name)
                show_snackbar(page, f"Profile '{name}' deleted")
                page.pop_dialog()
                _refresh()
            except Exception as exc:
                show_snackbar(page, f"Failed to delete: {exc}", "#ff5555")

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Profile", color=ERROR_RED),
            content=ft.Text(
                f"Delete profile '{name}' and all its data?\nThis cannot be undone.",
                color=ft.Colors.WHITE70,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Delete",
                    bgcolor=ERROR_RED,
                    color=ft.Colors.WHITE,
                    on_click=lambda ev: page.run_task(_do_delete, ev),
                ),
            ],
            bgcolor="#1a1a1a",
        )
        page.show_dialog(dialog)

    delete_btn = ft.FilledButton(
        "Delete",
        icon=ft.Icons.DELETE,
        bgcolor=ERROR_RED,
        color=ft.Colors.WHITE,
        on_click=lambda e: page.run_task(_confirm_delete, e),
    )

    # --- Initial load ---
    try:
        _refresh()
    except Exception:
        pass

    return ft.Column(
        controls=[
            ft.Text(
                "Profiles",
                size=24,
                color=CYAN,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Manage user profiles for separate data storage.",
                color=ft.Colors.WHITE70,
                size=14,
            ),
            ft.Divider(color=ft.Colors.WHITE24),
            active_label,
            ft.Row(
                controls=[profile_dropdown, switch_btn],
                spacing=12,
            ),
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Text("Create new profile", color=CYAN, size=14, weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[new_profile_field, create_btn],
                spacing=12,
            ),
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Text("Delete profile", color=ERROR_RED, size=14, weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[delete_btn],
                spacing=12,
            ),
        ],
        spacing=12,
        expand=True,
    )


# Class alias for import compatibility
ProfileView = type("ProfileView", (), {"build": staticmethod(build_profile_view)})
