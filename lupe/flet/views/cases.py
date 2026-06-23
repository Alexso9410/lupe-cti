"""Cases view — investigation case management with Edit/Delete actions (PR-31)."""

from __future__ import annotations

from datetime import datetime

import flet as ft

from lupe.case import CaseInfo, create_case, delete_case, list_cases, update_case
from lupe.flet.theme import CYAN, ERROR_RED, MATRIX_GREEN
from lupe.flet.utils import show_snackbar


def build_cases_view(page: ft.Page) -> ft.Control:
    """Build the cases view with full CRUD including Edit/Delete.

    Args:
        page: The Flet page.

    Returns:
        A Flet Column control for the cases view.
    """
    # --- State ---
    cases_state: dict = {"items": []}

    # --- Table ---
    def _build_table_rows() -> list[ft.DataRow]:
        items: list[CaseInfo] = cases_state["items"]
        if not items:
            return [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text("—", color=ft.Colors.WHITE54)),
                        ft.DataCell(
                            ft.Text(
                                "No cases loaded — create one above",
                                color=ft.Colors.WHITE54,
                            )
                        ),
                        ft.DataCell(ft.Text("—")),
                        ft.DataCell(ft.Text("—")),
                        ft.DataCell(ft.Text("—")),
                        ft.DataCell(ft.Text("—")),
                    ]
                )
            ]
        rows: list[ft.DataRow] = []
        for c in items:
            created = c.created_at
            if isinstance(created, datetime):
                created_str = created.strftime("%Y-%m-%d %H:%M")
            else:
                created_str = str(created)
            case_id_str = str(c.id) if c.id is not None else "—"
            case_id_short = case_id_str[:8] if len(case_id_str) >= 8 else case_id_str

            # Action buttons for this row
            def _make_edit_handler(cid: int, cname: str):
                def _handler(e: ft.ControlEvent):
                    _show_edit_dialog(cid, cname)

                return _handler

            def _make_delete_handler(cid: int, cname: str):
                def _handler(e: ft.ControlEvent):
                    _show_delete_dialog(cid, cname)

                return _handler

            edit_btn = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_color=CYAN,
                icon_size=18,
                tooltip="Edit case",
                on_click=_make_edit_handler(c.id, c.name),
            )
            delete_btn = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color=ERROR_RED,
                icon_size=18,
                tooltip="Delete case",
                on_click=_make_delete_handler(c.id, c.name),
            )
            actions_row = ft.Row(controls=[edit_btn, delete_btn], spacing=0, tight=True)

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(case_id_short, color=CYAN)),
                        ft.DataCell(ft.Text(c.name, color=ft.Colors.WHITE)),
                        ft.DataCell(ft.Text(c.status, color=MATRIX_GREEN)),
                        ft.DataCell(ft.Text(str(getattr(c, "ioc_count", 0)))),
                        ft.DataCell(ft.Text(created_str, color=ft.Colors.WHITE70)),
                        ft.DataCell(actions_row),
                    ]
                )
            )
        return rows

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Name", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Status", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("IOCs", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Created", color=CYAN, weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Actions", color=CYAN, weight=ft.FontWeight.BOLD)),
        ],
        rows=_build_table_rows(),
        border=ft.Border.all(1, ft.Colors.WHITE24),
        bgcolor="#141414",
    )

    def _refresh() -> None:
        try:
            items = list_cases()
            cases_state["items"] = items
            table.rows = _build_table_rows()
            page.update()
        except Exception as exc:
            show_snackbar(page, f"Failed to load cases: {exc}", "#ff5555")

    # --- Edit dialog ---
    def _show_edit_dialog(case_id: int, current_name: str) -> None:
        edit_field = ft.TextField(
            label="Case name",
            value=current_name,
            border_color=CYAN,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            bgcolor="#1a1a1a",
        )

        async def _save_edit(e: ft.ControlEvent) -> None:
            new_name = (edit_field.value or "").strip()
            if not new_name:
                show_snackbar(page, "Name cannot be empty", "#ff5555")
                return
            try:
                success = update_case(case_id, name=new_name)
                if success:
                    show_snackbar(page, "Case updated")
                    page.pop_dialog()
                    _refresh()
                else:
                    show_snackbar(page, "Case not found", "#ff5555")
            except Exception as exc:
                show_snackbar(page, f"Failed to update case: {exc}", "#ff5555")

        dialog = ft.AlertDialog(
            title=ft.Text("Edit Case", color=CYAN),
            content=ft.Container(
                content=edit_field,
                width=400,
                padding=ft.Padding.all(16),
                bgcolor="#1a1a1a",
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.ElevatedButton(
                    "Save",
                    bgcolor=MATRIX_GREEN,
                    color=ft.Colors.BLACK,
                    on_click=lambda e: page.run_task(_save_edit, e),
                ),
            ],
            bgcolor="#1a1a1a",
        )
        page.show_dialog(dialog)

    # --- Delete confirmation dialog ---
    def _show_delete_dialog(case_id: int, case_name: str) -> None:
        async def _confirm_delete(e: ft.ControlEvent) -> None:
            try:
                success = delete_case(case_id)
                if success:
                    show_snackbar(page, "Case deleted")
                    page.pop_dialog()
                    _refresh()
                else:
                    show_snackbar(page, "Case not found", "#ff5555")
            except Exception as exc:
                show_snackbar(page, f"Failed to delete case: {exc}", "#ff5555")

        dialog = ft.AlertDialog(
            title=ft.Text("Delete Case", color=ERROR_RED),
            content=ft.Text(
                f"Are you sure you want to delete '{case_name}'?\nThis action cannot be undone.",
                color=ft.Colors.WHITE70,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.ElevatedButton(
                    "Delete",
                    bgcolor=ERROR_RED,
                    color=ft.Colors.WHITE,
                    on_click=lambda e: page.run_task(_confirm_delete, e),
                ),
            ],
            bgcolor="#1a1a1a",
        )
        page.show_dialog(dialog)

    # --- Input + buttons ---
    new_case_field = ft.TextField(
        label="New case name",
        hint_text="e.g. Incident-2026-001",
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        expand=True,
    )

    async def _create_case(e: ft.ControlEvent) -> None:
        name = new_case_field.value or ""
        name = name.strip()
        if not name:
            show_snackbar(page, "Enter a case name first", "#ff5555")
            return
        try:
            new_case = create_case(name=name)
            case_id_short = str(new_case.id)[:8] if new_case.id is not None else "—"
            show_snackbar(page, f"Case created: {new_case.name} ({case_id_short})")
            new_case_field.value = ""
            _refresh()
        except Exception as exc:
            show_snackbar(page, f"Failed to create case: {exc}", "#ff5555")

    create_btn = ft.ElevatedButton(
        "Create Case",
        icon=ft.Icons.ADD,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
        on_click=lambda e: page.run_task(_create_case, e),
    )

    refresh_btn = ft.ElevatedButton(
        "Refresh",
        icon=ft.Icons.REFRESH,
        bgcolor=ft.Colors.WHITE24,
        color=ft.Colors.WHITE,
        on_click=lambda _: _refresh(),
    )

    # Initial load (without throwing if DB unavailable)
    try:
        cases_state["items"] = list_cases()
        table.rows = _build_table_rows()
    except Exception:
        pass

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
                controls=[new_case_field, create_btn, refresh_btn],
                spacing=12,
            ),
            ft.Container(
                content=table,
                padding=ft.Padding(top=12, bottom=12),
                expand=True,
            ),
        ],
        spacing=12,
        expand=True,
    )


# Class alias for import compatibility
CasesView = type("CasesView", (), {"build": staticmethod(build_cases_view)})
