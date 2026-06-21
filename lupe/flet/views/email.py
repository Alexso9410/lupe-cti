"""Email view — analyze .eml files with file picker and phishing detection."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from lupe.email_analyzer import analyze_email
from lupe.email_parser import parse_eml
from lupe.flet.theme import CYAN, MATRIX_GREEN
from lupe.flet.views.settings import load_settings


def build_email_view(page: ft.Page) -> ft.Control:
    """Build the email analysis view.

    Args:
        page: The Flet page.

    Returns:
        A Flet Column control for the email view.
    """
    # --- State ---
    selected_path: dict[str, str] = {"value": ""}

    # --- Input ---
    path_field = ft.TextField(
        label="Email file path",
        read_only=True,
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        expand=True,
    )

    # --- Output ---
    output_md = ft.Markdown(
        value="*Select an .eml file and click Analyze.*",
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
    )
    progress_ring = ft.ProgressRing(visible=False, width=20, height=20)

    # --- File picker ---
    file_picker = ft.FilePicker()

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            selected_path["value"] = e.files[0].path
            path_field.value = e.files[0].path
            page.update()

    file_picker.on_result = on_file_picked
    page.overlay.append(file_picker)
    page.update()

    # --- Buttons ---
    browse_btn = ft.ElevatedButton(
        "Browse",
        icon=ft.Icons.FOLDER_OPEN,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
    )
    browse_btn.on_click = lambda _: file_picker.pick_files(
        allowed_extensions=["eml"],
        dialog_title="Select .eml file",
    )

    analyze_btn = ft.ElevatedButton(
        "Analyze Email",
        icon=ft.Icons.ANALYTICS,
        bgcolor=CYAN,
        color=ft.Colors.BLACK,
    )

    def _show_snackbar(msg: str, color: str = MATRIX_GREEN):
        page.show_snack_bar(ft.SnackBar(ft.Text(msg), bgcolor=color))
        page.update()

    async def _analyze(e: ft.ControlEvent):
        file_path = selected_path["value"]
        if not file_path:
            _show_snackbar("Select an .eml file first", "#ff5555")
            return

        if not Path(file_path).exists():
            _show_snackbar(f"File not found: {file_path}", "#ff5555")
            return

        # Loading state
        analyze_btn.disabled = True
        progress_ring.visible = True
        output_md.value = "*Analyzing...*"
        page.update()

        try:
            parsed = parse_eml(file_path)
            settings_obj = _load_settings_obj()
            result = await analyze_email(parsed, settings_obj, no_ai=True)
            output_md.value = _format_result(result)
            _show_snackbar(f"Analysis complete — {len(result.iocs_found)} IOCs found")
        except Exception as exc:
            output_md.value = f"*Error: {exc}*"
            _show_snackbar(f"Analysis failed: {exc}", "#ff5555")
        finally:
            analyze_btn.disabled = False
            progress_ring.visible = False
            page.update()

    analyze_btn.on_click = _analyze

    return ft.Column(
        controls=[
            ft.Text(
                "Email Analysis",
                size=24,
                color=CYAN,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Analyze .eml files for phishing indicators and IOCs.",
                color=ft.Colors.WHITE70,
                size=14,
            ),
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Row(
                controls=[path_field, browse_btn],
                spacing=12,
            ),
            ft.Row(controls=[analyze_btn, progress_ring], spacing=12),
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Container(
                content=output_md,
                expand=True,
                padding=ft.Padding(top=8, bottom=8),
            ),
        ],
        spacing=12,
        expand=True,
    )


def _load_settings_obj():
    """Load settings into a Settings-like object for analyze_email."""
    from lupe.config import Settings

    raw = load_settings()
    # Map settings keys to Settings field names
    mapping = {
        "ollama_url": "ollama_base_url",
        "ollama_model": "ollama_model",
        "misp_url": "misp_url",
        "misp_key": "misp_key",
    }
    kwargs = {}
    for src, dst in mapping.items():
        if src in raw and raw[src]:
            kwargs[dst] = raw[src]
    return Settings(**kwargs)


def _format_result(result) -> str:
    """Format EmailAnalysisResult as Markdown."""
    lines: list[str] = []
    h = result.headers

    lines.append("## Email Headers")
    lines.append(f"- **From:** {h.from_addr}")
    lines.append(f"- **To:** {', '.join(h.to_addr)}")
    lines.append(f"- **Subject:** {h.subject}")
    lines.append(f"- **Date:** {h.date}")
    if h.reply_to:
        lines.append(f"- **Reply-To:** {h.reply_to}")

    lines.append("")
    lines.append("## Authentication")
    auth = result.auth
    spf_extra = f" ({auth.spf_domain})" if auth.spf_domain else ""
    dkim_extra = f" ({auth.dkim_domain})" if auth.dkim_domain else ""
    lines.append(f"- **SPF:** {auth.spf}{spf_extra}")
    lines.append(f"- **DKIM:** {auth.dkim}{dkim_extra}")
    lines.append(f"- **DMARC:** {auth.dmarc}")

    lines.append("")
    lines.append(f"## Phishing Score: {result.phishing_score.total:.1f}/10")
    if result.phishing_score.indicators:
        for ind in result.phishing_score.indicators:
            lines.append(f"- {ind}")

    if result.iocs_found:
        lines.append("")
        lines.append("## IOCs Found")
        for ioc in result.iocs_found:
            lines.append(f"- `{ioc.value}` ({ioc.type.value})")

    if result.attachments:
        lines.append("")
        lines.append("## Attachments")
        for att in result.attachments:
            exec_flag = " ⚠️ EXECUTABLE" if att.is_executable else ""
            lines.append(f"- {att.filename} ({att.mime_type}, {att.size_bytes} bytes)")
            lines.append(f"  SHA-256: `{att.sha256}`{exec_flag}")

    return "\n".join(lines)


# Class alias for import compatibility
EmailView = type("EmailView", (), {"build": staticmethod(build_email_view)})
