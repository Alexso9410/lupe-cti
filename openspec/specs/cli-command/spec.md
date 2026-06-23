# Delta for cli-command

## MODIFIED Requirements

### Requirement: CLI Entry Point Name

The main CLI command SHALL be `lupe`. The desktop entry point SHALL be `lupe-desktop`.
(Previously: main CLI was `centinela` and desktop entry was `centinela-desktop`.)

#### Scenario: CLI help displays new branding

- GIVEN the command `lupe --help`
- WHEN it executes
- THEN the output banner reads "Lupe CTI — Cyber Threat Intelligence for OSINT & Forensics"

#### Scenario: Subcommands available under new name

- GIVEN the command `lupe enrich 8.8.8.8`
- WHEN it executes
- THEN it performs IOC enrichment identical to the previous `centinela enrich` behavior

#### Scenario: Legacy command not found

- GIVEN the command `centinela --help`
- WHEN it executes in an environment where only `lupe-cti` is installed
- THEN the shell returns "command not found"

#### Scenario: New migration subcommand

- GIVEN the command `lupe migrate-from-centinela`
- WHEN it executes
- THEN it copies the legacy Centinela database to the new Lupe XDG path

## REMOVED Requirements

### Requirement: Legacy CLI commands

(Reason: Hard cut rebrand. No `centinela` or `centinela-desktop` aliases are maintained.)
