"""The Pure spa integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, HEARTBEAT_INTERVAL, PLATFORMS
from .coordinator import PureSpaConfigEntry, PureSpaCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions of the integration."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PureSpaConfigEntry) -> bool:
    """Set the config entry up."""
    coordinator = PureSpaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(
        async_track_time_interval(hass, coordinator.async_heartbeat, HEARTBEAT_INTERVAL)
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PureSpaConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.client.async_close()
    return unload_ok
