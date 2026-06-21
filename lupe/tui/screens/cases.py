"""Cases screen — case management."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, DataTable, Button, Input
from textual.containers import Vertical


class CasesScreen(Screen):
    """Screen for managing investigation cases."""

    CSS = """
    #cases-table {
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
            Static("[bold #00FFFF]Cases[/bold #00FFFF] — Investigation case management"),
            Input(placeholder="New case name...", id="new-case-name"),
            Button("Create Case", id="btn-create-case", variant="success"),
            DataTable(id="cases-table"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Populate the cases table on mount."""
        table = self.query_one("#cases-table", DataTable)
        table.add_columns("ID", "Name", "Status", "IOCs", "Created")
        # Will be populated dynamically from DB in future iteration
        table.add_row("---", "No cases loaded", "", "", "")
