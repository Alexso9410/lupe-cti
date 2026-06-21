"""Email parser for phishing analysis module.

This module provides functionality to parse .eml files and extract
security-relevant information for phishing analysis.

Uses only Python stdlib - zero external dependencies.
"""

from __future__ import annotations

import email
import email.header
import email.parser
import email.policy
import hashlib
import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class ParsedHeaders:
    """Extracted email headers relevant for security analysis."""

    from_addr: str
    to_addr: list[str]
    subject: str
    date: str
    reply_to: str | None
    message_id: str | None
    x_mailer: str | None


@dataclass
class ReceivedHop:
    """A single hop in the email delivery chain."""

    raw: str
    from_host: str | None
    by_host: str | None
    timestamp: str | None
    country_code: str | None = None
    is_suspicious: bool = False  # True if private IP embedded in external hop


@dataclass
class AuthResults:
    """Authentication results from SPF, DKIM, and DMARC checks."""

    spf: str  # "pass" | "fail" | "softfail" | "neutral" | "none" | "permerror"
    dkim: str  # "pass" | "fail" | "none"
    dmarc: str  # "pass" | "fail" | "none"
    spf_domain: str | None
    dkim_domain: str | None


@dataclass
class AttachmentInfo:
    """Information about an email attachment."""

    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    is_executable: bool


@dataclass
class ParsedEmail:
    """Complete parsed email structure for phishing analysis."""

    file_path: str
    headers: ParsedHeaders
    auth: AuthResults
    received_chain: list[ReceivedHop]
    body_text: str  # plain text, max 10000 chars
    attachments: list[AttachmentInfo]


# =============================================================================
# Constants
# =============================================================================

# Executable extensions that warrant attention in phishing analysis
EXECUTABLE_EXTENSIONS: set[str] = {
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".ps1",
    ".vbs",
    ".js",
    ".hta",
    ".doc",
    ".docm",
    ".xls",
    ".xlsm",
    ".ppt",
    ".pptm",
    ".zip",
    ".7z",
    ".rar",
    ".iso",
    ".img",
}

# Maximum body text size to store (prevents memory issues with large emails)
MAX_BODY_LENGTH = 10000


# =============================================================================
# Header Extraction
# =============================================================================

def _extract_email_from_header(header_value: str) -> str:
    """Extract email address from a header value.

    Handles formats like:
    - "user@example.com"
    - "Name <user@example.com>"
    - "\"Name\" <user@example.com>"
    """
    if not header_value:
        return ""

    # Try to extract from angle brackets first
    match = re.search(r"<([^>]+)>", header_value)
    if match:
        return match.group(1).strip()

    # Otherwise return the whole string, stripped
    return header_value.strip()


def _decode_header_value(header_value: str) -> str:
    """Decode an email header value, handling encoded words.

    Handles RFC 2047 encoded words like =?UTF-8?B?...?= or =?ISO-8859-1?Q?...?=
    """
    if not header_value:
        return ""

    try:
        decoded_parts = email.header.decode_header(header_value)
        result_parts: list[str] = []

        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result_parts.append(part.decode(charset or "utf-8", errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    # Unknown charset or decode error, try utf-8 with replacement
                    result_parts.append(part.decode("utf-8", errors="replace"))
            else:
                result_parts.append(part)

        return "".join(result_parts)
    except Exception:
        # Fallback: return original if decoding fails
        return header_value


def _extract_headers(msg: email.message.Message) -> ParsedHeaders:
    """Extract relevant headers from an email message.

    Args:
        msg: The email message object to parse.

    Returns:
        ParsedHeaders with extracted and decoded header values.
    """
    try:
        from_addr_raw = msg.get("From", "")
        from_addr = _extract_email_from_header(_decode_header_value(from_addr_raw))
    except Exception:
        from_addr = ""

    try:
        to_addr_raw = msg.get("To", "")
        to_decoded = _decode_header_value(to_addr_raw)
        to_addr = [addr.strip() for addr in to_decoded.split(",") if addr.strip()]
    except Exception:
        to_addr = []

    try:
        subject_raw = msg.get("Subject", "")
        subject = _decode_header_value(subject_raw)
    except Exception:
        subject = ""

    try:
        date = msg.get("Date", "")
    except Exception:
        date = ""

    try:
        reply_to_raw = msg.get("Reply-To")
        reply_to = _decode_header_value(reply_to_raw) if reply_to_raw else None
    except Exception:
        reply_to = None

    try:
        message_id = msg.get("Message-ID")
    except Exception:
        message_id = None

    try:
        x_mailer = msg.get("X-Mailer")
    except Exception:
        x_mailer = None

    return ParsedHeaders(
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        date=date,
        reply_to=reply_to,
        message_id=message_id,
        x_mailer=x_mailer,
    )


# =============================================================================
# Authentication Results Extraction
# =============================================================================

def _extract_auth_results(msg: email.message.Message) -> AuthResults:
    """Extract SPF, DKIM, and DMARC authentication results.

    Searches for Authentication-Results header first, then falls back
    to Received-SPF if needed.

    Args:
        msg: The email message object to parse.

    Returns:
        AuthResults with parsed authentication status.
    """
    spf = "none"
    dkim = "none"
    dmarc = "none"
    spf_domain: str | None = None
    dkim_domain: str | None = None

    # Try Authentication-Results header first
    try:
        auth_results = msg.get("Authentication-Results", "")
        if auth_results:
            # Extract SPF result
            spf_match = re.search(r"spf=(\w+)", auth_results, re.IGNORECASE)
            if spf_match:
                spf = spf_match.group(1).lower()

            # Extract DKIM result
            dkim_match = re.search(r"dkim=(\w+)", auth_results, re.IGNORECASE)
            if dkim_match:
                dkim = dkim_match.group(1).lower()

            # Extract DMARC result
            dmarc_match = re.search(r"dmarc=(\w+)", auth_results, re.IGNORECASE)
            if dmarc_match:
                dmarc = dmarc_match.group(1).lower()

            # Extract SPF domain
            spf_domain_match = re.search(r"smtp\.mailfrom=([^\s;]+)", auth_results, re.IGNORECASE)
            if spf_domain_match:
                spf_domain = spf_domain_match.group(1)

            # Extract DKIM domain
            dkim_domain_match = re.search(r"header\.d=([^\s;]+)", auth_results, re.IGNORECASE)
            if dkim_domain_match:
                dkim_domain = dkim_domain_match.group(1)
    except Exception:
        pass

    # Fallback: Check Received-SPF if SPF not found
    if spf == "none":
        try:
            received_spf = msg.get("Received-SPF", "")
            if received_spf:
                # First word after the colon is typically the result
                spf_match = re.search(r"^\s*(\w+)", received_spf)
                if spf_match:
                    spf = spf_match.group(1).lower()
        except Exception:
            pass

    return AuthResults(
        spf=spf,
        dkim=dkim,
        dmarc=dmarc,
        spf_domain=spf_domain,
        dkim_domain=dkim_domain,
    )


# =============================================================================
# Received Chain Extraction
# =============================================================================

def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address string represents a private address.

    Args:
        ip_str: String that may contain an IP address.

    Returns:
        True if the string contains a valid private IP address.
    """
    # Extract IP from possible hostname:port or other formats
    ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", ip_str)
    if not ip_match:
        return False

    try:
        addr = ipaddress.ip_address(ip_match.group(1))
        return addr.is_private
    except ValueError:
        return False


def _extract_received_chain(msg: email.message.Message) -> list[ReceivedHop]:
    """Extract the chain of MTA hops from Received headers.

    The hops are returned in the order they appear in the headers,
    which is typically most recent first.

    Args:
        msg: The email message object to parse.

    Returns:
        List of ReceivedHop objects with parsed hop information.
    """
    hops: list[ReceivedHop] = []

    try:
        received_headers = msg.get_all("Received") or []
    except Exception:
        return hops

    for hop_raw in received_headers:
        try:
            hop_str = hop_raw if isinstance(hop_raw, str) else str(hop_raw)

            # Extract from host
            from_match = re.search(r"from\s+(\S+)", hop_str, re.IGNORECASE)
            from_host = from_match.group(1) if from_match else None

            # Extract by host
            by_match = re.search(r"by\s+(\S+)", hop_str, re.IGNORECASE)
            by_host = by_match.group(1) if by_match else None

            # Extract timestamp (typically after last semicolon)
            timestamp = None
            if ";" in hop_str:
                timestamp = hop_str.split(";")[-1].strip()

            # Check for suspicious private IP in from_host
            is_suspicious = False
            if from_host:
                is_suspicious = _is_private_ip(from_host)

            hops.append(
                ReceivedHop(
                    raw=hop_str,
                    from_host=from_host,
                    by_host=by_host,
                    timestamp=timestamp,
                    is_suspicious=is_suspicious,
                )
            )
        except Exception:
            # Skip malformed hops but continue processing others
            continue

    return hops


# =============================================================================
# Body Extraction
# =============================================================================

def _strip_html_tags(html_text: str) -> str:
    """Strip HTML tags from text and normalize whitespace.

    Args:
        html_text: HTML content to clean.

    Returns:
        Plain text with HTML tags removed and whitespace normalized.
    """
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", html_text)
    # Normalize whitespace (multiple spaces/newlines to single space)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message.

    Prefers text/plain content. Falls back to text/html with tag stripping.
    Returns empty string if no readable body is found.

    Args:
        msg: The email message object to parse.

    Returns:
        Plain text body content, truncated to MAX_BODY_LENGTH.
    """
    text_content: str | None = None
    html_content: str | None = None

    # Walk through all message parts
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = part.get_content_disposition() or ""

        # Skip attachments - only process inline content
        if "attachment" in content_disposition:
            continue

        if content_type == "text/plain":
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text_content = payload.decode(charset, errors="replace")
                    break  # Found plain text, use it
            except Exception:
                continue

        elif content_type == "text/html" and html_content is None:
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html_content = payload.decode(charset, errors="replace")
            except Exception:
                continue

    # Prefer plain text, fall back to HTML
    if text_content:
        return text_content[:MAX_BODY_LENGTH]
    elif html_content:
        stripped = _strip_html_tags(html_content)
        return stripped[:MAX_BODY_LENGTH]

    return ""


# =============================================================================
# Attachment Extraction
# =============================================================================

def _get_filename(part: email.message.Message) -> str:
    """Extract filename from a message part.

    Args:
        part: The MIME message part.

    Returns:
        The filename or "unnamed" if not specified.
    """
    filename = part.get_filename()
    if filename:
        return filename

    # Try Content-Disposition params
    content_disp = part.get("Content-Disposition", "")
    fname_match = re.search(r'filename="?([^";]+)"?', content_disp)
    if fname_match:
        return fname_match.group(1)

    return "unnamed"


def _is_executable_file(filename: str) -> bool:
    """Check if a filename has an executable extension.

    Args:
        filename: The filename to check.

    Returns:
        True if the file extension is in the executable list.
    """
    name_lower = filename.lower()
    for ext in EXECUTABLE_EXTENSIONS:
        if name_lower.endswith(ext):
            return True
    return False


def _extract_attachments(msg: email.message.Message) -> list[AttachmentInfo]:
    """Extract attachment information from email.

    Args:
        msg: The email message object to parse.

    Returns:
        List of AttachmentInfo with metadata and SHA256 hashes.
    """
    attachments: list[AttachmentInfo] = []

    for part in msg.walk():
        try:
            content_disposition = part.get_content_disposition()
            if content_disposition != "attachment":
                continue

            filename = _get_filename(part)
            mime_type = part.get_content_type()

            # Get payload bytes
            payload = part.get_payload(decode=True)
            if payload is None:
                payload = b""

            size_bytes = len(payload)
            sha256_hash = hashlib.sha256(payload).hexdigest()
            is_executable = _is_executable_file(filename)

            attachments.append(
                AttachmentInfo(
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    sha256=sha256_hash,
                    is_executable=is_executable,
                )
            )
        except Exception:
            # Skip malformed attachments but continue processing
            continue

    return attachments


# =============================================================================
# Main Parser
# =============================================================================

def parse_eml(file_path: Path | str) -> ParsedEmail:
    """Parse an .eml file and return complete structure for phishing analysis.

    This function uses email.policy.compat32 for robust parsing of malformed
    emails commonly encountered in phishing samples.

    Args:
        file_path: Path to the .eml file to parse.

    Returns:
        ParsedEmail with all extracted information. Never raises exceptions;
        if parsing fails, returns a structure with error information in body_text.
    """
    path = Path(file_path)

    # Default structures for error case
    default_headers = ParsedHeaders(
        from_addr="",
        to_addr=[],
        subject="",
        date="",
        reply_to=None,
        message_id=None,
        x_mailer=None,
    )
    default_auth = AuthResults(
        spf="none",
        dkim="none",
        dmarc="none",
        spf_domain=None,
        dkim_domain=None,
    )

    try:
        # Read file bytes
        file_bytes = path.read_bytes()

        # Parse with compat32 policy for robust handling of malformed emails
        msg = email.message_from_bytes(file_bytes, policy=email.policy.compat32)

        # Extract all components
        headers = _extract_headers(msg)
        auth = _extract_auth_results(msg)
        received_chain = _extract_received_chain(msg)
        body_text = _extract_body(msg)
        attachments = _extract_attachments(msg)

        return ParsedEmail(
            file_path=str(path.resolve()),
            headers=headers,
            auth=auth,
            received_chain=received_chain,
            body_text=body_text,
            attachments=attachments,
        )

    except FileNotFoundError:
        return ParsedEmail(
            file_path=str(path),
            headers=default_headers,
            auth=default_auth,
            received_chain=[],
            body_text=f"Error: File not found: {path}",
            attachments=[],
        )
    except PermissionError:
        return ParsedEmail(
            file_path=str(path),
            headers=default_headers,
            auth=default_auth,
            received_chain=[],
            body_text=f"Error: Permission denied reading file: {path}",
            attachments=[],
        )
    except Exception as e:
        # Generic error handling - never raise, always return structure
        return ParsedEmail(
            file_path=str(path),
            headers=default_headers,
            auth=default_auth,
            received_chain=[],
            body_text=f"Error parsing email: {type(e).__name__}: {e}",
            attachments=[],
        )
