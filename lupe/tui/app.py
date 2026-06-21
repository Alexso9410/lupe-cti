"""Main Textual application for Lupe CTI TUI."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from lupe.tui.theme import LupeTheme, MATRIX_GREEN, CYAN, DARK_BG, ERROR_RED
from lupe.tui.screens.home import HomeScreen
from lupe.tui.screens.enrich import EnrichScreen
from lupe.tui.screens.settings import SettingsScreen
from lupe.tui.screens.misp import MISPScreen
from lupe.tui.screens.plugins import PluginsScreen
from lupe.tui.screens.cases import CasesScreen

_CSS = f"""
Screen {{
    background: {DARK_BG};
}}
Header {{
    background: {CYAN};
    color: {DARK_BG};
}}
Footer {{
    background: {DARK_BG};
}}
#banner {{
    color: {MATRIX_GREEN};
}}
"""


class LupeTuiApp(App):
    """Lupe CTI — Text User Interface.

    A terminal-based interface for cyber threat intelligence
    investigation and enrichment.
    """

    TITLE = "Lupe CTI"
    CSS = _CSS

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("question_mark", "help", "Help"),
        ("1", "push_screen('home')", "Home"),
        ("2", "push_screen('enrich')", "Enrich"),
        ("3", "push_screen('settings')", "Settings"),
        ("4", "push_screen('misp')", "MISP"),
        ("5", "push_screen('plugins')", "Plugins"),
        ("6", "push_screen('cases')", "Cases"),
    ]

    SCREENS = {
        "home": HomeScreen,
        "enrich": EnrichScreen,
        "settings": SettingsScreen,
        "misp": MISPScreen,
        "plugins": PluginsScreen,
        "cases": CasesScreen,
    }

    def on_mount(self) -> None:
        """Start on the home screen."""
        self.push_screen("home")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()


def run() -> None:
    """Entry point for the lupe-desktop command."""
    LupeTuiApp().run()


def main() -> None:
    """Alias for run() — used by pyproject.toml entry point."""
    run()
