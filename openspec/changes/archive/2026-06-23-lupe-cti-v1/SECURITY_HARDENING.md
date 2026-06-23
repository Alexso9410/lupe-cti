# Security Hardening — lupe-cti-v1 (v1.0.0)

**Change**: `lupe-cti-v1` (centinela → Lupe CTI)
**Date**: 2026-06-23
**Status**: In Progress (5 sub-agents auditing, awaiting synthesis)
**Based on**: `pre-release-security-audit` skill v1.0

---

## Audit Scope

This security hardening report covers the **Lupe CTI v1.0.0** release candidate (HEAD `07565e4`, tag `v1.0.0`). The project is a Python CLI + Flet desktop app for cyber threat intelligence, with 25+ enrichment plugins, a multi-LLM system, MISP integration, email analysis, and auto-update functionality.

### Pre-existing audits

Before this hardening report, two audits were run:

1. **Judgment Day (Dual Blind Review)**: 2 independent judges found 12 real issues (0 CRITICAL, 8 WARNING, 4 INFO). 4 false positives. Results are in `final-audit.md`.
2. **Pre-Hardening Cleanup**: 4 commits resolved branding remnants, version drift, working tree hygiene, and file cleanup.

### This audit

This report consolidates findings from 5 parallel phases:

| Phase | Topic | Status |
|-------|-------|--------|
| 1 | Surface Map + STRIDE/PASTA Threat Model | 🔄 Awaiting |
| 2 | Supply Chain Risk Audit (dependencies) | ✅ Complete |
| 3 | CI/CD Security Audit (GitHub Actions) | ✅ Complete |
| 4 | Secrets & Credentials Audit | 🔄 Awaiting |
| 5 | OWASP Top 10 + Python-Specific | 🔄 Awaiting |

---

## Phase 2 — Supply Chain Risk Audit

> TO BE POPULATED after synthesis

---

## Phase 3 — CI/CD Security Audit

> TO BE POPULATED after synthesis

---

## Cross-Phase Findings

> TO BE POPULATED after synthesis (items found in 2+ phases)

---

## Risk Matrix

| # | Finding | Phase | Severity | CVSS approx | Fixed? | Fix commit |
|---|---------|-------|----------|-------------|--------|------------|
| | | | | | | |

---

## Fixes Applied

> TO BE POPULATED after user approves and fix agent runs

---

## Veredict (Post-Fixes)

> TO BE POPULATED after re-audit

---

## Notes

- The `pre-release-security-audit` skill (and its RELEASE_SECURITY_CHECKLIST.md template) was created during this audit and lives at `~/.config/opencode/skills/pre-release-security-audit/`.
- This SECURITY_HARDENING.md file should be archived with `sdd-archive` when the change is closed.
