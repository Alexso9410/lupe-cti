import pytest
import respx
import httpx
from centinela.enrichment.circl_hashlookup import CIRCLHashlookupPlugin
from centinela.models import IOC, IOCType, Severity

class TestCIRCLHashlookupPlugin:
    @pytest.fixture
    def plugin(self):
        return CIRCLHashlookupPlugin()

    @pytest.fixture
    def md5_ioc(self):
        return IOC(type=IOCType.hash_md5, value="d41d8cd98f00b204e9800998ecf8427e")

    @pytest.fixture
    def sha256_ioc(self):
        return IOC(type=IOCType.hash_sha256, value="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    @respx.mock
    async def test_known_malicious(self, plugin, md5_ioc):
        respx.get(f"https://hashlookup.circl.lu/lookup/md5/{md5_ioc.value}").mock(
            return_value=httpx.Response(200, json={
                "KnownMalicious": "true",
                "FileName": "malware.exe",
                "FileSize": "12345",
                "SHA-256": md5_ioc.value,
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(md5_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical
        assert "MALICIOSO" in result.summary
        assert "malware.exe" in result.summary

    @respx.mock
    async def test_benign_hash(self, plugin, md5_ioc):
        respx.get(f"https://hashlookup.circl.lu/lookup/md5/{md5_ioc.value}").mock(
            return_value=httpx.Response(200, json={
                "KnownMalicious": "false",
                "FileName": "notepad.exe",
                "FileSize": "54321",
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(md5_ioc, client)
        assert result is not None
        assert result.severity == Severity.info
        assert "benigno" in result.summary

    @respx.mock
    async def test_returns_none_on_404(self, plugin, md5_ioc):
        respx.get(f"https://hashlookup.circl.lu/lookup/md5/{md5_ioc.value}").mock(
            return_value=httpx.Response(404)
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(md5_ioc, client)
        assert result is None

    @respx.mock
    async def test_returns_none_on_500(self, plugin, md5_ioc):
        respx.get(f"https://hashlookup.circl.lu/lookup/md5/{md5_ioc.value}").mock(
            return_value=httpx.Response(500)
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(md5_ioc, client)
        assert result is None

    @respx.mock
    async def test_sha256_endpoint(self, plugin, sha256_ioc):
        respx.get(f"https://hashlookup.circl.lu/lookup/sha256/{sha256_ioc.value}").mock(
            return_value=httpx.Response(200, json={
                "KnownMalicious": "true",
                "FileName": "evil.dll",
                "FileSize": "99999",
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(sha256_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical

    @respx.mock
    async def test_malicious_boolean(self, plugin, md5_ioc):
        """Test when KnownMalicious is a boolean instead of string"""
        respx.get(f"https://hashlookup.circl.lu/lookup/md5/{md5_ioc.value}").mock(
            return_value=httpx.Response(200, json={
                "KnownMalicious": True,
                "FileName": "trojan.exe",
                "FileSize": "777",
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(md5_ioc, client)
        assert result is not None
        assert result.severity == Severity.critical
        assert "MALICIOSO" in result.summary

    @respx.mock
    async def test_unknown_field_defaults_to_medium(self, plugin, md5_ioc):
        """When KnownMalicious is absent, severity should be medium"""
        respx.get(f"https://hashlookup.circl.lu/lookup/md5/{md5_ioc.value}").mock(
            return_value=httpx.Response(200, json={
                "FileName": "unknown.exe",
                "FileSize": "100",
            })
        )
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(md5_ioc, client)
        assert result is not None
        assert result.severity == Severity.medium
