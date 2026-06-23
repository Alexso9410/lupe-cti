# Delta for legacy-db-paths

## REMOVED Requirements

### Requirement: Automatic legacy database path access

The system SHALL NOT automatically read from or write to `~/.centinela/centinela.db`.
(Reason: Hard cut rebrand. Automatic access to legacy paths is removed to enforce XDG compliance and prevent accidental data mixing.)

#### Scenario: Legacy path not accessed on startup

- GIVEN `~/.centinela/centinela.db` exists but `~/.local/share/lupe/lupe.db` does not
- WHEN `lupe enrich` runs for the first time
- THEN a new database is created at `~/.local/share/lupe/lupe.db`; the legacy file is not touched

#### Scenario: Manual migration available

- GIVEN `~/.centinela/centinela.db` exists
- WHEN `lupe migrate-from-centinela` is executed
- THEN the legacy database is copied (not moved) to the new XDG path, preserving the original
