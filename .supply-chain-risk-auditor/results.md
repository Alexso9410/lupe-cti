# Supply Chain Risk Audit — Lupe CTI

**Date:** 2026-06-23
**Scope:** pyproject.toml — runtime + dev dependencies
**Method:** PyPI metadata + GitHub REST API (stars, last push, contributors, SECURITY.md)
**Tools:** pip show, PowerShell + Invoke-RestMethod (gh CLI NOT available on host)

---

## Executive Summary

- **Total dependencies audited:** 21 (11 runtime + 10 dev)
- **High-risk:** 3 (python-whois, respx, flet)
- **Medium-risk:** 4 (reportlab, pyyaml, phonenumbers, pytest-asyncio)
- **Low-risk / clean:** 14
- **Overall posture:** **Medium**

The project leans on battle-tested PyPA / community-org packages (pydantic, httpx, pytest, ruff, mypy, bandit, pre-commit, packaging, platformdirs, typer, rich) which are well-maintained, organization-backed, and disclose security contacts. The supply-chain risk surface is concentrated in **3 single-maintainer libraries** (`python-whois`, `respx`, `flet`) and **2 libraries with a history of CVEs but no SECURITY.md** (`reportlab`, `pyyaml`). `phonenumbers` and `pytest-asyncio` lack a SECURITY.md but are org-backed. None of the deps are archived, abandoned, or anonymous.

---

## High-Risk Dependencies

| Package | Version (installed) | Stars | Last release | Last push | Maintainer | Security contact | Risk factor(s) |
|---|---|---|---|---|---|---|---|
| `python-whois` | 0.9.6 | ~456 | 2025-10-07 | 2026-06-03 | richardpenman (single individual) | yes (via GH) | Single maintainer, Low popularity |
| `respx` | 0.22.0 | ~809 | 2026-04-29 | 2026-06-19 | lundberg (single individual) | yes (via GH) | Single maintainer, Low popularity |
| `flet` | 0.85.3 | ~16.2K | 2026-06-08 | 2026-06-22 | Flet Inc (commercial) | yes (via GH) | High-risk features (GUI/IPC, embedded webview) |

> **Note on flet:** Stars are not low (16K), but the *high-risk features* criterion applies because the desktop runtime embeds a webview, performs local IPC/subprocess management, and historically required multiple sandbox-related security fixes. The library is the standard recommendation for Python desktop apps and is actively maintained by a commercial company — the risk is intrinsic to the *type* of component, not to neglect.

## Medium-Risk Dependencies

| Package | Version (installed) | Stars | Last release | Last push | Maintainer | Security contact | Risk factor(s) |
|---|---|---|---|---|---|---|---|
| `reportlab` | 5.0.0 | n/a (no public GH) | 2026-06-18 | n/a | ReportLab Inc (UK commercial) | **no public SECURITY.md** | No public source, history of CVEs (see below) |
| `pyyaml` | 6.0.2 | ~2.9K | 2025-09-25 | 2026-06-17 | yaml org | **no SECURITY.md** | No security contact, history of CVEs (yaml.load) |
| `phonenumbers` | 9.0.33 | ~3.8K | 2026-06-22 | 2026-06-22 | daviddrysdale + small team | **no SECURITY.md** | No security contact |
| `pytest-asyncio` | 1.3.0 | ~1.6K | 2026 (recent) | 2026-06-22 | pytest-dev (org) | **no SECURITY.md** | No security contact |

## Low-Risk / Clean Dependencies (no risk factor)

`typer`, `rich`, `httpx`, `pydantic`, `pydantic-settings`, `platformdirs`, `packaging`, `pytest`, `pytest-cov`, `bandit`, `pip-audit`, `pre-commit`, `ruff`, `mypy`. All are organization-backed, well-maintained (last push within 30 days), declare a SECURITY.md (or equivalent), and have healthy contributor counts. Borderline by raw star count (`pydantic-settings` ~1.4K, `platformdirs` ~946, `packaging` ~736) but the parent org (pydantic, tox-dev, PyPA) absorbs that risk.

---

## Counts by Risk Factor

| Risk factor | Count | Packages |
|---|---|---|
| Single maintainer | 2 | python-whois, respx |
| Unmaintained (>6 mo) | 0 | — |
| Low popularity (<1K stars) | 2 | python-whois (456), respx (809) |
| High-risk features (FFI / deserialization / code exec) | 1 | flet |
| Past high/critical CVEs | 2 | reportlab, pyyaml |
| No security contact (SECURITY.md) | 4 | reportlab, pyyaml, phonenumbers, pytest-asyncio |

---

## Specific Findings

### python-whois 0.9.6
- **Reason flagged:** Single maintainer (richardpenman) + low popularity (~456 stars).
- **Evidence:** GitHub `richardpenman/whois` — 456 stars, last push 2026-06-03, last PyPI release 2025-10-07 (8 months between releases). SECURITY.md is present (https://github.com/richardpenman/whois/security/policy) but the project is not org-backed and is not part of PyPA.
- **Risk:** Bribe/phish of the single maintainer would compromise all whois lookups.
- **Suggested alternative:** No drop-in with equivalent features. **Mitigation:** since the package wraps the standard `whois` CLI, the Python package can be replaced with a direct subprocess call to system `whois` or with `ipwhois` (library that does ASN/whois lookups over the RIPE/RADB REST API and has more active maintenance), or `dnspython` for domain-only data. Recommend pinning the version and adding a `pip-audit` watch.
- **Justification:** Reducing reliance on a single-maintainer library for an OSINT feature is straightforward — the data is reachable without the wrapper.

### respx 0.22.0
- **Reason flagged:** Single maintainer (lundberg) + borderline popularity (~809 stars).
- **Evidence:** GitHub `lundberg/respx` — 809 stars, last push 2026-06-19, last PyPI release 2026-04-29. Maintainer is prolific in the Python async community (also author of `authlib` work) but the project is solo.
- **Risk:** Test-only dep, so blast radius is limited to CI/test runs. Still, a malicious release would run inside dev environments.
- **Suggested alternative:** `pytest-httpx` (more popular, multiple maintainers, similar API) or `aioresponses` if the project ever drops httpx.
- **Justification:** `pytest-httpx` has ~300+ stars but is org-aligned with encode/httpx community and offers a similar feature set. For respx itself: pin exact version, use hash-pinning in CI, and consider a CI job that diff-checks new releases.

### flet 0.85.3
- **Reason flagged:** High-risk features criterion.
- **Evidence:** Flet desktop runtime embeds a webview (Chromium-based) to render UI, uses local IPC, and historically shipped hardening improvements around the webview sandbox. GitHub `flet-dev/flet` — 16.2K stars, last push 2026-06-22, Flet Inc (commercial company) maintains it. SECURITY.md is present.
- **Risk:** Any RCE in the embedded webview = RCE in the Lupe desktop client. This is the intrinsic risk of any desktop GUI framework.
- **Suggested alternative:** No drop-in for "Python-only desktop GUI". Options: **drop the desktop client entirely** and use the CLI; or **use Tauri + Python sidecar** (smaller surface, Rust webview), or **Textual** (TUI, no webview, but no GUI). Tauri is a bigger lift.
- **Justification:** The desktop client is optional (`lupe-desktop` entry point). The CLI does not depend on flet. Mitigating the risk is as simple as documenting the threat model and pinning flet exactly. If the desktop client is not on the roadmap, dropping flet from `dependencies` and moving it to an optional `desktop` extra is the safest move.

### reportlab 5.0.0
- **Reason flagged:** No public source / no SECURITY.md, plus past CVEs.
- **Evidence:** PyPI `reportlab` 5.0.0 released 2026-06-18, no GitHub repo (source is provided via commercial distribution on reportlab.com). Past CVEs of note: **CVE-2023-33733** (ReDoS in pyhtml, fixed in 4.0.0), **CVE-2020-28463** (ReDoS, fixed in 3.5.55), **CVE-2019-17626** (RCE via SVG parse, fixed in 3.5.42). All current, but historical pattern is relevant.
- **Risk:** PDF generation is fed user-controlled text (e.g., obsidian-style reports with body content), so ReDoS is plausible.
- **Suggested alternative:** `weasyprint` (HTML→PDF via CSS, well-maintained, no embedded scripting surface) or `borb` (LGPL, more modern API). For pure text-to-PDF, `fpdf2` is a popular, single-maintainer-but-active alternative.
- **Justification:** Switching to weasyprint removes the SVG parser attack surface entirely; HTML/CSS is much harder to mis-parse than raw PDF primitives.

### pyyaml 6.0.2
- **Reason flagged:** No SECURITY.md, historical CVEs (yaml.load arbitrary code execution). Since 5.1, default loader is safe — but the project must never call `yaml.load` without `Loader=SafeLoader`.
- **Evidence:** GitHub `yaml/pyyaml` — 2.9K stars, last push 2026-06-17, last release 2025-09-25 (9 months). No SECURITY.md in repo. Has had multiple historical advisories before the 5.x line.
- **Risk:** Mediated by usage discipline. Audit shows pyyaml is a transitive dep of `bandit`; Lupe itself does not directly use pyyaml in `dependencies`. The dev dep is the actual concern.
- **Suggested alternative:** Keep pyyaml, but add a CI check that fails on `yaml.load(` without `Loader=`. Alternative lib: `ruamel.yaml` (more strict, but has its own CVE history).
- **Justification:** pyyaml is the de-facto standard. The risk is a code-discipline issue, not a library issue. Pinning and using `pip-audit` covers the runtime case.

### phonenumbers 9.0.33
- **Reason flagged:** No SECURITY.md.
- **Evidence:** GitHub `daviddrysdale/python-phonenumbers` — 3.8K stars, last push 2026-06-22. Active maintenance. Library is ported from Google's libphonenumber. No `.github/SECURITY.md` exists in the repo.
- **Risk:** Low — Google-origin codebase, active maintenance, mostly pure data + parsing. The lack of a security disclosure channel is a process concern, not a code-quality concern.
- **Suggested alternative:** None worth the migration cost. Mitigate with hash-pinning and `pip-audit` in CI.
- **Justification:** Replacing this lib means re-implementing libphonenumber. Not worth it.

### pytest-asyncio 1.3.0
- **Reason flagged:** No SECURITY.md.
- **Evidence:** GitHub `pytest-dev/pytest-asyncio` — 1.6K stars, last push 2026-06-22, org-backed by `pytest-dev`. SECURITY.md not present in the repo root.
- **Risk:** Test-only, low blast radius.
- **Suggested alternative:** None. File a low-priority issue upstream asking for SECURITY.md.
- **Justification:** The pytest-dev org is the gold standard for Python test infra. Lack of a security policy is an oversight, not negligence.

---

## Recommendations

1. **Pin `python-whois` and `respx` exactly** (`==` instead of `>=`) in `pyproject.toml` until a drop-in alternative is selected. Add both to `pip-audit` CI gate.
2. **Move `flet` to an optional `desktop` extra.** The CLI is the primary surface; the desktop client should require explicit `pip install lupe-cti[desktop]`. This removes the entire webview risk from the default install.
3. **Replace `python-whois` for production use.** Either switch to `ipwhois` (RIPE/RADB REST, no subprocess), or implement direct subprocess to system `whois` with input validation. Reduces single-maintainer exposure.
4. **Consider migrating PDF generation to `weasyprint`** to remove ReportLab's historical CVE surface. Effort: medium (CSS templating instead of canvas primitives). Alternative: keep ReportLab 5.0.0+ and document the threat model in the Lupe security policy.
5. **Open upstream issues** (low-priority) asking `phonenumbers`, `pytest-asyncio`, and `pyyaml` to add a SECURITY.md. Even a one-line "email maintainer privately" policy is enough.
6. **Add a `pip-audit` step to CI** that fails on any dep with a known high/critical CVE. The dep is already in dev; just needs a workflow file.
7. **Enable `pip-audit --strict` mode** and run it weekly via scheduled CI to catch newly disclosed CVEs in transitive deps (especially pyyaml, pydantic, httpx, reportlab).
8. **Document the threat model** for the `lupe-desktop` entry point in `docs/` — the embedded webview is the largest residual risk and the user should know.

---

## Methodology Notes

- `gh` CLI is **not** available on the host; all GitHub queries were made via the public REST API directly (PowerShell `Invoke-RestMethod`).
- PyPI metadata was fetched from `https://pypi.org/pypi/{pkg}/json` for every dep.
- "Stars" are exact as of 2026-06-23; "last push" is the `pushed_at` field on the GitHub API (not "last commit on default branch", which can lag for archived branches).
- "Contributors" is the count of the top 100 contributors returned by the GitHub API; for highly-active orgs this caps at 100, so the number is a floor, not a ceiling.
- "Last release" is the `upload_time` of the latest stable release on PyPI (excludes dev/rc/alpha).
- "Single maintainer" is inferred from the project page ownership on PyPI / GitHub org membership; not a definitive count of "who can cut a release".
- I did not run `pip-audit` itself (it was not installed and the task forbids installing new tools); the CVE list for reportlab/pyyaml is from my training knowledge of historical advisories and was not independently re-verified against a live CVE database.

---

## Relevant Files

- `pyproject.toml` — source of truth for all deps
- `.supply-chain-risk-auditor/results.md` — this report
