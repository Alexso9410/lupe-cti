"""Plugins screen — list enrichment plugins and their status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, DataTable
from textual.containers import Vertical


class PluginsScreen(Screen):
    """Screen listing all enrichment plugins and their configuration status."""

    CSS = """
    #plugins-table {
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
            Static("[bold #00FFFF]Plugins[/bold #00FFFF] — Enrichment plugin status"),
            DataTable(id="plugins-table"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Populate the plugins table on mount."""
        table = self.query_one("#plugins-table", DataTable)
        table.add_columns("Plugin", "Type", "Key Required", "Status")
        # Will be populated dynamically in future iteration
        table.add_row("Loading...", "", "", "")
