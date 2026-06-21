"""MISP screen — pull/push indicators."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static


class MISPScreen(Screen):
    """Screen for MISP integration (pull/push IOCs)."""

    CSS = """
    #misp-output {
        margin: 1 2;
        height: 1fr;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("1", "app.push_screen('home')", "Home"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("[bold #00FFFF]MISP[/bold #00FFFF] — Pull and push indicators"),
            Input(placeholder="Tag filter (e.g. osint)", id="misp-tag"),
            Input(placeholder="Days to look back (default: 7)", id="misp-days"),
            Button("Pull Indicators", id="btn-misp-pull", variant="primary"),
            Static("[bold]Push to MISP[/bold]"),
            Input(placeholder="IOC value to push", id="misp-push-ioc"),
            Button("Push IOC", id="btn-misp-push", variant="success"),
        )
        yield Footer()
