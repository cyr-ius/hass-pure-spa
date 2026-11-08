"""Tests for the Pure spa actions (timers)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from espspapy import CommandError, Device
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.purespa.const import DOMAIN
from custom_components.purespa.services import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DELAY,
    ATTR_DEVICE,
    ATTR_HOURS,
    SERVICE_CLEAR_TIMER,
    SERVICE_SET_TIMER,
)

from .conftest import setup_integration


async def _call(hass: HomeAssistant, service: str, **data: object) -> None:
    await hass.services.async_call(DOMAIN, service, data, blocking=True)


async def test_set_heater_timer(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Heater in 2 hours for 3 hours at 38 °C."""
    await setup_integration(hass, mock_config_entry)
    await _call(
        hass,
        SERVICE_SET_TIMER,
        **{
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DEVICE: "heater",
            ATTR_HOURS: 3,
            ATTR_DELAY: {"hours": 2},
            ATTR_TEMPERATURE: 38,
        },
    )
    mock_spa.async_set_heater_timer.assert_awaited_once_with(3, timedelta(hours=2), 38)


@pytest.mark.parametrize(
    ("device", "method"),
    [("filter", "async_set_filter_timer"), ("sanitizer", "async_set_sanitizer_timer")],
)
async def test_set_timer_now(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spa: MagicMock,
    device: str,
    method: str,
) -> None:
    """Filter or sanitizer for 4 hours, starting now."""
    await setup_integration(hass, mock_config_entry)
    await _call(
        hass,
        SERVICE_SET_TIMER,
        **{
            ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
            ATTR_DEVICE: device,
            ATTR_HOURS: 4,
        },
    )
    getattr(mock_spa, method).assert_awaited_once_with(4, timedelta())


async def test_clear_timer(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Clear the heater timer."""
    await setup_integration(hass, mock_config_entry)
    await _call(
        hass,
        SERVICE_CLEAR_TIMER,
        **{ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id, ATTR_DEVICE: "heater"},
    )
    mock_spa.async_clear_timer.assert_awaited_once_with(Device.HEATER)


async def test_temperature_heater_only(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """A temperature is refused for the filter."""
    await setup_integration(hass, mock_config_entry)
    with pytest.raises(ServiceValidationError) as err:
        await _call(
            hass,
            SERVICE_SET_TIMER,
            **{
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DEVICE: "filter",
                ATTR_HOURS: 2,
                ATTR_TEMPERATURE: 38,
            },
        )
    assert err.value.translation_key == "temperature_heater_only"
    mock_spa.async_set_filter_timer.assert_not_awaited()


async def test_unknown_and_unloaded_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """The entry must exist and be loaded."""
    await setup_integration(hass, mock_config_entry)
    data = {ATTR_DEVICE: "filter", ATTR_HOURS: 2}
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, SERVICE_SET_TIMER, **data, **{ATTR_CONFIG_ENTRY_ID: "x"})
    assert err.value.translation_key == "entry_not_found"

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    with pytest.raises(ServiceValidationError) as err:
        await _call(
            hass,
            SERVICE_SET_TIMER,
            **data,
            **{ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id},
        )
    assert err.value.translation_key == "entry_not_loaded"


async def test_timer_command_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """A refused command (temperature out of range) is reported."""
    mock_spa.async_set_heater_timer.side_effect = CommandError("out of range")
    await setup_integration(hass, mock_config_entry)
    with pytest.raises(HomeAssistantError) as err:
        await _call(
            hass,
            SERVICE_SET_TIMER,
            **{
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_DEVICE: "heater",
                ATTR_HOURS: 1,
                ATTR_TEMPERATURE: 45,
            },
        )
    assert err.value.translation_key == "command_failed"
