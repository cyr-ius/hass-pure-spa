"""Switches of the Pure spa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from espspapy import Device
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PureSpaConfigEntry, PureSpaCoordinator
from .entity import PureSpaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PureSpaSwitchEntityDescription(SwitchEntityDescription):
    """Pure spa switch description."""

    device: Device


SWITCHES: tuple[PureSpaSwitchEntityDescription, ...] = (
    PureSpaSwitchEntityDescription(key="power", device=Device.POWER),
    PureSpaSwitchEntityDescription(key="filter", device=Device.FILTER),
    PureSpaSwitchEntityDescription(key="jets", device=Device.JETS),
    PureSpaSwitchEntityDescription(key="bubbles", device=Device.BUBBLES),
    PureSpaSwitchEntityDescription(key="sanitizer", device=Device.SANITIZER),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PureSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switches."""
    async_add_entities(
        PureSpaSwitch(entry.runtime_data, description) for description in SWITCHES
    )


class PureSpaSwitch(PureSpaEntity, SwitchEntity):
    """Spa device switch."""

    entity_description: PureSpaSwitchEntityDescription

    def __init__(
        self,
        coordinator: PureSpaCoordinator,
        description: PureSpaSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.key

    @property
    def is_on(self) -> bool:
        """Return True if the device is on."""
        return self.coordinator.data.is_on(self.entity_description.device)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the device on."""
        await self.coordinator.async_set_device(self.entity_description.device, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the device off."""
        await self.coordinator.async_set_device(self.entity_description.device, False)
