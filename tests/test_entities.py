"""Tests for the Pure spa entities."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from espspapy import CommandError, Device, SpaStatus, TimerSlot
from homeassistant.components.climate import (
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    ATTR_UNIT_OF_MEASUREMENT,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.purespa.const import DOMAIN

from .conftest import STATUS, UID, setup_integration

CLIMATE = "climate.pure_spa"


async def test_entities_created(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test all the entities and the device are created."""
    await setup_integration(hass, mock_config_entry)

    entities = er.async_entries_for_config_entry(
        er.async_get(hass), mock_config_entry.entry_id
    )
    assert len(entities) == 13
    assert {e.unique_id for e in entities} >= {f"{UID}_climate", f"{UID}_power"}

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, UID), mock_config_entry.entry_id
    )
    assert device is not None
    assert device.serial_number == UID
    assert device.connections


async def test_climate(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the climate state and commands."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(CLIMATE)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING
    assert state.attributes[ATTR_TEMPERATURE] == 37
    assert state.attributes["current_temperature"] == 30
    assert state.attributes[ATTR_MIN_TEMP] == STATUS.temperature_range[0]
    assert state.attributes[ATTR_MAX_TEMP] == STATUS.temperature_range[1]

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: CLIMATE, ATTR_TEMPERATURE: 35.4},
        blocking=True,
    )
    mock_spa.async_set_temperature.assert_awaited_once_with(35)
    assert hass.states.get(CLIMATE).attributes[ATTR_TEMPERATURE] == 35

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: CLIMATE, ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    mock_spa.async_set_device.assert_awaited_with(Device.HEATER, False)

    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: CLIMATE}, blocking=True
    )
    mock_spa.async_set_device.assert_awaited_with(Device.HEATER, False)
    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: CLIMATE}, blocking=True
    )
    mock_spa.async_set_device.assert_awaited_with(Device.HEATER, True)


@pytest.mark.parametrize(
    ("status", "mode", "action"),
    [
        (replace(STATUS, heating=False), HVACMode.HEAT, HVACAction.IDLE),
        (replace(STATUS, heating=False, heater=False), HVACMode.OFF, HVACAction.OFF),
        # Water at the target: the spa may heat or not.
        (replace(STATUS, heating=None), HVACMode.HEAT, None),
    ],
)
async def test_climate_hvac_action(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spa: MagicMock,
    mode: HVACMode,
    action: HVACAction | None,
) -> None:
    """Test the heater activity."""
    await setup_integration(hass, mock_config_entry)
    state = hass.states.get(CLIMATE)
    assert state.state == mode
    assert state.attributes.get(ATTR_HVAC_ACTION) == action


@pytest.mark.parametrize(
    "status",
    [
        replace(
            STATUS,
            fahrenheit=True,
            current_temperature=86,
            target_temperature=99,
            error_code="E90",
        )
    ],
)
async def test_fahrenheit_and_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spa: MagicMock,
    status: SpaStatus,
) -> None:
    """Test a spa set to Fahrenheit with an error."""
    await setup_integration(hass, mock_config_entry)

    # Home Assistant converts to its own unit system (metric).
    assert float(hass.states.get(CLIMATE).attributes[ATTR_TEMPERATURE]) == 37.2
    water = hass.states.get("sensor.pure_spa_water_temperature")
    assert water.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert float(water.state) == 30
    assert hass.states.get("sensor.pure_spa_error").state == "e90"


async def test_sensors(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the sensor values."""
    await setup_integration(hass, mock_config_entry)

    water = hass.states.get("sensor.pure_spa_water_temperature")
    assert water.state == "30"
    assert water.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS
    assert hass.states.get("sensor.pure_spa_error").state == "none"
    assert float(hass.states.get("sensor.pure_spa_filter_timer").state) == 12
    assert hass.states.get("sensor.pure_spa_heater_delayed_start").state == "unknown"
    heater = hass.states.get("sensor.pure_spa_heater_timer")
    assert heater.attributes["scheduled_start"] is None


@pytest.mark.parametrize("status", [replace(STATUS, heater_delay_hours=3.0)])
async def test_scheduled_timer_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the delayed start and the timers set from Home Assistant."""
    start = datetime(2026, 11, 9, 7, 0, tzinfo=UTC)
    later = TimerSlot(start + timedelta(hours=12), 2)
    mock_spa.scheduled_timers = {Device.HEATER: (later, TimerSlot(start, 3, 38))}
    await setup_integration(hass, mock_config_entry)

    assert float(hass.states.get("sensor.pure_spa_heater_delayed_start").state) == 3
    heater = hass.states.get("sensor.pure_spa_heater_timer")
    assert heater.attributes["scheduled_start"] == start
    assert heater.attributes["scheduled_end"] == start + timedelta(hours=3)
    assert (
        hass.states.get("sensor.pure_spa_filter_timer").attributes["scheduled_start"]
        is None
    )


async def test_switches(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the switch states and commands."""
    await setup_integration(hass, mock_config_entry)

    assert hass.states.get("switch.pure_spa_power").state == STATE_ON
    assert hass.states.get("switch.pure_spa_jets").state == STATE_OFF

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.pure_spa_jets"},
        blocking=True,
    )
    mock_spa.async_set_device.assert_awaited_with(Device.JETS, True)
    assert hass.states.get("switch.pure_spa_jets").state == STATE_ON

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.pure_spa_power"},
        blocking=True,
    )
    mock_spa.async_set_device.assert_awaited_with(Device.POWER, False)
    assert hass.states.get("switch.pure_spa_power").state == STATE_OFF


async def test_command_errors(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test a failing command raises an error."""
    await setup_integration(hass, mock_config_entry)
    mock_spa.async_set_device.side_effect = CommandError("boom")
    mock_spa.async_set_temperature.side_effect = CommandError("boom")

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: "switch.pure_spa_jets"},
            blocking=True,
        )
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: CLIMATE, ATTR_TEMPERATURE: 36},
            blocking=True,
        )


async def test_temperature_unit(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the temperature unit select."""
    await setup_integration(hass, mock_config_entry)
    entity_id = "select.pure_spa_temperature_unit"
    assert hass.states.get(entity_id).state == "celsius"

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: "fahrenheit"},
        blocking=True,
    )
    mock_spa.async_set_unit.assert_awaited_once_with(True)
    assert hass.states.get(entity_id).state == "fahrenheit"
