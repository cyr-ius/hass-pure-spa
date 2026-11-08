"""Pure spa coordinator."""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from datetime import datetime, timedelta

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

    async def _async_command(self, command: Awaitable[SpaStatus]) -> None:
        """Run a command and publish the status it returns."""
        try:
            status = await command
        except (SpaException, ValueError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        self.async_set_updated_data(status)

    async def async_set_device(self, device: Device, on: bool) -> None:
        """Switch a device on or off."""
        await self._async_command(self.client.async_set_device(device, on))

    async def async_set_temperature(self, value: int) -> None:
        """Set the target temperature."""
        await self._async_command(self.client.async_set_temperature(value))

    async def async_set_timer(
        self,
        device: Device,
        hours: int,
        delay: timedelta,
        temperature: int | None = None,
    ) -> None:
        """Run the filter, heater or sanitizer for some hours, now or later."""
        if device is Device.HEATER:
            command = self.client.async_set_heater_timer(hours, delay, temperature)
        elif device is Device.FILTER:
            command = self.client.async_set_filter_timer(hours, delay)
        else:
            command = self.client.async_set_sanitizer_timer(hours, delay)
        await self._async_command(command)

    async def async_clear_timer(self, device: Device) -> None:
        """Clear the timers of the filter, heater or sanitizer."""
        await self._async_command(self.client.async_clear_timer(device))
