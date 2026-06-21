"""AI analysis module — delegates to configured LLM provider."""

from __future__ import annotations

import json
import logging

from lupe.config import Settings
from lupe.models import IOC, EnrichmentResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Sos un analista de ciberinteligencia senior. Analizá los resultados de enriquecimiento de este IOC y proporcioná:

1. **Puntuación de riesgo**: 0 a 10 (0 = benigno, 10 = amenaza crítica confirmada)
2. **Técnicas MITRE ATT&CK** asociadas (si aplican)
3. **Evaluación**: resumen de la amenaza en 2-3 oraciones
4. **Acciones recomendadas**: qué hacer con este IOC

Respondé en español. Sé directo y conciso.\
"""


def _build_user_message(ioc: IOC, enrichments: list[EnrichmentResult]) -> str:
    """Serialize IOC and enrichment results into a structured text for the LLM."""
    lines: list[str] = [
        f"IOC: {ioc.value}",
        f"Tipo: {ioc.type.value}",
        "",
        "Resultados de enriquecimiento:",
    ]
    for result in enrichments:
        lines.append(
            f"- [{result.source}] Severidad: {result.severity.value} | {result.summary}"
        )

    # Include raw data summary (capped to keep the prompt lean)
    lines.append("")
    lines.append("Datos adicionales (JSON):")
    for result in enrichments:
        try:
            raw_str = json.dumps(result.raw_data, ensure_ascii=False)
            # Truncate very long payloads to avoid context overflow
            if len(raw_str) > 800:
                raw_str = raw_str[:800] + "..."
            lines.append(f"  {result.source}: {raw_str}")
        except (TypeError, ValueError):
            pass

    return "\n".join(lines)


async def analyze_ioc(
    ioc: IOC,
    enrichments: list[EnrichmentResult],
    settings: Settings,
) -> str | None:
    """Request an AI analysis of the IOC enrichment results.

    Uses the configured LLM provider (via ``LUPE_LLM_PROVIDER``).
    Returns None when:
    - No enrichments are available
    - No provider is configured (empty llm_provider)
    - The provider fails or returns an empty response
    """
    if not enrichments:
        return None

    # Lazy import to avoid circular dependency at module load time
    from lupe.llm.registry import get_provider

    provider = get_provider(settings.llm_provider, settings)

    if provider.name == "null":
        logger.debug("No LLM provider configured — skipping AI analysis")
        return None

    prompt = _build_user_message(ioc, enrichments)

    try:
        result = await provider.generate(prompt, system=_SYSTEM_PROMPT)
    except Exception:
        logger.warning("LLM provider %r failed during generate()", provider.name, exc_info=True)
        return None

    return result if result else None
