# Delta for plugin-spamhaus

## ADDED Requirements

### Requirement: Spamhaus Plugin

The system MUST implement an enrichment plugin `SpamhausPlugin` that queries Spamhaus for IP and domain reputation.

#### Scenario: Malicious IP

- GIVEN the IOC type is `IPv4` and Spamhaus returns a listing
- WHEN `enrich()` is called with a valid Spamhaus key
- THEN the plugin returns threat category, confidence, and listing reason

#### Scenario: Domain lookup

- GIVEN the IOC type is `domain`
- WHEN `enrich()` is called
- THEN the plugin queries the Spamhaus domain API and returns reputation data if listed

#### Scenario: Missing API key

- GIVEN `LUPE_SPAMHAUS_KEY` is not set
- WHEN the plugin registry loads
- THEN `SpamhausPlugin` is excluded from the active plugin list
