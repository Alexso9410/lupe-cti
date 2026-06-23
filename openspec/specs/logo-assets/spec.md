# Delta for logo-assets

## ADDED Requirements

### Requirement: Logo Asset Generation

The system MUST include logo assets in the repository under `assets/logo/`.

#### Scenario: SVG primary asset exists

- GIVEN the repository is checked out
- THEN `assets/logo/lupe-logo.svg` exists and renders an abstract magnifying glass with binary matrix green (#00FF41) lens, crossed headphones behind, on a dark background

#### Scenario: PNG exports at all sizes

- GIVEN the build/packaging process runs
- THEN PNG files exist at 256x256, 128x128, 64x64, 32x32, and 16x16 pixels in `assets/logo/`

#### Scenario: Monochrome variant

- GIVEN the repository is checked out
- THEN `assets/logo/lupe-logo-mono.svg` exists and renders legibly in single color for manpages, terminals, and grayscale contexts

### Requirement: Logo Integration

The system MUST reference logo assets in packaging and runtime metadata.

#### Scenario: pyproject.toml includes icon URL

- GIVEN `pyproject.toml` is parsed
- THEN it contains a project URL or readme badge referencing the logo SVG

#### Scenario: TUI splash screen

- GIVEN the TUI launches
- THEN the logo or its ASCII representation appears in the splash/header area

#### Scenario: .desktop file references icon

- GIVEN `lupe.desktop` is installed
- THEN the `Icon=` key points to the installed logo path
