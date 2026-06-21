from __future__ import annotations

import json

import httpx

from centinela.config import Settings
from centinela.models import IOC, EnrichmentResult

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
    """Request an AI analysis of the IOC enrichment results via Ollama.

    Args:
        ioc: The IOC being analysed.
        enrichments: List of enrichment results already gathered.
        settings: Application settings (contains Ollama URL and model name).

    Returns:
        The model's text response, or None if Ollama is unavailable or
        returns an error.
    """
    if not enrichments:
        return None

    url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(ioc, enrichments)},
        ],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=120.0)
    except httpx.ConnectError:
        # Ollama not running — silent skip
        return None
    except httpx.RequestError:
        return None

    if response.status_code != 200:
        return None

    try:
        data: dict = response.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        return None
