# Delta for security-hardening

## ADDED Requirements

### Requirement: Dependency Security Scanning

The system MUST run `pip-audit` and `bandit` in CI to detect known vulnerabilities and insecure code patterns.

#### Scenario: CI passes with clean scan

- GIVEN a PR is opened
- WHEN the CI workflow runs
- THEN `pip-audit` reports zero known vulnerabilities and `bandit` reports zero high-severity issues

#### Scenario: Vulnerability detected blocks merge

- GIVEN `pip-audit` finds a known CVE in a dependency
- WHEN the CI workflow runs
- THEN the security job fails and merge is blocked

### Requirement: Secret Detection

The system MUST prevent accidental commit of secrets using `gitleaks` or `detect-secrets` in a pre-commit hook.

#### Scenario: Secret in staged file

- GIVEN a developer stages a file containing `LUPE_OPENAI_API_KEY=sk-xxx`
- WHEN the pre-commit hook runs
- THEN the commit is rejected with a clear message indicating the detected secret and its location

### Requirement: API Key Redaction

The system MUST redact all API keys in logs, tracebacks, and CLI output.

#### Scenario: Log output sanitized

- GIVEN an error occurs during an HTTP request that includes an `Authorization` header
- WHEN the error is logged
- THEN the key value is replaced with `***` and the header name is preserved

#### Scenario: Config show command

- GIVEN the user runs `lupe config show`
- WHEN the output is rendered
- THEN all key fields display `***` instead of the actual values

### Requirement: HTTPS Enforcement

The system MUST reject non-HTTPS URLs in all external API calls.

#### Scenario: HTTP URL blocked

- GIVEN a plugin attempts to call `http://insecure.example.com/api`
- WHEN the request is made
- THEN the system raises a security error and the request is not sent

### Requirement: Input Validation

The system MUST validate IOC inputs before passing them to plugins.

#### Scenario: Overlong input rejected

- GIVEN an IOC string exceeding the maximum allowed length (e.g., 4096 chars)
- WHEN enrichment is requested
- THEN the CLI returns an error before any plugin executes

#### Scenario: Invalid format rejected

- GIVEN an input that does not match any known IOC regex pattern
- WHEN enrichment is requested
- THEN the CLI returns an error stating the type could not be detected
