# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Lupe CTI, please report it responsibly.

**Do NOT open a public issue for security vulnerabilities.**

### How to Report

1. **GitHub Security Advisories** (preferred): Use the [Security Advisories](https://github.com/Alexso9410/lupe-cti/security/advisories/new) feature to report privately
2. **Email**: Send details to the maintainers via the contact information in the repository

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Fix timeline**: Provided within 7 days of acknowledgment
- **Public disclosure**: After the fix is released (coordinated disclosure)

## Disclosure Policy

We follow coordinated disclosure:

1. Reporter submits the vulnerability privately
2. We acknowledge and assess the report
3. We develop and test a fix
4. We release the fix and publish a security advisory
5. We credit the reporter (unless they prefer anonymity)

We ask that reporters:
- Give us reasonable time to address the issue before public disclosure
- Avoid exploiting the vulnerability beyond what is necessary to demonstrate it
- Avoid accessing or modifying data belonging to other users

## Security Measures

Lupe CTI implements the following security measures:

### Transport Security
- HTTPS-only enforcement for all external API calls
- Localhost (Ollama) exempted from HTTPS requirement

### Input Validation
- IOC values validated by type with per-type maximum lengths
- Absolute maximum IOC length: 4096 characters

### Credential Protection
- API keys redacted in CLI output and log formatters
- Config directory permissions: chmod 700 (Linux)
- Config file permissions: chmod 600 (Linux, TUI settings)

### Rate Limiting
- Token-bucket rate limiter for plugin concurrency
- Configurable `max_requests` / `per_seconds`

### Static Analysis
- Pre-commit hooks: gitleaks, ruff, bandit
- CI pipeline: bandit, pip-audit, mypy, CodeQL
- Dependency review on all PRs
- Dependabot for automated dependency updates
