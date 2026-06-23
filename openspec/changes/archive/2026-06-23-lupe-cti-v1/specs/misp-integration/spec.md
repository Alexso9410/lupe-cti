# Delta for misp-integration

## ADDED Requirements

### Requirement: MISP REST Client

The system MUST implement a lightweight MISP client in `lupe/integrations/misp.py` using `httpx.AsyncClient` directly (no `pymisp` dependency).

#### Scenario: Pull indicators from MISP

- GIVEN `LUPE_MISP_URL` and `LUPE_MISP_KEY` are configured
- WHEN `MISPClient.get_indicators(filters={"tags": ["osint"], "days": 7})` is called
- THEN it returns a list of `IOC` objects parsed from the MISP REST API response

#### Scenario: Push indicator to MISP

- GIVEN a valid `ioc: IOC` and `tags: list[str]`
- WHEN `MISPClient.add_indicator(ioc, tags=["lupe-enrichment"])` is called
- THEN it creates an event/attribute in MISP and returns the new attribute UUID

#### Scenario: MISP not configured

- GIVEN `LUPE_MISP_URL` or `LUPE_MISP_KEY` is missing
- WHEN any `lupe misp` subcommand is invoked
- THEN the CLI exits with a clear error message and a link to documentation

### Requirement: MISP CLI Commands

The system MUST expose `lupe misp pull` and `lupe misp push` subcommands.

#### Scenario: Pull with filters

- GIVEN the CLI command `lupe misp pull --tag osint --days 7`
- WHEN it executes
- THEN it prints a table of pulled IOCs with their types and values

#### Scenario: Push single IOC

- GIVEN the CLI command `lupe misp push 8.8.8.8`
- WHEN it executes
- THEN it enriches the IOC, converts the result to MISP format, and uploads it

#### Scenario: MISP failure does not break enrichment

- GIVEN the main `lupe enrich` command is running
- WHEN the MISP plugin is not configured or returns an error
- THEN the enrichment pipeline continues with other plugins; MISP errors are isolated
