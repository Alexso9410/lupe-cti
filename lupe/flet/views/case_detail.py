"""Case detail view — timeline display with export buttons (PR #3)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import flet as ft

from lupe.case import CaseHistory, build_case_history
from lupe.flet.theme import CYAN, ERROR_RED, MATRIX_GREEN
from lupe.flet.utils import show_snackbar


def format_event_for_display(event: dict[str, Any]) -> dict[str, Any]:
    """Format a raw timeline event for display in the Flet detail view.

    Args:
        event: Raw event dict from get_case_timeline().

    Returns:
        Dict with normalized keys: type, icon, source, severity, model,
        summary, timestamp, detail.
    """
    ev_type = event.get("event_type", "unknown")
    result: dict[str, Any] = {
        "type": ev_type,
        "icon": ev_type,
        "timestamp": event.get("timestamp", ""),
        "summary": "",
        "detail": event.get("detail", ""),
        "source": "",
        "severity": "",
        "model": "",
    }

    if ev_type == "enrichment":
        result["source"] = event.get("source", "")
        result["severity"] = event.get("detail", event.get("severity", ""))
        result["summary"] = event.get("summary", event.get("description", ""))

    elif ev_type == "analysis":
        result["model"] = event.get("model", "")
        result["summary"] = event.get("summary", "")
        result["source"] = event.get("model", "")

    elif ev_type == "ioc_added":
        desc = event.get("description", "")
        result["summary"] = desc

    elif ev_type == "note":
        result["summary"] = event.get("description", "")

    else:
        result["summary"] = event.get("description", "")

    return result


def build_case_detail_data(case_id: int) -> dict[str, Any] | None:
    """Build formatted data for the case detail view.

    Args:
        case_id: The case to build detail data for.

    Returns:
        Dict with 'case', 'iocs', 'case_notes', 'stats' keys, where each
        IOC group has formatted events, or None if case not found.
    """
    history: CaseHistory = build_case_history(case_id)

    if not history.get("case"):
        return None

    # Format events in each IOC group
    formatted_iocs: list[dict[str, Any]] = []
    for ioc_group in history.get("iocs", []):
        formatted_events = [
            format_event_for_display(e) for e in ioc_group.get("events", [])
        ]
        formatted_iocs.append({
            "ioc": ioc_group["ioc"],
            "events": formatted_events,
        })

    return {
        "case": history["case"],
        "iocs": formatted_iocs,
        "case_notes": history.get("case_notes", []),
        "stats": history.get("stats", {}),
    }


def _resolve_export_path(base_name: str, ext: str, default: str = "case") -> Path:
    """Resolve a default export path in the user's Downloads folder.

    Args:
        base_name: Case name or IOC value for filename sanitization.
        ext: File extension (e.g. '.txt', '.docx').
        default: Fallback name when base_name produces empty string.

    Returns:
        Path to the export file.
    """
    safe_name = "".join(
        c if c.isalnum() or c in "-_ ." else "_" for c in base_name
    )
    safe_name = safe_name.strip() or default
    filename = f"{safe_name}_report{ext}"

    # Try Downloads folder, fall back to temp
    try:
        downloads = Path.home() / "Downloads"
    except RuntimeError:
        downloads = Path.cwd()
    if not downloads.exists():
        downloads = Path.cwd()
    return downloads / filename


def export_case_txt_to_file(case_id: int) -> Path | None:
    """Export a case to TXT and save to file.

    Args:
        case_id: The case to export.

    Returns:
        Path to the saved file, or None if case not found.
    """
    from lupe.export.txt_export import export_case_to_txt

    history = build_case_history(case_id)
    if not history.get("case"):
        return None

    txt_content = export_case_to_txt(history)
    out_path = _resolve_export_path(history["case"].get("name", "case"), ".txt")
    out_path.write_text(txt_content, encoding="utf-8")
    return out_path


def export_case_docx_to_file(case_id: int) -> Path | None:
    """Export a case to DOCX and save to file.

    Args:
        case_id: The case to export.

    Returns:
        Path to the saved file, or None if case not found.
    """
    from lupe.export.docx_export import export_case_to_docx

    history = build_case_history(case_id)
    if not history.get("case"):
        return None

    out_path = _resolve_export_path(history["case"].get("name", "case"), ".docx")
    export_case_to_docx(history, out_path)
    return out_path


def export_ioc_txt_to_file(case_id: int, ioc_value: str) -> Path | None:
    """Export a single IOC to TXT and save to file.

    Args:
        case_id: The case containing the IOC.
        ioc_value: The IOC value to export.

    Returns:
        Path to the saved file, or None if not found.
    """
    from lupe.export.txt_export import export_ioc_to_txt

    history = build_case_history(case_id)
    if not history.get("case"):
        return None

    ioc_group = None
    for g in history.get("iocs", []):
        if g["ioc"]["value"] == ioc_value:
            ioc_group = g
            break

    if ioc_group is None:
        return None

    txt_content = export_ioc_to_txt(ioc_group, history["case"])
    out_path = _resolve_export_path(ioc_value, ".txt", default="ioc")
    out_path.write_text(txt_content, encoding="utf-8")
    return out_path


def export_ioc_docx_to_file(case_id: int, ioc_value: str) -> Path | None:
    """Export a single IOC to DOCX and save to file.

    Args:
        case_id: The case containing the IOC.
        ioc_value: The IOC value to export.

    Returns:
        Path to the saved file, or None if not found.
    """
    from lupe.export.docx_export import export_ioc_to_docx

    history = build_case_history(case_id)
    if not history.get("case"):
        return None

    ioc_group = None
    for g in history.get("iocs", []):
        if g["ioc"]["value"] == ioc_value:
            ioc_group = g
            break

    if ioc_group is None:
        return None

    out_path = _resolve_export_path(ioc_value, ".docx", default="ioc")
    export_ioc_to_docx(ioc_group, history["case"], out_path)
    return out_path


# ---------------------------------------------------------------------------
# Severity color mapping
# ---------------------------------------------------------------------------

_SEVERITY_COLORS: dict[str, str] = {
    "critical": "#ff0000",
    "high": "#ff5555",
    "medium": "#ffaa00",
    "low": "#00cc66",
    "info": "#00aaff",
}

_EVENT_ICONS: dict[str, str] = {
    "enrichment": ft.Icons.INSIGHTS,
    "analysis": ft.Icons.SMART_TOY,
    "ioc_added": ft.Icons.ADD_CIRCLE,
    "note": ft.Icons.NOTE,
}


# ---------------------------------------------------------------------------
# Flet view builder
# ---------------------------------------------------------------------------


def build_case_detail_view(
    detail_data: dict[str, Any],
    on_back: Callable[[], None],
    page: ft.Page | None = None,
) -> ft.Column:
    """Build the case detail view with timeline and export buttons.

    Args:
        detail_data: Dict from build_case_detail_data() with case, iocs,
            case_notes, and stats.
        on_back: Callback to return to the case list view.
        page: Optional Flet page for snackbar notifications.

    Returns:
        A Flet Column control for the case detail view.
    """
    case_info = detail_data.get("case", {})
    iocs = detail_data.get("iocs", [])
    notes = detail_data.get("case_notes", [])
    stats = detail_data.get("stats", {})

    # --- Header ---
    case_name = case_info.get("name", "Unknown Case")
    case_desc = case_info.get("description", "")
    case_status = case_info.get("status", "open")
    case_created = case_info.get("created_at", "N/A")

    header = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    icon_color=CYAN,
                    tooltip="Back to cases",
                    on_click=lambda _: on_back(),
                ),
                ft.Text(case_name, size=22, color=CYAN, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text(case_status, color=MATRIX_GREEN, size=13),
                    bgcolor="#1a3a1a",
                    border_radius=4,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                ),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(case_desc, color=ft.Colors.WHITE70, size=14) if case_desc else ft.Container(),
            ft.Row([
                ft.Text(f"Created: {case_created}", color=ft.Colors.WHITE54, size=12),
                ft.Text(f"IOCs: {stats.get('ioc_count', 0)}", color=CYAN, size=12),
                ft.Text(
                    f"Enrichments: {stats.get('enrichment_count', 0)}",
                    color=ft.Colors.WHITE54, size=12,
                ),
                ft.Text(
                    f"Analyses: {stats.get('analysis_count', 0)}",
                    color=ft.Colors.WHITE54, size=12,
                ),
            ], spacing=16),
        ], spacing=6),
        padding=ft.Padding.only(bottom=12),
    )

    # --- Export buttons ---
    def _export_txt(e: ft.ControlEvent) -> None:
        try:
            case_id = case_info.get("id")
            if case_id is None:
                if page:
                    show_snackbar(page, "Export failed — missing case ID", ERROR_RED)
                return
            result = export_case_txt_to_file(case_id)
            if result and page:
                show_snackbar(page, f"Exported: {result}")
            elif page:
                show_snackbar(page, "Export failed — case not found", ERROR_RED)
        except Exception as exc:
            if page:
                show_snackbar(page, f"Export error: {exc}", ERROR_RED)

    def _export_docx(e: ft.ControlEvent) -> None:
        try:
            case_id = case_info.get("id")
            if case_id is None:
                if page:
                    show_snackbar(page, "Export failed — missing case ID", ERROR_RED)
                return
            result = export_case_docx_to_file(case_id)
            if result and page:
                show_snackbar(page, f"Exported: {result}")
            elif page:
                show_snackbar(page, "Export failed — case not found", ERROR_RED)
        except Exception as exc:
            if page:
                show_snackbar(page, f"Export error: {exc}", ERROR_RED)

    export_row = ft.Row([
        ft.Button(
            "Export TXT",
            icon=ft.Icons.DESCRIPTION,
            bgcolor=MATRIX_GREEN,
            color=ft.Colors.BLACK,
            on_click=_export_txt,
        ),
        ft.Button(
            "Export DOCX",
            icon=ft.Icons.ARTICLE,
            bgcolor=CYAN,
            color=ft.Colors.BLACK,
            on_click=_export_docx,
        ),
    ], spacing=12)

    # --- Timeline (IOC groups) ---
    timeline_controls: list[ft.Control] = []

    if not iocs:
        timeline_controls.append(
            ft.Container(
                content=ft.Text("No IOCs in this case.", color=ft.Colors.WHITE54, size=14),
                padding=ft.Padding.all(16),
            )
        )
    else:
        for ioc_group in iocs:
            ioc = ioc_group.get("ioc", {})
            events = ioc_group.get("events", [])
            ioc_value = ioc.get("value", "N/A")
            ioc_type = ioc.get("type", "unknown")

            # Build event rows for this IOC
            event_rows: list[ft.Control] = []
            for event in events:
                ev_type = event.get("type", "")
                timestamp = event.get("timestamp", "")
                summary = event.get("summary", "")

                if ev_type == "enrichment":
                    source = event.get("source", "")
                    severity = event.get("severity", "info")
                    sev_color = _SEVERITY_COLORS.get(severity, "#ffffff")
                    event_rows.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.INSIGHTS, color=CYAN, size=16),
                                    ft.Text(
                                        f"[{source}]",
                                        color=CYAN, size=13,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        severity.upper(),
                                        color=sev_color, size=12,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(timestamp, color=ft.Colors.WHITE54, size=11),
                                ], spacing=8),
                                ft.Text(summary, color=ft.Colors.WHITE, size=13),
                            ], spacing=4),
                            padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                        )
                    )

                elif ev_type == "analysis":
                    model = event.get("model", "unknown")
                    event_rows.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.SMART_TOY, color=MATRIX_GREEN, size=16),
                                    ft.Text(f"AI Analysis — {model}", color=MATRIX_GREEN, size=13,
                                            weight=ft.FontWeight.BOLD),
                                    ft.Text(timestamp, color=ft.Colors.WHITE54, size=11),
                                ], spacing=8),
                                ft.Text(summary, color=ft.Colors.WHITE, size=13),
                            ], spacing=4),
                            padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                            bgcolor="#0d1f0d",
                            border_radius=4,
                        )
                    )

                elif ev_type == "ioc_added":
                    event_rows.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.ADD_CIRCLE, color=CYAN, size=16),
                                ft.Text(
                                    f"IOC added — {event.get('ioc_type', 'unknown')}",
                                    color=ft.Colors.WHITE70, size=13,
                                ),
                                ft.Text(timestamp, color=ft.Colors.WHITE54, size=11),
                            ], spacing=8),
                            padding=ft.Padding.symmetric(vertical=2, horizontal=8),
                        )
                    )

                elif ev_type == "note":
                    event_rows.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.NOTE, color=ft.Colors.WHITE54, size=16),
                                ft.Text(summary, color=ft.Colors.WHITE70, size=13),
                                ft.Text(timestamp, color=ft.Colors.WHITE54, size=11),
                            ], spacing=8),
                            padding=ft.Padding.symmetric(vertical=2, horizontal=8),
                        )
                    )

            # Per-IOC export buttons
            def _make_ioc_export_txt(val: str):
                def _handler(e: ft.ControlEvent) -> None:
                    try:
                        cid = case_info.get("id")
                        if cid is None:
                            if page:
                                show_snackbar(page, "Export failed — missing case ID", ERROR_RED)
                            return
                        result = export_ioc_txt_to_file(cid, val)
                        if result and page:
                            show_snackbar(page, f"Exported: {result}")
                        elif page:
                            show_snackbar(page, "Export failed — IOC not found", ERROR_RED)
                    except Exception as exc:
                        if page:
                            show_snackbar(page, f"Export error: {exc}", ERROR_RED)
                return _handler

            def _make_ioc_export_docx(val: str):
                def _handler(e: ft.ControlEvent) -> None:
                    try:
                        cid = case_info.get("id")
                        if cid is None:
                            if page:
                                show_snackbar(page, "Export failed — missing case ID", ERROR_RED)
                            return
                        result = export_ioc_docx_to_file(cid, val)
                        if result and page:
                            show_snackbar(page, f"Exported: {result}")
                        elif page:
                            show_snackbar(page, "Export failed — IOC not found", ERROR_RED)
                    except Exception as exc:
                        if page:
                            show_snackbar(page, f"Export error: {exc}", ERROR_RED)
                return _handler

            ioc_export_row = ft.Row([
                ft.TextButton(
                    "Export TXT",
                    icon=ft.Icons.DESCRIPTION,
                    style=ft.ButtonStyle(color=CYAN),
                    on_click=_make_ioc_export_txt(ioc_value),
                ),
                ft.TextButton(
                    "Export DOCX",
                    icon=ft.Icons.ARTICLE,
                    style=ft.ButtonStyle(color=CYAN),
                    on_click=_make_ioc_export_docx(ioc_value),
                ),
            ], spacing=4)

            # IOC group card
            ioc_card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(
                            f"[{ioc_type}]",
                            color=CYAN, size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            ioc_value,
                            color=ft.Colors.WHITE, size=14,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Container(expand=True),
                        ioc_export_row,
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Divider(height=1, color=ft.Colors.WHITE24),
                    *event_rows,
                ], spacing=4),
                padding=ft.Padding.all(12),
                bgcolor="#141414",
                border=ft.Border.all(1, ft.Colors.WHITE24),
                border_radius=6,
            )
            timeline_controls.append(ioc_card)

    # --- Case notes section ---
    if notes:
        notes_section = ft.Container(
            content=ft.Column([
                ft.Text("Case Notes", size=16, color=CYAN, weight=ft.FontWeight.BOLD),
                *[
                    ft.Text(
                        f"[{n.get('created_at', '')}] {n.get('content', '')}",
                        color=ft.Colors.WHITE70,
                        size=13,
                    )
                    for n in notes
                ],
            ], spacing=4),
            padding=ft.Padding.all(12),
            bgcolor="#141414",
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=6,
        )
        timeline_controls.append(notes_section)

    # --- Assemble ---
    return ft.Column(
        controls=[
            header,
            export_row,
            ft.Text("Timeline", size=18, color=CYAN, weight=ft.FontWeight.BOLD),
            ft.Column(
                controls=timeline_controls,
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        ],
        spacing=12,
        expand=True,
    )
