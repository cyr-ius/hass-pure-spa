"""Select entity of the Pure spa (temperature unit)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PureSpaConfigEntry, PureSpaCoordinator
from .entity import PureSpaEntity

PARALLEL_UPDATES = 1

CELSIUS = "celsius"
FAHRENHEIT = "fahrenheit"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PureSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the select entity."""
    async_add_entities([PureSpaTemperatureUnit(entry.runtime_data)])


class PureSpaTemperatureUnit(PureSpaEntity, SelectEntity):
    """Temperature unit shown on the spa control panel."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "temperature_unit"
    _attr_options = [CELSIUS, FAHRENHEIT]

    def __init__(self, coordinator: PureSpaCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, "temperature_unit")

    @property
    def current_option(self) -> str:
        """Return the unit of the spa."""
        return FAHRENHEIT if self.coordinator.data.fahrenheit else CELSIUS

    async def async_select_option(self, option: str) -> None:
        """Switch the spa unit, keeping the target temperature."""
        await self.coordinator.async_set_unit(option == FAHRENHEIT)
