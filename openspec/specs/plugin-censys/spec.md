# Delta for plugin-censys

## ADDED Requirements

### Requirement: Censys Plugin

The system MUST implement an enrichment plugin `CensysPlugin` that queries Censys for IP, domain, and certificate data.

#### Scenario: IP host data

- GIVEN the IOC type is `IPv4` and `LUPE_CENSYS_KEY` is configured
- WHEN `enrich()` is called
- THEN the plugin returns open ports, services, certificates, and autonomous system data

#### Scenario: Certificate lookup

- GIVEN the IOC type is `domain` or `SHA256` (certificate fingerprint)
- WHEN `enrich()` is called
- THEN the plugin queries the Censys certificates endpoint and returns parsed fields

#### Scenario: Invalid credentials

- GIVEN `LUPE_CENSYS_KEY` is invalid
- WHEN `enrich()` is called
- THEN the plugin returns `None` and logs an authentication failure warning
