from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class IOCType(str, Enum):
    ipv4 = "ipv4"
    ipv6 = "ipv6"
    domain = "domain"
    url = "url"
    hash_md5 = "hash_md5"
    hash_sha1 = "hash_sha1"
    hash_sha256 = "hash_sha256"
    email = "email"
    phone = "phone"
    username = "username"


class Severity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IOC(BaseModel):
    type: IOCType
    value: str


class EnrichmentResult(BaseModel):
    source: str
    ioc_value: str
    severity: Severity
    summary: str
    raw_data: dict
    enriched_at: datetime


class EmailHeaders(BaseModel):
    from_addr: str
    to_addr: list[str]
    subject: str
    date: str
    reply_to: str | None = None
    message_id: str | None = None
    x_mailer: str | None = None


class ReceivedHop(BaseModel):
    raw: str
    from_host: str | None = None
    by_host: str | None = None
    timestamp: str | None = None
    country_code: str | None = None
    is_suspicious: bool = False


class EmailAuthResults(BaseModel):
    spf: str   # "pass" | "fail" | "softfail" | "neutral" | "none" | "permerror"
    dkim: str  # "pass" | "fail" | "none"
    dmarc: str # "pass" | "fail" | "none"
    spf_domain: str | None = None
    dkim_domain: str | None = None


class AttachmentInfo(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    is_executable: bool


class PhishingScore(BaseModel):
    total: float
    indicators: list[str]
    breakdown: dict[str, float]


class EmailAnalysisResult(BaseModel):
    file_path: str
    file_sha256: str
    headers: EmailHeaders
    auth: EmailAuthResults
    received_chain: list[ReceivedHop]
    body_text: str
    attachments: list[AttachmentInfo]
    iocs_found: list[IOC]
    enrichments: dict[str, list[EnrichmentResult]]
    phishing_score: PhishingScore
    ai_classification: str | None = None
    ai_techniques: list[str] = []
    ai_confidence: float | None = None
    ai_recommendations: list[str] = []
    ai_raw_response: str | None = None
    analyzed_at: datetime
