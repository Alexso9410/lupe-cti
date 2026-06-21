"""Theme constants and dataclass for the Lupe CTI TUI."""

from __future__ import annotations

from dataclasses import dataclass

# Core palette
MATRIX_GREEN = "#00FF41"
CYAN = "#00FFFF"
DARK_BG = "#1a1a1a"
ERROR_RED = "#ff5555"
CHARCOAL = "#2a2a2a"
DIM_TEXT = "#888888"


@dataclass(frozen=True)
class LupeTheme:
    """Color tokens for the Lupe CTI TUI."""

    background: str = DARK_BG
    primary: str = CYAN
    success: str = MATRIX_GREEN
    error: str = ERROR_RED
    surface: str = CHARCOAL
    text: str = "#e0e0e0"
    text_dim: str = DIM_TEXT
    accent: str = CYAN
