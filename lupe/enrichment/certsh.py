from __future__ import annotations
from datetime import datetime, timezone
import httpx
from lupe.enrichment.base import EnrichmentPlugin
from lupe.models import IOC, IOCType, EnrichmentResult, Severity

class CertShPlugin(EnrichmentPlugin):
    name = "certsh"
    supported_ioc_types: set[IOCType] = {IOCType.domain}
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        try:
            resp = await client.get(
                f"https://crt.sh/?q={ioc.value}&output=json",
                timeout=20.0
            )
            resp.raise_for_status()
            certs = resp.json()
            if not isinstance(certs, list):
                return None
        except Exception:
            return None

        now = datetime.now(tz=timezone.utc)
        subdomains = set()
        active_count = 0
        total = len(certs)

        for cert in certs:
            name_value = cert.get("name_value", "")
            for name in name_value.split("\n"):
                name = name.strip()
                if name and name != ioc.value:
                    subdomains.add(name)

            not_after_str = cert.get("not_after", "")
            if not_after_str:
                try:
                    # Handle typical crt.sh format: "YYYY-MM-DD HH:MM:SS"
                    not_after = datetime.strptime(not_after_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    if not_after > now:
                        active_count += 1
                except (ValueError, TypeError):
                    pass

        severity = Severity.medium if active_count > 0 else Severity.info

        subdomains_list = sorted(subdomains)
        extra = f" (+{len(subdomains_list) - 5} más)" if len(subdomains_list) > 5 else ""
        subdomains_str = ", ".join(subdomains_list[:5]) + extra if subdomains_list else "ninguno"

        summary = f"crt.sh: {total} certs | {active_count} activos | subdominios: {subdomains_str}"

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data={
                "total_certs": total,
                "active_certs": active_count,
                "subdomains": subdomains_list,
            },
            enriched_at=datetime.now(tz=timezone.utc),
        )
