"""Settings screen — API key configuration."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Input, Button, Label
from textual.containers import Vertical, VerticalScroll


class SettingsScreen(Screen):
    """Screen for configuring API keys and provider settings."""

    CSS = """
    .settings-group {
        margin: 0 2;
    }
    .key-input {
        margin: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("1", "app.push_screen('home')", "Home"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static("[bold #00FFFF]Settings[/bold #00FFFF] — Configure API Keys and Provider")
            yield Label("[bold]LLM Provider[/bold]", classes="settings-group")
            yield Input(placeholder="ollama / openai / anthropic / openrouter", id="input-llm-provider", classes="key-input")
            yield Input(placeholder="Ollama URL (http://localhost:11434)", id="input-ollama-url", classes="key-input")
            yield Label("[bold]LLM API Keys[/bold]", classes="settings-group")
            yield Input(placeholder="OpenAI API key (sk-...)", id="input-openai-key", classes="key-input", password=True)
            yield Input(placeholder="Anthropic API key (sk-ant-...)", id="input-anthropic-key", classes="key-input", password=True)
            yield Input(placeholder="OpenRouter API key (sk-or-...)", id="input-openrouter-key", classes="key-input", password=True)
            yield Label("[bold]Enrichment API Keys[/bold]", classes="settings-group")
            yield Input(placeholder="VirusTotal key", id="input-virustotal-key", classes="key-input", password=True)
            yield Input(placeholder="AbuseIPDB key", id="input-abuseipdb-key", classes="key-input", password=True)
            yield Input(placeholder="Shodan key", id="input-shodan-key", classes="key-input", password=True)
            yield Input(placeholder="OTX key", id="input-otx-key", classes="key-input", password=True)
            yield Input(placeholder="URLScan key", id="input-urlscan-key", classes="key-input", password=True)
            yield Input(placeholder="HIBP key", id="input-hibp-key", classes="key-input", password=True)
            yield Input(placeholder="GreyNoise key", id="input-greynoise-key", classes="key-input", password=True)
            yield Input(placeholder="IPQS key", id="input-ipqs-key", classes="key-input", password=True)
            yield Input(placeholder="NumVerify key", id="input-numverify-key", classes="key-input", password=True)
            yield Label("[bold]MISP[/bold]", classes="settings-group")
            yield Input(placeholder="MISP URL (https://misp.example.com)", id="input-misp-url", classes="key-input")
            yield Input(placeholder="MISP API key", id="input-misp-key", classes="key-input", password=True)
            yield Label("[bold]Censys[/bold]", classes="settings-group")
            yield Input(placeholder="Censys ID", id="input-censys-id", classes="key-input")
            yield Input(placeholder="Censys Secret", id="input-censys-secret", classes="key-input", password=True)
            yield Label("[bold]Hybrid Analysis[/bold]", classes="settings-group")
            yield Input(placeholder="Hybrid Analysis key", id="input-hybrid-analysis-key", classes="key-input", password=True)
            yield Static("", id="signup-link")
            yield Button("Save", id="btn-save", variant="success")
            yield Button("Test Keys", id="btn-test", variant="primary")
        yield Footer()
