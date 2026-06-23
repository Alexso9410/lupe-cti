# Delta for frontend-replacement

## MODIFIED Requirements

### Requirement: Primary User Interface

The system's primary interactive interface SHALL be a Textual TUI application in `lupe/tui/`.
(Previously: the primary interactive interface was a pywebview window serving `centinela_kimi_frontend.html`.)

#### Scenario: TUI renders all screens

- GIVEN the user launches `lupe-desktop`
- WHEN navigating through Home, Enrich, Settings, MISP, Plugins, and Cases screens
- THEN each screen renders correctly in the terminal without requiring a display server

#### Scenario: pywebview no longer required

- GIVEN the application is installed on a headless server
- WHEN `lupe-desktop` is executed over SSH
- THEN the TUI opens without errors and `pywebview` is not imported

#### Scenario: Settings panel in TUI

- GIVEN the user navigates to the Settings screen in the TUI
- WHEN they view API key fields
- THEN all provider and plugin keys are editable with live validation and signup links

## REMOVED Requirements

### Requirement: HTML frontend file

(Reason: The monolithic HTML file `centinela_kimi_frontend.html` is deleted. All UI functionality is reimplemented in the Textual TUI.)
