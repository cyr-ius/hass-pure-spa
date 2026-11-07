"""Fixtures for the Pure spa tests."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from espspapy import SpaInfo, SpaStatus
from homeassistant.const import CONF_HOST, CONF_MAC
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.purespa.const import CONF_UID, DOMAIN

HOST = "192.168.1.50"
UID = "SPA123456"
MAC = "aa:bb:cc:dd:ee:ff"

STATUS = SpaStatus(
    power=True,
    filter=True,
    heater=True,
    heating=True,
    jets=False,
    bubbles=False,
    sanitizer=False,
    fahrenheit=False,
    current_temperature=30,
    target_temperature=37,
    error_code=None,
    filter_hours=12.0,
    sanitizer_hours=3.0,
    heater_hours=5.0,
    raw="",
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable the custom integration in every test."""


@pytest.fixture
def status() -> SpaStatus:
    """Return the default spa status."""
    return STATUS


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Pure spa",
        unique_id=UID,
        data={CONF_HOST: HOST, CONF_UID: UID, CONF_MAC: MAC},
    )


@pytest.fixture
def mock_spa(status: SpaStatus) -> Generator[MagicMock]:
    """Mock the Spa client used by the coordinator."""
    with patch("custom_components.purespa.coordinator.Spa", autospec=True) as spa_cls:
        client = spa_cls.return_value
        client.async_get_status = AsyncMock(return_value=status)
        client.async_heartbeat = AsyncMock()
        client.async_close = AsyncMock()

        async def _set_device(device, on):
            return replace(status, **{device.name.lower(): on})

        async def _set_temperature(value):
            return replace(status, target_temperature=value)

        client.async_set_device = AsyncMock(side_effect=_set_device)
        client.async_set_temperature = AsyncMock(side_effect=_set_temperature)
        yield client


@pytest.fixture
def mock_identify() -> Generator[AsyncMock]:
    """Mock the spa identification used by the config flow."""
    with patch(
        "custom_components.purespa.config_flow.async_identify",
        return_value=SpaInfo(uid=UID, ip=HOST),
    ) as identify:
        yield identify


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Do not set the entry up during config flow tests."""
    with (
        patch(
            "custom_components.purespa.async_setup_entry", return_value=True
        ) as setup,
        patch("custom_components.purespa.async_unload_entry", return_value=True),
    ):
        yield setup


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set the integration up."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
