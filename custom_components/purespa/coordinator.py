"""Pure spa coordinator."""

from __future__ import annotations

import logging
from datetime import datetime

from espspapy import Device, Spa, SpaException, SpaStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type PureSpaConfigEntry = ConfigEntry[PureSpaCoordinator]


class PureSpaCoordinator(DataUpdateCoordinator[SpaStatus]):
    """Poll the spa status over a persistent connection."""

    config_entry: PureSpaConfigEntry

    def __init__(self, hass: HomeAssistant, entry: PureSpaConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        # The heartbeat is scheduled by Home Assistant (see __init__).
        self.client = Spa(entry.data[CONF_HOST], heartbeat_interval=None)

    async def _async_update_data(self) -> SpaStatus:
        try:
            return await self.client.async_get_status()
        except SpaException as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_heartbeat(self, _now: datetime) -> None:
        """Keep the TCP connection alive."""
        await self.client.async_heartbeat()

    async def async_set_device(self, device: Device, on: bool) -> None:
        """Switch a device on or off."""
        try:
            status = await self.client.async_set_device(device, on)
        except SpaException as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        self.async_set_updated_data(status)

    async def async_set_temperature(self, value: int) -> None:
        """Set the target temperature."""
        try:
            status = await self.client.async_set_temperature(value)
        except SpaException as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        self.async_set_updated_data(status)
