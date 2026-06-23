# Delta for packaging-cross-platform

## ADDED Requirements

### Requirement: XDG Base Directory Compliance

The system MUST use XDG-compliant paths on Linux and equivalent paths on Windows.

#### Scenario: Linux default paths

- GIVEN the application runs on Linux with default environment
- WHEN it needs to store data, config, or cache
- THEN it uses `~/.local/share/lupe/`, `~/.config/lupe/`, and `~/.cache/lupe/` respectively

#### Scenario: Windows default paths

- GIVEN the application runs on Windows
- WHEN it needs to store data
- THEN it uses `%LOCALAPPDATA%\Lupe\lupe.db` for the database

#### Scenario: Custom XDG_DATA_HOME respected

- GIVEN `XDG_DATA_HOME=/mnt/data`
- WHEN the database is initialized
- THEN it is created at `/mnt/data/lupe/lupe.db`

### Requirement: pipx Installability

The system MUST be installable via `pipx install lupe-cti`.

#### Scenario: Clean pipx install

- GIVEN a fresh Debian 12 system with pipx installed
- WHEN `pipx install lupe-cti` is executed
- THEN `lupe` and `lupe-desktop` commands are available in PATH

### Requirement: Desktop Integration

The system MUST provide a `.desktop` file and manpage.

#### Scenario: .desktop file valid

- GIVEN `lupe.desktop` is installed to `/usr/share/applications/`
- WHEN the desktop environment lists applications
- THEN Lupe CTI appears in the Security/Network category with correct icon and exec command

#### Scenario: Manpage readable

- GIVEN `lupe.1` is installed
- WHEN `man lupe` is executed
- THEN it displays usage, subcommands, and environment variables in formatted groff output

### Requirement: Migration Command

The system MUST provide a manual migration command from Centinela.

#### Scenario: Migrate legacy database

- GIVEN `~/.centinela/centinela.db` exists
- WHEN `lupe migrate-from-centinela` is executed
- THEN a copy of the legacy database is created at the new XDG path and a success message is printed

#### Scenario: No legacy database found

- GIVEN `~/.centinela/centinela.db` does not exist
- WHEN `lupe migrate-from-centinela` is executed
- THEN the CLI prints an error and exits with code 1
