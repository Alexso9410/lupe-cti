# Delta for plugin-blocklist-de

## ADDED Requirements

### Requirement: Blocklist.de Plugin

The system MUST implement an enrichment plugin `BlocklistDePlugin` in `lupe/enrichment/` that queries blocklist.de for IP reputation.

#### Scenario: IP reported in blocklist

- GIVEN the IOC type is `IPv4` and the IP exists in blocklist.de
- WHEN `enrich()` is called
- THEN the plugin returns an `EnrichmentResult` with abuse categories, report counts, and source URL

#### Scenario: Clean IP

- GIVEN the IOC type is `IPv4` and the IP is not listed
- WHEN `enrich()` is called
- THEN the plugin returns `None` silently

#### Scenario: Rate limit respected

- GIVEN multiple enrichment jobs run concurrently
- WHEN the plugin makes requests to blocklist.de
- THEN it respects the internal rate limit of 5 req/sec per host and queues excess requests
