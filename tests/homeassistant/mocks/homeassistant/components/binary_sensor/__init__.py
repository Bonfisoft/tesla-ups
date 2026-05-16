"""Mock Home Assistant binary_sensor component."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any, Optional


class BinarySensorDeviceClass(str, Enum):
    """Mock BinarySensorDeviceClass."""
    BATTERY = "battery"
    BATTERY_CHARGING = "battery_charging"
    POWER = "power"
    PLUG = "plug"
    CONNECTIVITY = "connectivity"
    DOOR = "door"
    WINDOW = "window"
    MOTION = "motion"
    OCCUPANCY = "occupancy"
    PRESENCE = "presence"


@dataclass
class BinarySensorEntityDescription:
    """Mock BinarySensorEntityDescription."""
    key: str
    name: str
    device_class: Optional[BinarySensorDeviceClass] = None
    icon: Optional[str] = None
    icon_on: Optional[str] = None
    entity_registry_enabled_default: bool = True
    is_on_fn: Optional[Callable[[Any], bool]] = None


class BinarySensorEntity:
    """Mock BinarySensorEntity base class."""
    
    entity_description: BinarySensorEntityDescription
    _attr_has_entity_name: bool = True
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[dict] = None
    _attr_is_on: Optional[bool] = None
    
    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._attr_is_on
    
    @property
    def unique_id(self):
        """Return unique id."""
        return self._attr_unique_id
    
    @property
    def device_info(self):
        """Return device info."""
        return self._attr_device_info
    
    @property
    def device_class(self):
        """Return device class."""
        return self.entity_description.device_class if self.entity_description else None
    
    @property
    def available(self):
        """Return availability."""
        return True
