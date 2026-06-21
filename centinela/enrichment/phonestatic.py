from __future__ import annotations

import httpx
import phonenumbers
from phonenumbers import geocoder, carrier as pn_carrier
from datetime import datetime, timezone

from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity


class PhoneStaticPlugin(EnrichmentPlugin):
    name = "phone_static"
    supported_ioc_types: set[IOCType] = {IOCType.phone}
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        try:
            parsed = phonenumbers.parse(ioc.value, None)
        except phonenumbers.NumberParseException:
            return None

        is_valid = phonenumbers.is_valid_number(parsed)
        country = geocoder.description_for_number(parsed, "es") or "Desconocido"
        carrier_name = pn_carrier.name_for_number(parsed, "es") or "N/A"
        number_type = phonenumbers.number_type(parsed)
        international_fmt = phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )

        type_map = {
            phonenumbers.PhoneNumberType.MOBILE: "móvil",
            phonenumbers.PhoneNumberType.FIXED_LINE: "fijo",
            phonenumbers.PhoneNumberType.VOIP: "VOIP",
            phonenumbers.PhoneNumberType.TOLL_FREE: "0800",
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fijo/móvil",
        }
        line_type = type_map.get(number_type, "desconocido")
        severity = Severity.info if is_valid else Severity.low

        summary = (
            f"Formato: {international_fmt} | País: {country} | "
            f"Tipo: {line_type} | Operadora: {carrier_name} | "
            f"Válido: {is_valid}"
        )
        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data={
                "valid": is_valid,
                "country": country,
                "carrier": carrier_name,
                "line_type": line_type,
                "international_format": international_fmt,
                "national_number": str(parsed.national_number),
                "country_code": parsed.country_code,
            },
            enriched_at=datetime.now(tz=timezone.utc),
        )
