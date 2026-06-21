from __future__ import annotations

from datetime import datetime, timezone

import httpx

from centinela.enrichment.base import EnrichmentPlugin
from centinela.models import IOC, IOCType, EnrichmentResult, Severity

_IPQS_URL = "https://ipqualityscore.com/api/json/ip/"


def _fraud_score_to_severity(score: int, active_tor: bool = False, active_vpn: bool = False) -> Severity:
    """Convert fraud score to severity, considering active VPN/TOR status."""
    # Calculate base severity from score
    if score >= 85:
        base_severity = Severity.critical
    elif score >= 75:
        base_severity = Severity.high
    elif score >= 50:
        base_severity = Severity.medium
    else:
        base_severity = Severity.info

    # Apply TOR/VPN severity adjustments
    if active_tor:
        # Active TOR: minimum severity is high
        if score < 75:
            return Severity.high
        return Severity.critical

    if active_vpn:
        # Active VPN: take max of score-based severity and medium
        severity_order = {Severity.info: 0, Severity.low: 1, Severity.medium: 2, Severity.high: 3, Severity.critical: 4}
        if severity_order[base_severity] < severity_order[Severity.medium]:
            return Severity.medium

    return base_severity


class IPQSPlugin(EnrichmentPlugin):
    name = "ipqs"
    supported_ioc_types: set[IOCType] = {IOCType.ipv4, IOCType.ipv6}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(
        self, ioc: IOC, client: httpx.AsyncClient
    ) -> EnrichmentResult | None:
        """Query IPQualityScore for IP fraud score and proxy/VPN detection."""
        try:
            response = await client.get(
                f"{_IPQS_URL}{self._api_key}/{ioc.value}",
                timeout=15.0,
            )
        except httpx.RequestError:
            return None

        if response.status_code != 200:
            return None

        data: dict = response.json()

        if data.get("success") is not True:
            return None

        fraud_score = data.get("fraud_score", 0)
        vpn = data.get("vpn", False)
        tor = data.get("tor", False)
        proxy = data.get("proxy", False)
        bot_status = data.get("bot_status", False)
        recent_abuse = data.get("recent_abuse", False)
        country_code = data.get("country_code", "N/A")
        isp = data.get("ISP", "N/A")
        host = data.get("host")

        # New fields from API response
        active_vpn = data.get("active_vpn", False)
        active_tor = data.get("active_tor", False)
        connection_type = data.get("connection_type", "unknown")
        abuse_velocity = data.get("abuse_velocity", "none")
        is_crawler = data.get("is_crawler", False)
        mobile = data.get("mobile", False)
        organization = data.get("organization", isp)  # fallback to ISP
        asn = data.get("ASN")

        severity = _fraud_score_to_severity(fraud_score, active_tor, active_vpn)

        summary = (
            f"IPQS: score={fraud_score} | {connection_type} | {country_code}/{organization}\n"
            f"Flags: vpn={active_vpn}, tor={active_tor}, proxy={proxy}, bot={bot_status}, crawler={is_crawler}\n"
            f"Abuso: velocity={abuse_velocity}, recent={recent_abuse} | ASN={asn}"
        )

        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data=data,
            enriched_at=datetime.now(tz=timezone.utc),
        )


_IPQS_PHONE_URL = "https://www.ipqualityscore.com/api/json/phone/"


def _phone_fraud_score_to_severity(score: int, valid: bool) -> Severity:
    if not valid:
        return Severity.low
    if score >= 85:
        return Severity.critical
    if score >= 75:
        return Severity.high
    if score >= 50:
        return Severity.medium
    return Severity.info


class IPQSPhonePlugin(EnrichmentPlugin):
    name = "ipqs_phone"
    supported_ioc_types: set[IOCType] = {IOCType.phone}
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        import urllib.parse
        import phonenumbers

        try:
            parsed = phonenumbers.parse(ioc.value, None)
            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except Exception:
            e164 = ioc.value

        encoded = urllib.parse.quote(e164, safe="")
        try:
            response = await client.get(
                f"{_IPQS_PHONE_URL}{self._api_key}/{encoded}",
                timeout=15.0,
            )
        except httpx.RequestError:
            return None
        if response.status_code != 200:
            return None
        data: dict = response.json()
        if data.get("success") is not True:
            return None

        fraud_score = data.get("fraud_score", 0)
        valid = data.get("valid", False)
        active = data.get("active", False)
        line_type = data.get("line_type", "unknown")
        carrier = data.get("carrier", "N/A")
        country = data.get("country", "N/A")
        city = data.get("city", "")
        risky = data.get("risky", False)
        recent_abuse = data.get("recent_abuse", False)
        do_not_call = data.get("do_not_call", False)
        leaked = data.get("leaked", False)

        severity = _phone_fraud_score_to_severity(fraud_score, valid)
        location = f"{country}/{city}" if city else country
        summary = (
            f"IPQS Phone: score={fraud_score} | {line_type} | {carrier} | {location}"
            f"\nFlags: valid={valid}, active={active}, risky={risky}, "
            f"abuse={recent_abuse}, dnc={do_not_call}, leaked={leaked}"
        )
        return EnrichmentResult(
            source=self.name,
            ioc_value=ioc.value,
            severity=severity,
            summary=summary,
            raw_data=data,
            enriched_at=datetime.now(tz=timezone.utc),
        )
