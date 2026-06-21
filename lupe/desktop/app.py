"""PyWebView desktop application entry point for Centinela."""

from __future__ import annotations

from pathlib import Path

import webview

from lupe.desktop.bridge import CentinelaAPI


def main() -> None:
    """Launch the Centinela desktop window."""
    api = CentinelaAPI()

    html_path = Path(__file__).parent / "frontend" / "index.html"

    window = webview.create_window(
        title="Centinela — Heimdall Security",
        url=str(html_path),
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
        resizable=True,
        text_select=True,
    )  # noqa: F841 — window reference kept by webview internally

    webview.start(debug=False)


if __name__ == "__main__":
    main()
