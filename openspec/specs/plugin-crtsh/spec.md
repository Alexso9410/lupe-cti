# Delta for plugin-crtsh

## ADDED Requirements

### Requirement: crt.sh Plugin

The system MUST implement an enrichment plugin `CrtShPlugin` that queries crt.sh for certificate transparency logs related to domains.

#### Scenario: Domain certificates found

- GIVEN the IOC type is `domain`
- WHEN `enrich()` is called
- THEN the plugin returns a list of certificates with issuer, subject, SANs, and entry timestamp

#### Scenario: No certificates

- GIVEN the IOC type is `domain` and crt.sh returns no results
- WHEN `enrich()` is called
- THEN the plugin returns `None`

#### Scenario: Unsupported IOC type

- GIVEN the IOC type is `IPv4` or `hash`
- WHEN `enrich()` is called
- THEN the plugin returns `None` immediately without making an HTTP request
