"""Actions of the Pure spa integration (timers)."""

from __future__ import annotations

from datetime import timedelta

import voluptuous as vol
from espspapy import Device
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import PureSpaConfigEntry

SERVICE_SET_TIMER = "set_timer"
SERVICE_CLEAR_TIMER = "clear_timer"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DEVICE = "device"
ATTR_HOURS = "hours"
ATTR_DELAY = "delay"

TIMER_DEVICES = {
    "filter": Device.FILTER,
    "heater": Device.HEATER,
    "sanitizer": Device.SANITIZER,
}

BASE_SCHEMA = {
    vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required(ATTR_DEVICE): vol.In(TIMER_DEVICES),
}
SET_TIMER_SCHEMA = vol.Schema(
    {
        **BASE_SCHEMA,
        vol.Required(ATTR_HOURS): vol.All(vol.Coerce(int), vol.Range(min=1, max=48)),
        vol.Optional(ATTR_DELAY, default=timedelta()): cv.positive_time_period,
        vol.Optional(ATTR_TEMPERATURE): vol.Coerce(int),
    }
)
CLEAR_TIMER_SCHEMA = vol.Schema(BASE_SCHEMA)


def _get_entry(hass: HomeAssistant, call: ServiceCall) -> PureSpaConfigEntry:
    """Return the loaded config entry targeted by an action."""
    entry_id: str = call.data[ATTR_CONFIG_ENTRY_ID]
    entry: PureSpaConfigEntry | None = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found",
            translation_placeholders={"entry_id": entry_id},
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
            translation_placeholders={"entry_id": entry_id},
        )
    return entry


async def _async_set_timer(call: ServiceCall) -> None:
    """Run the filter, heater or sanitizer for some hours, now or later."""
    entry = _get_entry(call.hass, call)
    device = TIMER_DEVICES[call.data[ATTR_DEVICE]]
    temperature: int | None = call.data.get(ATTR_TEMPERATURE)
    if temperature is not None and device is not Device.HEATER:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="temperature_heater_only"
        )
    await entry.runtime_data.async_set_timer(
        device, call.data[ATTR_HOURS], call.data[ATTR_DELAY], temperature
    )


async def _async_clear_timer(call: ServiceCall) -> None:
    """Clear the timers of the filter, heater or sanitizer."""
    entry = _get_entry(call.hass, call)
    await entry.runtime_data.async_clear_timer(TIMER_DEVICES[call.data[ATTR_DEVICE]])


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions of the integration."""
    hass.services.async_register(
        DOMAIN, SERVICE_SET_TIMER, _async_set_timer, schema=SET_TIMER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_TIMER, _async_clear_timer, schema=CLEAR_TIMER_SCHEMA
    )
