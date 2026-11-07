"""Tests for the Pure spa setup and coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from espspapy import SpaConnectionError
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.purespa.const import HEARTBEAT_INTERVAL, SCAN_INTERVAL

from .conftest import setup_integration


async def test_setup_and_unload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the entry is set up and unloaded."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_spa.async_close.assert_awaited_once()


async def test_setup_retry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the setup is retried when the spa does not answer."""
    mock_spa.async_get_status.side_effect = SpaConnectionError("boom")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_heartbeat_and_update_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_spa: MagicMock
) -> None:
    """Test the heartbeat and the unavailability on update failure."""
    await setup_integration(hass, mock_config_entry)

    async_fire_time_changed(hass, dt_util.utcnow() + HEARTBEAT_INTERVAL)
    await hass.async_block_till_done()
    mock_spa.async_heartbeat.assert_awaited()

    mock_spa.async_get_status.side_effect = SpaConnectionError("boom")
    async_fire_time_changed(
        hass, dt_util.utcnow() + SCAN_INTERVAL + timedelta(seconds=60)
    )
    await hass.async_block_till_done()
    assert hass.states.get("climate.pure_spa").state == "unavailable"
