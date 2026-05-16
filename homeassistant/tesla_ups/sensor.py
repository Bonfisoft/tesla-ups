"""Sensors for Tesla Powerwall UPS Bridge integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# These imports require Home Assistant environment
from homeassistant.components.sensor import (  # type: ignore
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.const import PERCENTAGE  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .const import (
    DOMAIN,
    GRID_CONNECTED,
    GRID_DOWN,
    MANUFACTURER,
    MODEL,
    SENSOR_BATTERY,
    SENSOR_GRID_STATE,
    SENSOR_LAST_NOTIFICATION,
    SENSOR_LAST_UPDATE,
    SENSOR_PROVIDER,
    SENSOR_STATUS,
    STATUS_LOW_BATTERY,
    STATUS_ON_BATTERY,
    STATUS_ONLINE,
)
from .coordinator import TeslaUPSDataUpdateCoordinator


@dataclass
class TeslaUPSSensorEntityDescription(SensorEntityDescription):
    """Entity description for Tesla UPS sensors."""

    value_fn: callable[[dict[str, Any]], Any] | None = None


SENSOR_DESCRIPTIONS: tuple[TeslaUPSSensorEntityDescription, ...] = (
    TeslaUPSSensorEntityDescription(
        key=SENSOR_BATTERY,
        name="Battery Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("soe", 0.0),
    ),
    TeslaUPSSensorEntityDescription(
        key=SENSOR_STATUS,
        name="UPS Status",
        icon="mdi:power-plug",
        value_fn=lambda data: data.get("status", "UNKNOWN"),
    ),
    TeslaUPSSensorEntityDescription(
        key=SENSOR_GRID_STATE,
        name="Grid State",
        icon="mdi:transmission-tower",
        value_fn=lambda data: data.get("grid", "Unknown"),
    ),
    TeslaUPSSensorEntityDescription(
        key=SENSOR_LAST_NOTIFICATION,
        name="Last Notification",
        icon="mdi:email-send",
        value_fn=lambda data: data.get("last_notified", "Never"),
    ),
    TeslaUPSSensorEntityDescription(
        key=SENSOR_PROVIDER,
        name="Provider",
        entity_registry_enabled_default=False,
        icon="mdi:information",
        value_fn=lambda data: data.get("provider", "unknown"),
    ),
    TeslaUPSSensorEntityDescription(
        key=SENSOR_LAST_UPDATE,
        name="Last Update",
        entity_registry_enabled_default=False,
        icon="mdi:clock-outline",
        value_fn=lambda data: data.get("last_update", None),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla UPS sensors from a config entry."""
    coordinator: TeslaUPSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for description in SENSOR_DESCRIPTIONS:
        entities.append(TeslaUPSSensor(coordinator, description, entry))

    async_add_entities(entities)


class TeslaUPSSensor(CoordinatorEntity[TeslaUPSDataUpdateCoordinator], SensorEntity):
    """Representation of a Tesla UPS sensor."""

    entity_description: TeslaUPSSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TeslaUPSDataUpdateCoordinator,
        description: TeslaUPSSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None

        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return None

    @property
    def icon(self) -> str | None:
        """Return dynamic icon based on state."""
        # Dynamic icon for UPS status
        if self.entity_description.key == SENSOR_STATUS:
            status = self.native_value
            if status == STATUS_ONLINE:
                return "mdi:power-plug"
            elif status == STATUS_ON_BATTERY:
                return "mdi:battery"
            elif status == STATUS_LOW_BATTERY:
                return "mdi:battery-alert"
            return "mdi:power-plug-off"

        # Dynamic icon for grid state
        if self.entity_description.key == SENSOR_GRID_STATE:
            grid = self.native_value
            if grid == GRID_CONNECTED:
                return "mdi:transmission-tower"
            elif grid == GRID_DOWN:
                return "mdi:transmission-tower-off"

        return self.entity_description.icon

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
