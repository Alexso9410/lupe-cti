# Delta for plugin-cisco-talos

## ADDED Requirements

### Requirement: Cisco Talos Plugin

The system MUST implement an enrichment plugin `CiscoTalosPlugin` that queries Cisco Talos Intelligence for IP and domain reputation.

#### Scenario: Reputation data retrieved

- GIVEN the IOC type is `IPv4` or `domain` and `LUPE_CISCO_TALOS_KEY` is configured
- WHEN `enrich()` is called
- THEN the plugin returns reputation score, threat level, and related categories

#### Scenario: API key missing

- GIVEN `LUPE_CISCO_TALOS_KEY` is unset
- WHEN the plugin registry loads
- THEN the plugin is not registered for enrichment

#### Scenario: API returns error

- GIVEN the Talos API returns HTTP 429
- WHEN `enrich()` is called
- THEN the plugin logs the error, returns `None`, and the pipeline continues
