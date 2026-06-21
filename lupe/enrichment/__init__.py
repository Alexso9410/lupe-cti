from __future__ import annotations

import asyncio

import httpx

from lupe.config import Settings
from lupe.enrichment.abuseipdb import AbuseIPDBPlugin
from lupe.enrichment.base import EnrichmentPlugin
from lupe.enrichment.blocklist_de import BlocklistDePlugin
from lupe.enrichment.censys import CensysPlugin
from lupe.enrichment.certsh import CertShPlugin
from lupe.enrichment.circl_hashlookup import CIRCLHashlookupPlugin
from lupe.enrichment.crtsh import CrtShPlugin
from lupe.enrichment.emailrep import EmailRepPlugin
from lupe.enrichment.google_safebrowsing import GoogleSafeBrowsingPlugin
from lupe.enrichment.greynoise import GreyNoisePlugin
from lupe.enrichment.hibp import HaveIBeenPwnedPlugin
from lupe.enrichment.holehe import HolehePlugin
from lupe.enrichment.hybrid_analysis import HybridAnalysisPlugin
from lupe.enrichment.ipinfo import IpInfoPlugin
from lupe.enrichment.ipqs import IPQSPhonePlugin, IPQSPlugin
from lupe.enrichment.ipquery import IPQueryPlugin
from lupe.enrichment.malwarebazaar import MalwareBazaarPlugin
from lupe.enrichment.numverify import NumVerifyPlugin
from lupe.enrichment.otx import OTXPlugin
from lupe.enrichment.phishtank import PhishTankPlugin
from lupe.enrichment.phonestatic import PhoneStaticPlugin
from lupe.enrichment.pulsedive import PulsedivePlugin
from lupe.enrichment.shodan import ShodanPlugin
from lupe.enrichment.spamhaus import SpamhausPlugin
from lupe.enrichment.threatfox import ThreatFoxPlugin
from lupe.enrichment.urlhaus import URLhausPlugin
from lupe.enrichment.urlscan import URLScanPlugin
from lupe.enrichment.virustotal import VirusTotalPlugin
from lupe.enrichment.whats_my_name import WhatsMyNamePlugin
from lupe.enrichment.whois_plugin import WhoisPlugin
from lupe.models import IOC, EnrichmentResult

_CONCURRENCY_LIMIT = 5


def _build_plugins(settings: Settings) -> list[EnrichmentPlugin]:
    """Return the plugin list, including keyed plugins only when their key is set."""
    plugins: list[EnrichmentPlugin] = [
        WhoisPlugin(),
        IpInfoPlugin(),
        ThreatFoxPlugin(),
        URLhausPlugin(),
        MalwareBazaarPlugin(),
        PhoneStaticPlugin(),
        WhatsMyNamePlugin(),
        IPQueryPlugin(),
        CertShPlugin(),
        CIRCLHashlookupPlugin(),
        HolehePlugin(),
        BlocklistDePlugin(),
        CrtShPlugin(),
    ]

    # EmailRep: siempre activo (funciona sin key con cuota baja)
    if settings.emailrep_key:
        plugins.append(EmailRepPlugin(api_key=settings.emailrep_key))
    else:
        plugins.append(EmailRepPlugin())

    if settings.googlesb_key:
        plugins.append(GoogleSafeBrowsingPlugin(api_key=settings.googlesb_key))

    if settings.phishtank_key:
        plugins.append(PhishTankPlugin(api_key=settings.phishtank_key))

    if settings.pulsedive_key:
        plugins.append(PulsedivePlugin(api_key=settings.pulsedive_key))

    if settings.abuseipdb_key:
        plugins.append(AbuseIPDBPlugin(api_key=settings.abuseipdb_key))

    if settings.virustotal_key:
        plugins.append(VirusTotalPlugin(api_key=settings.virustotal_key))

    if settings.shodan_key:
        plugins.append(ShodanPlugin(api_key=settings.shodan_key))

    if settings.otx_key:
        plugins.append(OTXPlugin(api_key=settings.otx_key))

    if settings.urlscan_key:
        plugins.append(URLScanPlugin(api_key=settings.urlscan_key))

    if settings.hibp_key:
        plugins.append(HaveIBeenPwnedPlugin(api_key=settings.hibp_key))

    if settings.greynoise_key:
        plugins.append(GreyNoisePlugin(api_key=settings.greynoise_key))

    if settings.ipqs_key:
        plugins.append(IPQSPlugin(api_key=settings.ipqs_key))
        plugins.append(IPQSPhonePlugin(api_key=settings.ipqs_key))

    if settings.numverify_key:
        plugins.append(NumVerifyPlugin(api_key=settings.numverify_key))

    if settings.spamhaus_key:
        plugins.append(SpamhausPlugin(api_key=settings.spamhaus_key))

    if settings.hybrid_analysis_key:
        plugins.append(HybridAnalysisPlugin(api_key=settings.hybrid_analysis_key))

    if settings.censys_id and settings.censys_secret:
        plugins.append(
            CensysPlugin(censys_id=settings.censys_id, censys_secret=settings.censys_secret)
        )

    return plugins


async def run_enrichment(ioc: IOC, settings: Settings) -> list[EnrichmentResult]:
    """Run all compatible plugins against an IOC in parallel."""
    plugins = _build_plugins(settings)
    compatible = [p for p in plugins if p.supports(ioc.type)]

    semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)

    async def _run_one(plugin: EnrichmentPlugin) -> EnrichmentResult | None:
        async with semaphore:
            async with httpx.AsyncClient() as client:
                try:
                    return await plugin.enrich(ioc, client)
                except Exception:
                    return None

    results = await asyncio.gather(*(_run_one(p) for p in compatible))
    return [r for r in results if r is not None]
