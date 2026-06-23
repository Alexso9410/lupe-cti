"""Email view — analyze .eml files with file picker and phishing detection."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from lupe.email_analyzer import analyze_email
from lupe.email_parser import parse_eml
from lupe.flet.theme import CYAN, MATRIX_GREEN
from lupe.flet.utils import show_snackbar
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

    def _on_pick_result(e: ft.FilePickerResultEvent) -> None:
        """Handle file picker result — set path and update UI."""
        if e.files and len(e.files) > 0:
            path = e.files[0].path
            selected_path["value"] = path
            path_field.value = path
            page.update()

    def _on_drag_accept(e: ft.DragTargetAcceptEvent) -> None:
        """Handle file dropped onto the drag target."""
        src = getattr(e, "src", None) or (getattr(e, "data", None) or "")
        # data may be a path-like or whitespace-separated list
        path_str = str(src).strip().strip('"')
        # Take first whitespace-separated token
        first = path_str.split()[0] if path_str else ""
        if first and Path(first).is_file() and first.lower().endswith(".eml"):
            selected_path["value"] = first
            path_field.value = first
            page.update()
            show_snackbar(page, f"File loaded: {first}", MATRIX_GREEN)
        elif first:
            show_snackbar(page, f"Not an .eml file: {first}", "#ff5555")

    # --- Input ---
    path_field = ft.TextField(
        label="Email file path (type, paste, or drag .eml here)",
        hint_text="e.g. C:\\path\\to\\email.eml",
        border_color=MATRIX_GREEN,
        focused_border_color=CYAN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        label_style=ft.TextStyle(color=ft.Colors.WHITE70),
        on_change=lambda e: selected_path.update({"value": e.control.value or ""}),
    )

    # Drag & drop target wrapping the path field
    drag_target = ft.DragTarget(
        group="files",
        content=path_field,
        expand=True,
        on_will_accept=lambda e: (
            page.update(),
            isinstance(getattr(e, "data", None), str) or "text" in (getattr(e, "data", None) or ""),
        )[-1],
        on_accept=_on_drag_accept,
    )

    # --- Output ---
    output_md = ft.Markdown(
        value="*Drag an .eml file here, browse, or paste a path. Then click Analyze.*",
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
    )
    progress_ring = ft.ProgressRing(visible=False, width=20, height=20)

    analyze_btn = ft.ElevatedButton(
        "Analyze Email",
        icon=ft.Icons.ANALYTICS,
        bgcolor=CYAN,
        color=ft.Colors.BLACK,
    )

    async def _browse(e: ft.ControlEvent) -> None:
        """Open native file picker.

        Tries Flet's FilePicker first (Flet 0.85.3 + page.overlay works on some
        versions). If that fails, falls back to a subprocess call to
        PowerShell which opens Windows' native file dialog. This is the most
        reliable cross-version workaround.
        """
        # Strategy 1: Flet FilePicker
        picker = None
        try:
            # Flet 0.85.3: FilePicker does NOT accept on_result in __init__,
            # it must be assigned as a property after construction.
            picker = ft.FilePicker()
            picker.on_result = _on_pick_result
            page.overlay.append(picker)
            page.update()
            await picker.pick_files(
                allowed_extensions=["eml"],
                dialog_title="Select .eml file",
            )
            return
        except Exception as exc:
            print(f"Flet FilePicker failed: {exc}", flush=True)
            # Clean up the broken picker from overlay
            try:
                if picker is not None and picker in page.overlay:
                    page.overlay.remove(picker)
                page.update()
            except Exception:
                pass

        # Strategy 2: subprocess to PowerShell to open Windows' native dialog.
        # PowerShell + System.Windows.Forms.OpenFileDialog is the most
        # reliable way to open a native file dialog on Windows.
        try:
            import subprocess

            # PowerShell script: use Windows Forms OpenFileDialog
            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$dlg = New-Object System.Windows.Forms.OpenFileDialog; "
                "$dlg.Filter = 'EML files (*.eml)|*.eml|All files (*.*)|*.*'; "
                "$dlg.Title = 'Select .eml file'; "
                "if ($dlg.ShowDialog() -eq 'OK') { Write-Output $dlg.FileName }"
            )
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=60,
            )
            chosen = (result.stdout or "").strip()
            if chosen:
                selected_path["value"] = chosen
                path_field.value = chosen
                page.update()
                show_snackbar(page, f"Selected: {chosen}", MATRIX_GREEN)
            else:
                show_snackbar(page, "No file selected", "#ff9800")
            return
        except Exception as exc:
            print(f"PowerShell file dialog failed: {exc}", flush=True)

        # Strategy 3: AlertDialog fallback (last resort)
        _show_dialog_input(page, path_field, selected_path)

    browse_btn = ft.ElevatedButton(
        "Browse",
        icon=ft.Icons.FOLDER_OPEN,
        bgcolor=MATRIX_GREEN,
        color=ft.Colors.BLACK,
        on_click=lambda e: page.run_task(_browse, e),
    )

    def _show_snackbar(msg: str, color: str = MATRIX_GREEN) -> None:
        show_snackbar(page, msg, color)

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
                controls=[drag_target, browse_btn],
                spacing=12,
            ),
            ft.Row(controls=[analyze_btn, progress_ring], spacing=12),
            ft.Divider(color=ft.Colors.WHITE24),
            ft.Container(
                content=output_md,
                padding=ft.Padding(top=8, bottom=8),
                expand=True,
            ),
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
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


def _on_pick(
    e: ft.FilePickerResultEvent,
    path_field: ft.TextField,
    selected_path: dict[str, str],
    page: ft.Page,
) -> None:
    """Handle file picker result."""
    if e.files and len(e.files) > 0:
        selected_path["value"] = e.files[0].path
        path_field.value = e.files[0].path
        page.update()


def _show_dialog_input(
    page: ft.Page,
    path_field: ft.TextField,
    selected_path: dict[str, str],
) -> None:
    """Show a dialog asking for the file path (fallback when FilePicker is unavailable)."""
    path_input = ft.TextField(
        label="Path to .eml file",
        autofocus=True,
        border_color=MATRIX_GREEN,
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
    )

    def on_submit(_e: ft.ControlEvent) -> None:
        if path_input.value:
            path_field.value = path_input.value
            selected_path["value"] = path_input.value
        page.pop_dialog()

    dialog = ft.AlertDialog(
        title=ft.Text("Enter .eml file path"),
        content=path_input,
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
            ft.ElevatedButton(
                "OK",
                on_click=on_submit,
                bgcolor=MATRIX_GREEN,
                color=ft.Colors.BLACK,
            ),
        ],
    )
    # Flet 0.85.3+: use show_dialog (page.open doesn't exist)
    page.show_dialog(dialog)
