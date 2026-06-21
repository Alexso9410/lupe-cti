from __future__ import annotations

import httpx
import pytest

from lupe.enrichment.phonestatic import PhoneStaticPlugin
from lupe.models import IOC, IOCType, Severity


class TestPhoneStaticPlugin:
    def test_supports_only_phone(self) -> None:
        plugin = PhoneStaticPlugin()
        assert plugin.supported_ioc_types == {IOCType.phone}

    @pytest.mark.asyncio
    async def test_valid_argentina_mobile(self) -> None:
        plugin = PhoneStaticPlugin()
        ioc = IOC(type=IOCType.phone, value="+54 9 11 5555 5555")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.source == "phone_static"
        assert result.raw_data["valid"] is True
        assert result.severity == Severity.info
        assert "Argentina" in result.raw_data["country"] or result.raw_data["country_code"] == 54

    @pytest.mark.asyncio
    async def test_invalid_number_returns_low_severity(self) -> None:
        plugin = PhoneStaticPlugin()
        ioc = IOC(type=IOCType.phone, value="+54 9 2954 123456")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.raw_data["valid"] is False
        assert result.severity == Severity.low

    @pytest.mark.asyncio
    async def test_unparseable_number_returns_none(self) -> None:
        plugin = PhoneStaticPlugin()
        ioc = IOC(type=IOCType.phone, value="not-a-phone-number")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is None

    @pytest.mark.asyncio
    async def test_us_number(self) -> None:
        plugin = PhoneStaticPlugin()
        ioc = IOC(type=IOCType.phone, value="+1 202 555 0173")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        assert result.raw_data["country_code"] == 1

    @pytest.mark.asyncio
    async def test_result_has_required_fields(self) -> None:
        plugin = PhoneStaticPlugin()
        ioc = IOC(type=IOCType.phone, value="+54 9 11 5555 5555")

        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)

        assert result is not None
        raw = result.raw_data
        assert "valid" in raw
        assert "country" in raw
        assert "line_type" in raw
        assert "carrier" in raw
        assert "international_format" in raw
