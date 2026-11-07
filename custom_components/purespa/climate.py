"""Climate entity of the Pure spa (heater and target temperature)."""

from __future__ import annotations

from typing import Any

from espspapy import Device
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PureSpaConfigEntry, PureSpaCoordinator
from .entity import PureSpaEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PureSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    async_add_entities([PureSpaClimate(entry.runtime_data)])


class PureSpaClimate(PureSpaEntity, ClimateEntity):
    """Spa heater."""

    _attr_name = None
    _attr_translation_key = "spa"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1

    def __init__(self, coordinator: PureSpaCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, "climate")

    @property
    def temperature_unit(self) -> str:
        """Return the unit used by the spa."""
        if self.coordinator.data.fahrenheit:
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature."""
        return self.coordinator.data.temperature_range[0]

    @property
    def max_temp(self) -> float:
        """Return the maximum target temperature."""
        return self.coordinator.data.temperature_range[1]

    @property
    def current_temperature(self) -> float | None:
        """Return the water temperature."""
        return self.coordinator.data.current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self.coordinator.data.target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the heater mode."""
        return HVACMode.HEAT if self.coordinator.data.heater else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        """Return the heater activity."""
        status = self.coordinator.data
        if status.heating:
            return HVACAction.HEATING
        return HVACAction.IDLE if status.heater else HVACAction.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        await self.coordinator.async_set_temperature(round(kwargs[ATTR_TEMPERATURE]))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Switch the heater on or off."""
        await self.coordinator.async_set_device(
            Device.HEATER, hvac_mode == HVACMode.HEAT
        )

    async def async_turn_on(self) -> None:
        """Switch the heater on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Switch the heater off."""
        await self.async_set_hvac_mode(HVACMode.OFF)
