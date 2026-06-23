# Delta for plugin-hybrid-analysis

## ADDED Requirements

### Requirement: Hybrid Analysis Plugin

The system MUST implement an enrichment plugin `HybridAnalysisPlugin` that submits and queries files/URLs via the Hybrid Analysis API.

#### Scenario: Hash lookup with results

- GIVEN the IOC type is `SHA256` and `LUPE_HYBRID_ANALYSIS_KEY` is set
- WHEN `enrich()` is called
- THEN the plugin returns sandbox verdict, threat score, and behavioral indicators

#### Scenario: URL submission

- GIVEN the IOC type is `URL`
- WHEN `enrich()` is called
- THEN the plugin queries the URL analysis endpoint and returns scan results

#### Scenario: Freemium quota exceeded

- GIVEN the API returns a quota exceeded response
- WHEN `enrich()` is called
- THEN the plugin logs a warning, returns `None`, and does not crash the pipeline
