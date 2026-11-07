"""Sensors of the Pure spa."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from espspapy import SpaStatus
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import PureSpaConfigEntry, PureSpaCoordinator
from .entity import PureSpaEntity

PARALLEL_UPDATES = 0

ERROR_CODES = [
    "none",
    "e81",
    "e90",
    "e91",
    "e92",
    "e94",
    "e95",
    "e96",
    "e97",
    "e99",
    "end",
]


@dataclass(frozen=True, kw_only=True)
class PureSpaSensorEntityDescription(SensorEntityDescription):
    """Pure spa sensor description."""

    value_fn: Callable[[SpaStatus], StateType]


SENSORS: tuple[PureSpaSensorEntityDescription, ...] = (
    PureSpaSensorEntityDescription(
        key="water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda status: status.current_temperature,
    ),
    PureSpaSensorEntityDescription(
        key="error",
        device_class=SensorDeviceClass.ENUM,
        options=ERROR_CODES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda status: (status.error_code or "none").lower(),
    ),
    PureSpaSensorEntityDescription(
        key="filter_timer",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda status: status.filter_hours,
    ),
    PureSpaSensorEntityDescription(
        key="sanitizer_timer",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda status: status.sanitizer_hours,
    ),
    PureSpaSensorEntityDescription(
        key="heater_timer",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda status: status.heater_hours,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PureSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    async_add_entities(
        PureSpaSensor(entry.runtime_data, description) for description in SENSORS
    )


class PureSpaSensor(PureSpaEntity, SensorEntity):
    """Spa sensor."""

    entity_description: PureSpaSensorEntityDescription

    def __init__(
        self,
        coordinator: PureSpaCoordinator,
        description: PureSpaSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.key

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit, following the spa temperature unit."""
        if self.entity_description.device_class == SensorDeviceClass.TEMPERATURE:
            if self.coordinator.data.fahrenheit:
                return UnitOfTemperature.FAHRENHEIT
            return UnitOfTemperature.CELSIUS
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
