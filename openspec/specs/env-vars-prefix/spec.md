# Delta for env-vars-prefix

## MODIFIED Requirements

### Requirement: Environment Variable Prefix

All environment variables used by the application SHALL use the `LUPE_` prefix.
(Previously: all environment variables used the `CENTINELA_` prefix.)

#### Scenario: Config loads from LUPE_ variables

- GIVEN `LUPE_VIRUSTOTAL_KEY=vt-key-123` is set in the environment
- WHEN the settings singleton is initialized
- THEN `settings.virustotal_key` equals `vt-key-123`

#### Scenario: Legacy variables ignored

- GIVEN `CENTINELA_VIRUSTOTAL_KEY=old-key-456` is set but `LUPE_VIRUSTOTAL_KEY` is unset
- WHEN the settings singleton is initialized
- THEN `settings.virustotal_key` is `None` and the legacy variable is not read

#### Scenario: New LLM provider variables

- GIVEN `LUPE_LLM_PROVIDER=anthropic`, `LUPE_ANTHROPIC_API_KEY=sk-ant-xxx`, and `LUPE_OLLAMA_BASE_URL=http://ollama.local:11434`
- WHEN the settings singleton is initialized
- THEN all three values are available to the application

## REMOVED Requirements

### Requirement: CENTINELA_ prefix support

(Reason: Hard cut rebrand. No backward compatibility aliases for environment variables.)
