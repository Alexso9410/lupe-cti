# Delta for db-paths

## MODIFIED Requirements

### Requirement: Database Storage Paths

The system SHALL store the SQLite database at XDG-compliant paths on Linux and `%LOCALAPPDATA%` on Windows.
(Previously: the database was stored at `~/.centinela/centinela.db` on all platforms.)

#### Scenario: Linux default database path

- GIVEN the application runs on Linux with default environment variables
- WHEN the database is initialized
- THEN it is created at `~/.local/share/lupe/lupe.db`

#### Scenario: Windows default database path

- GIVEN the application runs on Windows
- WHEN the database is initialized
- THEN it is created at `%LOCALAPPDATA%\Lupe\lupe.db`

#### Scenario: Custom XDG path respected

- GIVEN `XDG_DATA_HOME=/opt/forensics/data`
- WHEN the database is initialized on Linux
- THEN it is created at `/opt/forensics/data/lupe/lupe.db`

## REMOVED Requirements

### Requirement: Legacy database path `~/.centinela/`

(Reason: Hard cut rebrand. The system no longer reads from or writes to `~/.centinela/` automatically. Migration is manual via `lupe migrate-from-centinela`.)
