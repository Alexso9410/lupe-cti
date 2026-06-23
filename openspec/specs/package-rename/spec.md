# Delta for package-rename

## MODIFIED Requirements

### Requirement: Python Package Name

The Python package directory SHALL be named `lupe/` and the PyPI distribution name SHALL be `lupe-cti`.
(Previously: package directory was `centinela/` and PyPI name was `centinela`.)

#### Scenario: Import statements updated

- GIVEN a developer writes `from lupe.ioc_detect import detect_ioc`
- WHEN the code is executed
- THEN the import resolves correctly from the `lupe/` package

#### Scenario: Legacy import fails

- GIVEN a developer writes `from centinela.ioc_detect import detect_ioc`
- WHEN the code is executed
- THEN an `ImportError` is raised because the `centinela` package no longer exists

#### Scenario: pip install uses new name

- GIVEN the command `pip install lupe-cti`
- WHEN it executes
- THEN it installs the `lupe` package and registers CLI entry points `lupe` and `lupe-desktop`

## REMOVED Requirements

### Requirement: Legacy package name

(Reason: Hard cut rebrand. No backward compatibility aliases are provided.)
