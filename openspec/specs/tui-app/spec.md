# Delta for tui-app

## ADDED Requirements

### Requirement: Textual TUI Application

The system MUST implement a Textual-based TUI in `lupe/tui/` that replaces the pywebview desktop GUI.

#### Scenario: Launch TUI

- GIVEN the command `lupe-desktop` is executed
- WHEN the terminal supports TUI rendering
- THEN a full-screen Textual application launches with a dark theme, cyan accents, and green matrix highlights

#### Scenario: SSH headless operation

- GIVEN the application runs over SSH without a display server
- WHEN `lupe-desktop` is executed
- THEN the TUI renders identically using terminal escape sequences, with no dependency on X11/Wayland

#### Scenario: Navigation between screens

- GIVEN the TUI is running
- WHEN the user presses Tab or uses key bindings
- THEN focus moves between Home, Enrich, Settings, MISP, Plugins, and Cases screens

### Requirement: TUI Theme

The system MUST apply a consistent dark theme across all TUI screens.

#### Scenario: Theme colors render correctly

- GIVEN the TUI is displayed
- THEN the background is dark, primary accent is cyan, success indicators are matrix green (#00FF41), and errors are red

#### Scenario: Cross-platform consistency

- GIVEN the TUI runs on Windows 10 or Debian 12
- THEN the color palette and layout are visually identical
