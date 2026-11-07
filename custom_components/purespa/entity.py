"""Base entity for the Pure spa integration."""

from __future__ import annotations

from homeassistant.const import CONF_MAC
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_UID, DOMAIN
from .coordinator import PureSpaCoordinator


class PureSpaEntity(CoordinatorEntity[PureSpaCoordinator]):
    """Pure spa entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PureSpaCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        data = coordinator.config_entry.data
        uid: str = data[CONF_UID]
        self._attr_unique_id = f"{uid}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            connections=(
                {(CONNECTION_NETWORK_MAC, data[CONF_MAC])}
                if data.get(CONF_MAC)
                else set()
            ),
            model="PureSpa",
            serial_number=uid,
            name=coordinator.config_entry.title,
        )
