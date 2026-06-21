"""Home screen — main dashboard for the Lupe CTI TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

_LUPE_BANNER = r"""
 ██╗     ██╗   ██╗██████╗ ███████╗
 ██║     ██║   ██║██╔══██╗██╔════╝
 ██║     ██║   ██║██████╔╝█████╗
 ██║     ██║   ██║██╔═══╝ ██╔══╝
 ███████╗╚██████╔╝██║     ███████╗
 ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝
      Cyber Threat Intelligence
"""


class HomeScreen(Screen):
    """Main dashboard screen with navigation options."""

    CSS = """
    #banner {
        color: #00FF41;
        text-align: center;
        margin: 1 0;
    }
    #subtitle {
        color: #00FFFF;
        text-align: center;
        margin-bottom: 2;
    }
    .nav-button {
        width: 100%;
        margin: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("1", "app.push_screen('home')", "Home"),
        ("2", "app.push_screen('enrich')", "Enrich"),
        ("3", "app.push_screen('settings')", "Settings"),
        ("4", "app.push_screen('misp')", "MISP"),
        ("5", "app.push_screen('plugins')", "Plugins"),
        ("6", "app.push_screen('cases')", "Cases"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(_LUPE_BANNER, id="banner"),
            Label(
                "[bold #00FFFF]Lupe CTI[/bold #00FFFF] — Cyber Threat Intelligence", id="subtitle"
            ),
            Button("Enrich IOC  [2]", id="btn-enrich", variant="primary", classes="nav-button"),
            Button("Settings    [3]", id="btn-settings", variant="default", classes="nav-button"),
            Button("MISP        [4]", id="btn-misp", variant="default", classes="nav-button"),
            Button("Plugins     [5]", id="btn-plugins", variant="default", classes="nav-button"),
            Button("Cases       [6]", id="btn-cases", variant="default", classes="nav-button"),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation button presses."""
        btn_id = event.button.id
        if btn_id == "btn-enrich":
            self.app.push_screen("enrich")
        elif btn_id == "btn-settings":
            self.app.push_screen("settings")
        elif btn_id == "btn-misp":
            self.app.push_screen("misp")
        elif btn_id == "btn-plugins":
            self.app.push_screen("plugins")
        elif btn_id == "btn-cases":
            self.app.push_screen("cases")
