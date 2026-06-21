"""Enrich screen — IOC enrichment interface."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Input, Button, TextArea
from textual.containers import Vertical


class EnrichScreen(Screen):
    """Screen for enriching IOCs interactively."""

    CSS = """
    #ioc-input {
        margin: 1 2;
    }
    #enrich-output {
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
            Static("[bold #00FFFF]Enrich IOC[/bold #00FFFF] — Enter an IP, domain, hash, URL, or email"),
            Input(placeholder="Enter IOC value...", id="ioc-input"),
            Button("Enrich", id="btn-enrich-run", variant="primary"),
            TextArea(id="enrich-output", read_only=True),
        )
        yield Footer()
