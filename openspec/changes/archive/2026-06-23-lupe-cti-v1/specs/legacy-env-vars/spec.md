# Delta for legacy-env-vars

## REMOVED Requirements

### Requirement: Backward-compatible environment variable aliases

The system SHALL NOT read environment variables with the `CENTINELA_` prefix.
(Reason: Hard cut rebrand. No alias or fallback to legacy env vars is implemented to avoid confusion and technical debt.)

#### Scenario: CENTINELA_ variables ignored

- GIVEN `CENTINELA_OLLAMA_BASE_URL=http://old` and `LUPE_OLLAMA_BASE_URL` is unset
- WHEN the application starts
- THEN the Ollama base URL defaults to `http://localhost:11434` and the `CENTINELA_` value is not consulted

#### Scenario: Migration documentation

- GIVEN a user has existing `CENTINELA_*` variables
- WHEN they consult the README or `lupe config --help`
- THEN documentation clearly states the new `LUPE_*` prefix and provides a mapping of old to new names
