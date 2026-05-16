"""Binary sensors for Tesla Powerwall UPS Bridge integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# These imports require Home Assistant environment
from homeassistant.components.binary_sensor import (  # type: ignore
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .const import (
    BINARY_LOW_BATTERY,
    BINARY_ON_BATTERY,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    STATUS_LOW_BATTERY,
    STATUS_ON_BATTERY,
)
from .coordinator import TeslaUPSDataUpdateCoordinator


@dataclass
class TeslaUPSBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Entity description for Tesla UPS binary sensors."""

    is_on_fn: callable[[dict[str, Any]], bool] | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[TeslaUPSBinarySensorEntityDescription, ...] = (
    TeslaUPSBinarySensorEntityDescription(
        key=BINARY_ON_BATTERY,
        name="On Battery",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug-off",
        icon_on="mdi:battery",
        is_on_fn=lambda data: data.get("status", "") in (STATUS_ON_BATTERY, STATUS_LOW_BATTERY),
    ),
    TeslaUPSBinarySensorEntityDescription(
        key=BINARY_LOW_BATTERY,
        name="Low Battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        icon="mdi:battery",
        icon_on="mdi:battery-alert",
        is_on_fn=lambda data: data.get("status", "") == STATUS_LOW_BATTERY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla UPS binary sensors from a config entry."""
    coordinator: TeslaUPSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for description in BINARY_SENSOR_DESCRIPTIONS:
        entities.append(TeslaUPSBinarySensor(coordinator, description, entry))

    async_add_entities(entities)


class TeslaUPSBinarySensor(CoordinatorEntity[TeslaUPSDataUpdateCoordinator], BinarySensorEntity):
    """Representation of a Tesla UPS binary sensor."""

    entity_description: TeslaUPSBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TeslaUPSDataUpdateCoordinator,
        description: TeslaUPSBinarySensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry

        # Unique ID based on entry ID and sensor key
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Tesla Powerwall UPS Bridge",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data is None:
            return None

        if self.entity_description.is_on_fn:
            return self.entity_description.is_on_fn(self.coordinator.data)
        return None

    @property
    def icon(self) -> str | None:
        """Return dynamic icon based on state."""
        if self.is_on and hasattr(self.entity_description, "icon_on"):
            return self.entity_description.icon_on
        return self.entity_description.icon

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
