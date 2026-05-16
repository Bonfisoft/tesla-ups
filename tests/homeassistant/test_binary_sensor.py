"""Comprehensive tests for Tesla UPS binary sensor platform."""

import sys
import os

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOMEASSISTANT_DIR = os.path.join(PROJECT_ROOT, "homeassistant")
MOCKS_DIR = os.path.join(os.path.dirname(__file__), "mocks")

# Add mocks directory FIRST (before any real homeassistant imports)
sys.path.insert(0, MOCKS_DIR)

# Add homeassistant directory to path for tesla_ imports
sys.path.insert(0, HOMEASSISTANT_DIR)

from unittest.mock import MagicMock, AsyncMock
import pytest

from tesla_ups.const import (
    BINARY_ON_BATTERY,
    BINARY_LOW_BATTERY,
    STATUS_ONLINE,
    STATUS_ON_BATTERY,
    STATUS_LOW_BATTERY,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from tesla_ups.binary_sensor import (
    TeslaUPSBinarySensor,
    TeslaUPSBinarySensorEntityDescription,
    BINARY_SENSOR_DESCRIPTIONS,
    async_setup_entry,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass


class TestTeslaUPSBinarySensorDescription:
    """Test binary sensor entity descriptions."""
    
    def test_on_battery_description_attributes(self):
        """Test on_battery sensor has correct description attributes."""
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_ON_BATTERY)
        
        assert desc.key == BINARY_ON_BATTERY
        assert desc.name == "On Battery"
        assert desc.device_class == BinarySensorDeviceClass.POWER
        assert desc.icon == "mdi:power-plug-off"
        assert desc.icon_on == "mdi:battery"
    
    def test_low_battery_description_attributes(self):
        """Test low_battery sensor has correct description attributes."""
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_LOW_BATTERY)
        
        assert desc.key == BINARY_LOW_BATTERY
        assert desc.name == "Low Battery"
        assert desc.device_class == BinarySensorDeviceClass.BATTERY
        assert desc.icon == "mdi:battery"
        assert desc.icon_on == "mdi:battery-alert"
    
    def test_on_battery_is_on_fn(self):
        """Test on_battery is_on_fn logic."""
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_ON_BATTERY)
        
        # Should be on for OB status
        assert desc.is_on_fn({"status": STATUS_ON_BATTERY}) is True
        # Should be on for OB LB status
        assert desc.is_on_fn({"status": STATUS_LOW_BATTERY}) is True
        # Should be off for OL status
        assert desc.is_on_fn({"status": STATUS_ONLINE}) is False
    
    def test_low_battery_is_on_fn(self):
        """Test low_battery is_on_fn logic."""
        desc = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == BINARY_LOW_BATTERY)
        
        # Should be on for OB LB status
        assert desc.is_on_fn({"status": STATUS_LOW_BATTERY}) is True
        # Should be off for OB status
        assert desc.is_on_fn({"status": STATUS_ON_BATTERY}) is False
        # Should be off for OL status
        assert desc.is_on_fn({"status": STATUS_ONLINE}) is False


class TestTeslaUPSBinarySensorValues:
    """Test binary sensor value retrieval."""
    
    def test_on_battery_when_online(self):
        """Test on_battery is False when on grid."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ONLINE}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda data: data.get("status", "") in (STATUS_ON_BATTERY, STATUS_LOW_BATTERY),
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.is_on is False
    
    def test_on_battery_when_on_battery(self):
        """Test on_battery is True during outage."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda data: data.get("status", "") in (STATUS_ON_BATTERY, STATUS_LOW_BATTERY),
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.is_on is True
    
    def test_on_battery_when_low_battery(self):
        """Test on_battery is True when low battery."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_LOW_BATTERY}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda data: data.get("status", "") in (STATUS_ON_BATTERY, STATUS_LOW_BATTERY),
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.is_on is True
    
    def test_low_battery_when_normal(self):
        """Test low_battery is False when battery normal."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_LOW_BATTERY,
            name="Low Battery",
            is_on_fn=lambda data: data.get("status", "") == STATUS_LOW_BATTERY,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.is_on is False
    
    def test_low_battery_when_low(self):
        """Test low_battery is True when battery low."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_LOW_BATTERY}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_LOW_BATTERY,
            name="Low Battery",
            is_on_fn=lambda data: data.get("status", "") == STATUS_LOW_BATTERY,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.is_on is True


class TestTeslaUPSBinarySensorDynamicIcons:
    """Test binary sensor dynamic icon behavior."""
    
    def test_on_battery_icon_offline(self):
        """Test on_battery shows battery icon when on battery."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            icon="mdi:power-plug-off",
            icon_on="mdi:battery",
            is_on_fn=lambda data: data.get("status", "") in (STATUS_ON_BATTERY, STATUS_LOW_BATTERY),
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:battery"
    
    def test_on_battery_icon_online(self):
        """Test on_battery shows plug-off icon when on grid."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ONLINE}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            icon="mdi:power-plug-off",
            icon_on="mdi:battery",
            is_on_fn=lambda data: data.get("status", "") in (STATUS_ON_BATTERY, STATUS_LOW_BATTERY),
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:power-plug-off"
    
    def test_low_battery_icon_normal(self):
        """Test low_battery shows battery icon when normal."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ONLINE}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_LOW_BATTERY,
            name="Low Battery",
            icon="mdi:battery",
            icon_on="mdi:battery-alert",
            is_on_fn=lambda data: data.get("status", "") == STATUS_LOW_BATTERY,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:battery"
    
    def test_low_battery_icon_alert(self):
        """Test low_battery shows alert icon when low."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_LOW_BATTERY}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_LOW_BATTERY,
            name="Low Battery",
            icon="mdi:battery",
            icon_on="mdi:battery-alert",
            is_on_fn=lambda data: data.get("status", "") == STATUS_LOW_BATTERY,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:battery-alert"
    
class TestTeslaUPSBinarySensorEntityProperties:
    """Test binary sensor entity properties."""
    
    def test_unique_id_format(self):
        """Test unique ID is formatted correctly."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        entry = MagicMock()
        entry.entry_id = "abc123"
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda d: True,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, entry)
        
        assert sensor.unique_id == "abc123_on_battery"
    
    def test_device_info_structure(self):
        """Test device info has correct structure."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        entry = MagicMock()
        entry.entry_id = "test_entry"
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda d: True,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, entry)
        
        device_info = sensor.device_info
        assert device_info["name"] == "Tesla Powerwall UPS Bridge"
        assert device_info["manufacturer"] == MANUFACTURER
        assert device_info["model"] == MODEL
        assert device_info["sw_version"] == "1.0.0"
        assert device_info["identifiers"] == {(DOMAIN, "test_entry")}
    
    def test_available_when_success(self):
        """Test sensor is available when last update succeeded."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        coordinator.last_update_success = True
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda d: True,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.available is True
    
    def test_not_available_when_failed(self):
        """Test sensor is not available when last update failed."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        coordinator.last_update_success = False
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda d: True,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.available is False
    
    def test_device_class_from_description(self):
        """Test device class is read from description."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            device_class=BinarySensorDeviceClass.POWER,
            is_on_fn=lambda d: True,
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.device_class == BinarySensorDeviceClass.POWER
    
    def test_is_on_none_when_no_data(self):
        """Test is_on is None when coordinator has no data."""
        coordinator = MagicMock()
        coordinator.data = None
        
        desc = TeslaUPSBinarySensorEntityDescription(
            key=BINARY_ON_BATTERY,
            name="On Battery",
            is_on_fn=lambda d: d.get("status") in (STATUS_ON_BATTERY, STATUS_LOW_BATTERY),
        )
        sensor = TeslaUPSBinarySensor(coordinator, desc, MagicMock())
        
        assert sensor.is_on is None


class TestAsyncSetupEntry:
    """Test binary sensor platform setup."""
    
    @pytest.mark.asyncio
    async def test_setup_entry_creates_binary_sensors(self):
        """Test setup entry creates all binary sensor entities."""
        from homeassistant.core import HomeAssistant
        from homeassistant.config_entries import ConfigEntry
        
        hass = HomeAssistant()
        hass.data = {}
        
        entry = ConfigEntry(
            entry_id="test_entry",
            domain="tesla_ups",
            data={"bridge_url": "http://test:8000"},
        )
        
        coordinator = MagicMock()
        coordinator.data = {
            "status": "OL",
            "soe": 85.0,
            "grid": "SystemGridConnected",
        }
        
        hass.data["tesla_ups"] = {entry.entry_id: coordinator}
        
        entities = []
        
        def mock_add_entities(new_entities):
            entities.extend(new_entities)
        
        await async_setup_entry(hass, entry, mock_add_entities)
        
        assert len(entities) == len(BINARY_SENSOR_DESCRIPTIONS)
        
        # Verify all expected binary sensors are created
        keys = [e.entity_description.key for e in entities]
        assert BINARY_ON_BATTERY in keys
        assert BINARY_LOW_BATTERY in keys
