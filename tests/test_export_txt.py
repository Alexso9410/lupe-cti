"""Tests for TXT export formatter."""

from __future__ import annotations

import pytest

from lupe.export.txt_export import export_case_to_txt, export_ioc_to_txt


@pytest.fixture
def sample_history():
    """A minimal CaseHistory dict for testing."""
    return {
        "case": {
            "id": 1,
            "name": "Incident-2026-001",
            "description": "Phishing investigation",
            "status": "open",
            "created_at": "2026-07-06 10:00:00",
        },
        "iocs": [
            {
                "ioc": {
                    "id": 1,
                    "type": "ipv4",
                    "value": "8.8.8.8",
                    "added_at": "2026-07-06 10:00:00",
                },
                "events": [
                    {
                        "event_type": "enrichment",
                        "timestamp": "2026-07-06 10:01:00",
                        "description": "[virustotal] 8.8.8.8: Clean IP",
                        "detail": "info",
                        "source": "virustotal",
                        "severity": "info",
                        "summary": "Clean IP",
                    },
                    {
                        "event_type": "analysis",
                        "timestamp": "2026-07-06 10:02:00",
                        "description": "AI analysis by gemini-2.5-flash",
                        "model": "gemini-2.5-flash",
                        "summary": "This IP is benign. No threats detected.",
                    },
                ],
            },
            {
                "ioc": {
                    "id": 2,
                    "type": "domain",
                    "value": "evil.com",
                    "added_at": "2026-07-06 10:03:00",
                },
                "events": [
                    {
                        "event_type": "enrichment",
                        "timestamp": "2026-07-06 10:04:00",
                        "description": "[urlhaus] evil.com: Malware distribution",
                        "detail": "high",
                        "source": "urlhaus",
                        "severity": "high",
                        "summary": "Malware distribution",
                    },
                    {
                        "event_type": "analysis",
                        "timestamp": "2026-07-06 10:05:00",
                        "description": "AI analysis by gemini-2.5-flash",
                        "model": "gemini-2.5-flash",
                        "summary": "Malicious domain distributing malware.",
                    },
                ],
            },
        ],
        "case_notes": [
            {
                "id": 1,
                "content": "Escalated to IR team.",
                "created_at": "2026-07-06 10:10:00",
            }
        ],
        "stats": {
            "ioc_count": 2,
            "enrichment_count": 2,
            "analysis_count": 2,
            "top_severity": "high",
        },
    }


class TestCaseExportTxt:
    """Test export_case_to_txt output structure."""

    def test_executive_summary_section(self, sample_history):
        """TXT should start with executive summary header."""
        result = export_case_to_txt(sample_history)
        assert "EXECUTIVE SUMMARY" in result
        assert "Incident-2026-001" in result
        assert "Phishing investigation" in result

    def test_executive_summary_has_stats(self, sample_history):
        """Executive summary should include IOC count and stats."""
        result = export_case_to_txt(sample_history)
        assert "2" in result  # IOC count
        assert "high" in result.lower()  # top severity

    def test_ioc_grouped_sections(self, sample_history):
        """TXT should have per-IOC sections."""
        result = export_case_to_txt(sample_history)
        assert "8.8.8.8" in result
        assert "evil.com" in result

    def test_enrichment_detail_included(self, sample_history):
        """TXT should include full enrichment details."""
        result = export_case_to_txt(sample_history)
        assert "virustotal" in result
        assert "urlhaus" in result
        assert "Clean IP" in result
        assert "Malware distribution" in result

    def test_analysis_full_text_included(self, sample_history):
        """TXT should include full AI analysis text (not truncated)."""
        result = export_case_to_txt(sample_history)
        assert "This IP is benign. No threats detected." in result
        assert "Malicious domain distributing malware." in result

    def test_case_notes_included(self, sample_history):
        """TXT should include case notes."""
        result = export_case_to_txt(sample_history)
        assert "Escalated to IR team." in result

    def test_empty_case(self):
        """TXT should handle empty case gracefully."""
        history = {
            "case": {
                "id": 1, "name": "Empty Case", "description": "",
                "status": "open", "created_at": "2026-01-01",
            },
            "iocs": [],
            "case_notes": [],
            "stats": {
                "ioc_count": 0, "enrichment_count": 0,
                "analysis_count": 0, "top_severity": "info",
            },
        }
        result = export_case_to_txt(history)
        assert "Empty Case" in result
        assert "No IOCs" in result


class TestIOCExportTxt:
    """Test export_ioc_to_txt output."""

    def test_single_ioc_export(self, sample_history):
        """export_ioc_to_txt should produce output for one IOC."""
        ioc_data = sample_history["iocs"][0]
        case_info = sample_history["case"]
        result = export_ioc_to_txt(ioc_data, case_info)
        assert "8.8.8.8" in result
        assert "virustotal" in result
        assert "This IP is benign." in result
        # Should NOT include evil.com
        assert "evil.com" not in result

    def test_single_ioc_has_header(self, sample_history):
        """export_ioc_to_txt should have IOC header."""
        ioc_data = sample_history["iocs"][1]
        case_info = sample_history["case"]
        result = export_ioc_to_txt(ioc_data, case_info)
        assert "evil.com" in result
        assert "domain" in result
