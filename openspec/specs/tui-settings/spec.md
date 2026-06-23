# Delta for tui-settings

## ADDED Requirements

### Requirement: API Key Settings Panel

The system MUST provide a Settings screen in the TUI where users can configure all API keys and provider settings.

#### Scenario: Display all provider fields

- GIVEN the user navigates to the Settings screen
- THEN input fields are shown for every LLM provider (Ollama base URL, OpenAI key, Anthropic key, OpenRouter key) and every keyed enrichment plugin (VirusTotal, AbuseIPDB, Shodan, OTX, URLScan, HaveIBeenPwned, GreyNoise, IPQS, NumVerify, MISP)

#### Scenario: Signup links available

- GIVEN the Settings screen is visible
- WHEN the user focuses a field for a provider that requires an API key
- THEN a help text or sidebar shows the signup URL (e.g., https://www.virustotal.com/ for VirusTotal)

#### Scenario: Live format validation

- GIVEN the user types into the OpenAI key field
- WHEN the input does not match the `sk-` prefix pattern
- THEN the field border turns red and a validation message appears immediately

#### Scenario: Secure persistence

- GIVEN the user saves settings from the TUI
- WHEN the config file is written on Linux
- THEN the file permissions are set to `600` (owner read/write only)

#### Scenario: Windows permission fallback

- GIVEN the user saves settings on Windows
- WHEN the config file is written
- THEN the file is written without Unix permissions, but the directory is restricted to the user profile
