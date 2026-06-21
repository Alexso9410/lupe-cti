# Delta for desktop-entry

## MODIFIED Requirements

### Requirement: Desktop Entry Point

The desktop GUI/TUI entry point SHALL be `lupe-desktop`.
(Previously: the desktop entry point was `centinela-desktop` which launched a pywebview window.)

#### Scenario: TUI launches from new entry point

- GIVEN the command `lupe-desktop` is executed
- WHEN the terminal supports interactive TUI
- THEN the Textual application launches with the Lupe branding and theme

#### Scenario: Legacy entry point unavailable

- GIVEN the command `centinela-desktop` is executed
- WHEN only `lupe-cti` is installed
- THEN the shell returns "command not found"

#### Scenario: systemd unit references correct binary

- GIVEN `lupe-watch.service` is installed
- WHEN the unit file is inspected
- THEN `ExecStart=` references `lupe-desktop` or `lupe` as appropriate

## REMOVED Requirements

### Requirement: pywebview desktop launcher

(Reason: Replaced by Textual TUI. The `centinela-desktop.py` standalone launcher and pywebview dependency are removed.)
