# Delta for ci-cd-pipeline

## ADDED Requirements

### Requirement: GitHub Actions CI Matrix

The system MUST run CI across multiple operating systems on every PR.

#### Scenario: PR triggers CI

- GIVEN a pull request is opened against `main`
- WHEN the `ci.yml` workflow runs
- THEN jobs execute on Ubuntu 22.04, Ubuntu 24.04, Debian 12, Windows 10, and Windows 11 runners

#### Scenario: CI job structure

- GIVEN the CI workflow executes
- THEN it runs lint (ruff), type-check (mypy), test (pytest), and security (pip-audit + bandit) in parallel stages

### Requirement: Release Automation

The system MUST publish releases automatically on tag push.

#### Scenario: Tag push triggers release

- GIVEN a git tag matching `v*` is pushed
- WHEN the `release.yml` workflow runs
- THEN it builds manylinux wheels + sdist, publishes to PyPI, and creates a GitHub Release with assets

### Requirement: CodeQL Security Analysis

The system MUST run CodeQL on the default branch and on PRs.

#### Scenario: CodeQL scan clean

- GIVEN the `codeql.yml` workflow runs on `main`
- WHEN the scan completes
- THEN zero alerts are present in the default branch (or alerts are triaged and documented)

### Requirement: Dependency Review

The system MUST review dependency changes in PRs.

#### Scenario: New dependency introduced

- GIVEN a PR adds a new package to `pyproject.toml`
- WHEN the dependency review workflow runs
- THEN it flags any known vulnerabilities or license incompatibilities before merge
