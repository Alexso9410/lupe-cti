from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from centinela.models import EnrichmentResult, IOC, Severity

# Severity ordering for comparison
_SEVERITY_RANK: dict[Severity, int] = {
    Severity.info: 0,
    Severity.low: 1,
    Severity.medium: 2,
    Severity.high: 3,
    Severity.critical: 4,
}

_MITRE_PATTERN = re.compile(r"\b(T\d{4}(?:\.\d{3})?)\b")


def _highest_severity(enrichments: list[EnrichmentResult]) -> Severity:
    """Return the highest severity across all enrichment results."""
    if not enrichments:
        return Severity.info
    return max(enrichments, key=lambda e: _SEVERITY_RANK[e.severity]).severity


def _extract_mitre_tags(text: str) -> list[str]:
    """Extract MITRE ATT&CK technique IDs from free text and return as tags."""
    return [f"mitre/{tid}" for tid in sorted(set(_MITRE_PATTERN.findall(text)))]


def _build_frontmatter(
    ioc: IOC,
    severity: Severity,
    enrichments: list[EnrichmentResult],
    analysis: str | None,
    case_name: str | None,
    today: date,
) -> str:
    """Build YAML frontmatter block."""
    tags: list[str] = [
        f"ioc/{ioc.type.value}",
        f"severity/{severity.value}",
    ]
    tags.extend(f"source/{e.source.lower().replace(' ', '-')}" for e in enrichments)

    if analysis:
        tags.extend(_extract_mitre_tags(analysis))

    # Also scan enrichment summaries for MITRE codes
    for e in enrichments:
        tags.extend(_extract_mitre_tags(e.summary))

    # Deduplicate preserving order
    seen: set[str] = set()
    unique_tags: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    lines = [
        "---",
        "type: ioc-enrichment",
        f"ioc_type: {ioc.type.value}",
        f'ioc_value: "{ioc.value}"',
        f"severity: {severity.value}",
        "tags:",
    ]
    lines.extend(f"  - {tag}" for tag in unique_tags)

    if case_name:
        lines.append(f'case: "{case_name}"')

    lines.append(f"date: {today.isoformat()}")
    lines.append("---")
    return "\n".join(lines)


def _build_enrichment_section(enrichments: list[EnrichmentResult]) -> str:
    """Build the enrichment results section in markdown."""
    if not enrichments:
        return "_No enrichment results available._"

    blocks: list[str] = []
    for result in enrichments:
        block_lines = [
            f"### {result.source}",
            f"- **Severidad**: {result.severity.value}",
            f"- {result.summary}",
        ]
        blocks.append("\n".join(block_lines))

    return "\n\n".join(blocks)


def export_ioc_to_obsidian(
    ioc: IOC,
    enrichments: list[EnrichmentResult],
    analysis: str | None = None,
    case_name: str | None = None,
) -> str:
    """Generate an Obsidian markdown note for an IOC.

    Args:
        ioc: The IOC being documented.
        enrichments: List of enrichment results from plugins.
        analysis: Optional AI-generated analysis text.
        case_name: Optional case identifier (e.g. "OP-2026-14").

    Returns:
        A complete Obsidian-compatible markdown string with YAML frontmatter.
    """
    now = datetime.utcnow()
    today = now.date()
    severity = _highest_severity(enrichments)

    frontmatter = _build_frontmatter(ioc, severity, enrichments, analysis, case_name, today)
    enrichment_section = _build_enrichment_section(enrichments)

    header_lines = [
        f"# IOC: {ioc.value}",
        "",
        f"**Tipo**: {ioc.type.value.upper()}",
        f"**Fecha de análisis**: {now.strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if case_name:
        header_lines.append(f"**Caso**: {case_name}")

    sections: list[str] = [
        frontmatter,
        "",
        "\n".join(header_lines),
        "",
        "## Resultados de enriquecimiento",
        "",
        enrichment_section,
    ]

    if analysis:
        sections += [
            "",
            "## Análisis IA",
            "",
            analysis,
        ]

    sections += [
        "",
        "---",
        "*Generado por Centinela — Heimdall Security*",
    ]

    return "\n".join(sections)


def save_obsidian_note(content: str, output_dir: str, ioc_value: str) -> str:
    """Save an Obsidian note to disk.

    Args:
        content: The full markdown content to write.
        output_dir: Directory where the note will be saved.
        ioc_value: Raw IOC value used to derive the filename.

    Returns:
        Absolute path to the saved file as a string.
    """
    safe_name = re.sub(r"[.:]", "-", ioc_value)
    # Strip any remaining filesystem-unsafe characters
    safe_name = re.sub(r'[<>"/\\|?*]', "_", safe_name)

    dest = Path(output_dir).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    file_path = dest / f"{safe_name}.md"
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)
