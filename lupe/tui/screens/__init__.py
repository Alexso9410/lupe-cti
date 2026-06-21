"""TUI screens package."""

from __future__ import annotations

from lupe.tui.screens.cases import CasesScreen
from lupe.tui.screens.enrich import EnrichScreen
from lupe.tui.screens.home import HomeScreen
from lupe.tui.screens.misp import MISPScreen
from lupe.tui.screens.plugins import PluginsScreen
from lupe.tui.screens.settings import SettingsScreen

__all__ = [
    "HomeScreen",
    "EnrichScreen",
    "SettingsScreen",
    "MISPScreen",
    "PluginsScreen",
    "CasesScreen",
]
