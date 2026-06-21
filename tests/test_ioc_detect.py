from __future__ import annotations

import pytest

from centinela.ioc_detect import detect_ioc
from centinela.models import IOCType


class TestIPv4Detection:
    def test_valid_ipv4(self) -> None:
        result = detect_ioc("192.168.1.1")
        assert result is not None
        assert result.type == IOCType.ipv4
        assert result.value == "192.168.1.1"

    def test_valid_ipv4_zeros(self) -> None:
        result = detect_ioc("0.0.0.0")
        assert result is not None
        assert result.type == IOCType.ipv4

    def test_valid_ipv4_max(self) -> None:
        result = detect_ioc("255.255.255.255")
        assert result is not None
        assert result.type == IOCType.ipv4

    def test_invalid_ipv4_octet_too_high(self) -> None:
        result = detect_ioc("256.0.0.1")
        assert result is None or result.type != IOCType.ipv4

    def test_invalid_ipv4_all_octets_too_high(self) -> None:
        result = detect_ioc("999.999.999.999")
        assert result is None or result.type != IOCType.ipv4

    def test_malicious_ip(self) -> None:
        result = detect_ioc("45.142.212.100")
        assert result is not None
        assert result.type == IOCType.ipv4


class TestIPv6Detection:
    def test_full_ipv6(self) -> None:
        result = detect_ioc("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert result is not None
        assert result.type == IOCType.ipv6

    def test_compressed_ipv6(self) -> None:
        result = detect_ioc("2001:db8::1")
        assert result is not None
        assert result.type == IOCType.ipv6

    def test_loopback_ipv6(self) -> None:
        result = detect_ioc("::1")
        assert result is not None
        assert result.type == IOCType.ipv6


class TestDomainDetection:
    def test_simple_domain(self) -> None:
        result = detect_ioc("evil.com")
        assert result is not None
        assert result.type == IOCType.domain

    def test_subdomain(self) -> None:
        result = detect_ioc("malware.evil.com")
        assert result is not None
        assert result.type == IOCType.domain

    def test_domain_with_long_tld(self) -> None:
        result = detect_ioc("example.museum")
        assert result is not None
        assert result.type == IOCType.domain

    def test_ip_not_detected_as_domain(self) -> None:
        result = detect_ioc("192.168.1.1")
        assert result is not None
        assert result.type == IOCType.ipv4

    def test_no_tld_not_a_domain(self) -> None:
        result = detect_ioc("notadomain")
        assert result is None

    def test_single_label_not_a_domain(self) -> None:
        result = detect_ioc("localhost")
        assert result is None


class TestURLDetection:
    def test_http_url(self) -> None:
        result = detect_ioc("http://evil.com/malware.exe")
        assert result is not None
        assert result.type == IOCType.url

    def test_https_url(self) -> None:
        result = detect_ioc("https://phishing.example.com/login")
        assert result is not None
        assert result.type == IOCType.url

    def test_url_takes_priority_over_domain(self) -> None:
        result = detect_ioc("https://evil.com")
        assert result is not None
        assert result.type == IOCType.url


class TestHashDetection:
    def test_md5_hash(self) -> None:
        result = detect_ioc("44d88612fea8a8f36de82e1278abb02f")
        assert result is not None
        assert result.type == IOCType.hash_md5

    def test_md5_not_domain(self) -> None:
        """A 32-char hex string must be MD5, never treated as domain."""
        result = detect_ioc("44d88612fea8a8f36de82e1278abb02f")
        assert result is not None
        assert result.type == IOCType.hash_md5
        assert result.type != IOCType.domain

    def test_sha1_hash(self) -> None:
        result = detect_ioc("3395856ce81f2b7382dee72602f798b642f14d40")
        assert result is not None
        assert result.type == IOCType.hash_sha1

    def test_sha256_hash(self) -> None:
        result = detect_ioc(
            "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
        )
        assert result is not None
        assert result.type == IOCType.hash_sha256

    def test_sha256_takes_priority_over_sha1_and_md5(self) -> None:
        # 64-char hex string must be SHA256
        value = "a" * 64
        result = detect_ioc(value)
        assert result is not None
        assert result.type == IOCType.hash_sha256

    def test_sha1_takes_priority_over_md5(self) -> None:
        # 40-char hex string must be SHA1
        value = "b" * 40
        result = detect_ioc(value)
        assert result is not None
        assert result.type == IOCType.hash_sha1

    def test_uppercase_md5(self) -> None:
        result = detect_ioc("44D88612FEA8A8F36DE82E1278ABB02F")
        assert result is not None
        assert result.type == IOCType.hash_md5

    def test_not_a_hash_too_short(self) -> None:
        result = detect_ioc("44d88612fea8a8f")
        assert result is None

    def test_not_a_hash_non_hex_chars(self) -> None:
        result = detect_ioc("44d88612fea8a8f36de82e1278abb0zz")
        assert result is None


class TestEmailDetection:
    def test_simple_email(self) -> None:
        result = detect_ioc("attacker@evil.com")
        assert result is not None
        assert result.type == IOCType.email

    def test_email_with_plus(self) -> None:
        result = detect_ioc("user+tag@example.org")
        assert result is not None
        assert result.type == IOCType.email

    def test_email_not_domain(self) -> None:
        result = detect_ioc("user@domain.com")
        assert result is not None
        assert result.type == IOCType.email

    def test_invalid_email_no_at(self) -> None:
        result = detect_ioc("notanemail.com")
        assert result is None or result.type != IOCType.email


class TestGarbageInput:
    def test_empty_string(self) -> None:
        result = detect_ioc("")
        assert result is None

    def test_random_text(self) -> None:
        result = detect_ioc("this is not an ioc at all")
        assert result is None

    def test_special_characters(self) -> None:
        result = detect_ioc("!@#$%^&*()")
        assert result is None

    def test_whitespace_stripped(self) -> None:
        result = detect_ioc("  evil.com  ")
        assert result is not None
        assert result.type == IOCType.domain
        assert result.value == "evil.com"

    def test_partial_ip(self) -> None:
        result = detect_ioc("192.168.1")
        assert result is None

    def test_number_only(self) -> None:
        result = detect_ioc("12345")
        assert result is None


class TestDetectionOrder:
    def test_url_before_domain(self) -> None:
        result = detect_ioc("http://192.168.1.1/path")
        assert result is not None
        assert result.type == IOCType.url

    def test_email_before_domain(self) -> None:
        result = detect_ioc("admin@example.com")
        assert result is not None
        assert result.type == IOCType.email

    def test_sha256_before_sha1_and_md5(self) -> None:
        value = "f" * 64
        result = detect_ioc(value)
        assert result is not None
        assert result.type == IOCType.hash_sha256

    def test_ip_before_domain(self) -> None:
        # An IP like "1.2.3.4" must not be parsed as domain
        result = detect_ioc("8.8.8.8")
        assert result is not None
        assert result.type == IOCType.ipv4


class TestPhoneDetection:
    def test_argentina_mobile(self) -> None:
        result = detect_ioc("+54 9 2954 123456")
        assert result is not None
        assert result.type == IOCType.phone
        assert result.value == "+54 9 2954 123456"

    def test_argentina_local_with_parens(self) -> None:
        # Area code must be 1-4 digits within parentheses per the regex
        result = detect_ioc("+54 (0295) 4123456")
        assert result is not None
        assert result.type == IOCType.phone

    def test_us_format(self) -> None:
        result = detect_ioc("+1-555-123-4567")
        assert result is not None
        assert result.type == IOCType.phone

    def test_international_with_spaces(self) -> None:
        result = detect_ioc("+44 20 7946 0958")
        assert result is not None
        assert result.type == IOCType.phone

    def test_no_plus_prefix_not_phone(self) -> None:
        result = detect_ioc("2954123456")
        assert result is None or result.type != IOCType.phone

    def test_phone_not_confused_with_ip(self) -> None:
        result = detect_ioc("192.168.1.1")
        assert result is not None
        assert result.type == IOCType.ipv4
        assert result.type != IOCType.phone

    def test_email_still_detected_as_email(self) -> None:
        result = detect_ioc("test@example.com")
        assert result is not None
        assert result.type == IOCType.email
