"""Mock Home Assistant sensor component."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any, Optional


class SensorDeviceClass(str, Enum):
    """Mock SensorDeviceClass."""
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    POWER = "power"
    ENERGY = "energy"
    VOLTAGE = "voltage"
    CURRENT = "current"


class SensorStateClass(str, Enum):
    """Mock SensorStateClass."""
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"


@dataclass
class SensorEntityDescription:
    """Mock SensorEntityDescription."""
    key: str
    name: str
    native_unit_of_measurement: Optional[str] = None
    device_class: Optional[SensorDeviceClass] = None
    state_class: Optional[SensorStateClass] = None
    icon: Optional[str] = None
    entity_registry_enabled_default: bool = True
    value_fn: Optional[Callable[[Any], Any]] = None


class SensorEntity:
    """Mock SensorEntity base class."""
    
    entity_description: SensorEntityDescription
    _attr_has_entity_name: bool = True
    _attr_unique_id: Optional[str] = None
    _attr_device_info: Optional[dict] = None
    _attr_native_value: Any = None
    
    @property
    def native_value(self):
        """Return the native value."""
        return self._attr_native_value
    
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
    def state_class(self):
        """Return state class."""
        return self.entity_description.state_class if self.entity_description else None
    
    @property
    def available(self):
        """Return availability."""
        return True
