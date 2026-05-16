"""Comprehensive tests for Tesla UPS sensor platform."""

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

from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Now we can import from the integration
from tesla_ups.const import (
    SENSOR_BATTERY,
    SENSOR_STATUS,
    SENSOR_GRID_STATE,
    SENSOR_LAST_NOTIFICATION,
    SENSOR_PROVIDER,
    SENSOR_LAST_UPDATE,
    STATUS_ONLINE,
    STATUS_ON_BATTERY,
    STATUS_LOW_BATTERY,
    GRID_CONNECTED,
    GRID_DOWN,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from tesla_ups.sensor import (
    TeslaUPSSensor,
    TeslaUPSSensorEntityDescription,
    SENSOR_DESCRIPTIONS,
    async_setup_entry,
)
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE


class TestTeslaUPSSensorDescription:
    """Test sensor entity descriptions."""
    
    def test_battery_description_attributes(self):
        """Test battery sensor has correct description attributes."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_BATTERY)
        
        assert desc.key == SENSOR_BATTERY
        assert desc.name == "Battery Charge"
        assert desc.native_unit_of_measurement == PERCENTAGE
        assert desc.device_class == SensorDeviceClass.BATTERY
        assert desc.state_class == SensorStateClass.MEASUREMENT
        assert desc.entity_registry_enabled_default is True
    
    def test_status_description_attributes(self):
        """Test status sensor has correct description attributes."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_STATUS)
        
        assert desc.key == SENSOR_STATUS
        assert desc.name == "UPS Status"
        assert desc.icon == "mdi:power-plug"
        assert desc.device_class is None
        assert desc.state_class is None
    
    def test_grid_state_description_attributes(self):
        """Test grid state sensor has correct description attributes."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_GRID_STATE)
        
        assert desc.key == SENSOR_GRID_STATE
        assert desc.name == "Grid State"
        assert desc.icon == "mdi:transmission-tower"
    
    def test_provider_description_disabled_by_default(self):
        """Test provider sensor is disabled by default."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_PROVIDER)
        
        assert desc.key == SENSOR_PROVIDER
        assert desc.entity_registry_enabled_default is False
    
    def test_last_update_description_disabled_by_default(self):
        """Test last update sensor is disabled by default."""
        desc = next(d for d in SENSOR_DESCRIPTIONS if d.key == SENSOR_LAST_UPDATE)
        
        assert desc.key == SENSOR_LAST_UPDATE
        assert desc.entity_registry_enabled_default is False


class TestTeslaUPSSensorValues:
    """Test sensor value retrieval."""
    
    def test_battery_sensor_value_online(self):
        """Test battery sensor returns correct value when online."""
        coordinator = MagicMock()
        coordinator.data = {
            "soe": 85.5,
            "status": "OL",
            "grid": "SystemGridConnected",
        }
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_BATTERY,
            name="Battery Charge",
            value_fn=lambda data: data.get("soe"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == 85.5
    
    def test_battery_sensor_value_on_battery(self):
        """Test battery sensor returns correct value when on battery."""
        coordinator = MagicMock()
        coordinator.data = {
            "soe": 45.0,
            "status": "OB",
            "grid": "GridDown",
        }
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_BATTERY,
            name="Battery Charge",
            value_fn=lambda data: data.get("soe"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == 45.0
    
    def test_status_sensor_value_online(self):
        """Test status sensor returns OL when online."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ONLINE}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_STATUS,
            name="UPS Status",
            value_fn=lambda data: data.get("status"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == STATUS_ONLINE
    
    def test_status_sensor_value_on_battery(self):
        """Test status sensor returns OB when on battery."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_STATUS,
            name="UPS Status",
            value_fn=lambda data: data.get("status"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == STATUS_ON_BATTERY
    
    def test_status_sensor_value_low_battery(self):
        """Test status sensor returns OB LB when low battery."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_LOW_BATTERY}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_STATUS,
            name="UPS Status",
            value_fn=lambda data: data.get("status"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == STATUS_LOW_BATTERY
    
    def test_grid_state_sensor_connected(self):
        """Test grid state sensor when connected."""
        coordinator = MagicMock()
        coordinator.data = {"grid": GRID_CONNECTED}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_GRID_STATE,
            name="Grid State",
            value_fn=lambda data: data.get("grid"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == GRID_CONNECTED
    
    def test_grid_state_sensor_down(self):
        """Test grid state sensor when down."""
        coordinator = MagicMock()
        coordinator.data = {"grid": GRID_DOWN}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_GRID_STATE,
            name="Grid State",
            value_fn=lambda data: data.get("grid"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == GRID_DOWN
    
    def test_last_notification_sensor(self):
        """Test last notification sensor returns timestamp."""
        coordinator = MagicMock()
        coordinator.data = {"last_notified": "14:30:25"}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_LAST_NOTIFICATION,
            name="Last Notification",
            value_fn=lambda data: data.get("last_notified"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == "14:30:25"
    
    def test_provider_sensor(self):
        """Test provider sensor returns provider name."""
        coordinator = MagicMock()
        coordinator.data = {"provider": "Tesla Powerwall"}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_PROVIDER,
            name="Provider",
            value_fn=lambda data: data.get("provider"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == "Tesla Powerwall"
    
    def test_last_update_sensor(self):
        """Test last update sensor returns timestamp."""
        coordinator = MagicMock()
        coordinator.data = {"last_update": "2024-01-15T14:30:00"}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_LAST_UPDATE,
            name="Last Update",
            value_fn=lambda data: data.get("last_update"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value == "2024-01-15T14:30:00"


class TestTeslaUPSSensorDynamicIcons:
    """Test sensor dynamic icon behavior."""
    
    def test_status_icon_online(self):
        """Test status sensor shows plug icon when online."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ONLINE}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_STATUS,
            name="UPS Status",
            icon="mdi:power-plug",
            value_fn=lambda data: data.get("status"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:power-plug"
    
    def test_status_icon_on_battery(self):
        """Test status sensor shows battery icon when on battery."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_ON_BATTERY}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_STATUS,
            name="UPS Status",
            icon="mdi:power-plug",
            value_fn=lambda data: data.get("status"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:battery"
    
    def test_status_icon_low_battery(self):
        """Test status sensor shows alert icon when low battery."""
        coordinator = MagicMock()
        coordinator.data = {"status": STATUS_LOW_BATTERY}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_STATUS,
            name="UPS Status",
            icon="mdi:power-plug",
            value_fn=lambda data: data.get("status"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:battery-alert"
    
    def test_status_icon_unknown(self):
        """Test status sensor shows off icon when unknown."""
        coordinator = MagicMock()
        coordinator.data = {"status": "UNKNOWN"}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_STATUS,
            name="UPS Status",
            icon="mdi:power-plug",
            value_fn=lambda data: data.get("status"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:power-plug-off"
    
    def test_grid_icon_connected(self):
        """Test grid sensor shows tower icon when connected."""
        coordinator = MagicMock()
        coordinator.data = {"grid": GRID_CONNECTED}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_GRID_STATE,
            name="Grid State",
            value_fn=lambda data: data.get("grid"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:transmission-tower"
    
    def test_grid_icon_down(self):
        """Test grid sensor shows off tower icon when down."""
        coordinator = MagicMock()
        coordinator.data = {"grid": GRID_DOWN}
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_GRID_STATE,
            name="Grid State",
            value_fn=lambda data: data.get("grid"),
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.icon == "mdi:transmission-tower-off"


class TestTeslaUPSSensorEntityProperties:
    """Test sensor entity properties."""
    
    def test_unique_id_format(self):
        """Test unique ID is formatted correctly."""
        coordinator = MagicMock()
        coordinator.data = {"soe": 50.0}
        
        entry = MagicMock()
        entry.entry_id = "abc123"
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_BATTERY,
            name="Battery Charge",
        )
        sensor = TeslaUPSSensor(coordinator, desc, entry)
        
        assert sensor.unique_id == "abc123_battery_charge"
    
    def test_device_info_structure(self):
        """Test device info has correct structure."""
        coordinator = MagicMock()
        coordinator.data = {"soe": 50.0}
        
        entry = MagicMock()
        entry.entry_id = "test_entry"
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_BATTERY,
            name="Battery Charge",
        )
        sensor = TeslaUPSSensor(coordinator, desc, entry)
        
        device_info = sensor.device_info
        assert device_info["name"] == "Tesla Powerwall UPS Bridge"
        assert device_info["manufacturer"] == MANUFACTURER
        assert device_info["model"] == MODEL
        assert device_info["sw_version"] == "1.0.0"
        assert device_info["identifiers"] == {(DOMAIN, "test_entry")}
    
    def test_available_when_success(self):
        """Test sensor is available when last update succeeded."""
        coordinator = MagicMock()
        coordinator.data = {"soe": 50.0}
        coordinator.last_update_success = True
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_BATTERY,
            name="Battery Charge",
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.available is True
    
    def test_not_available_when_failed(self):
        """Test sensor is not available when last update failed."""
        coordinator = MagicMock()
        coordinator.data = {"soe": 50.0}
        coordinator.last_update_success = False
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_BATTERY,
            name="Battery Charge",
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.available is False
    
    def test_native_value_none_when_no_data(self):
        """Test native value is None when coordinator has no data."""
        coordinator = MagicMock()
        coordinator.data = None
        
        desc = TeslaUPSSensorEntityDescription(
            key=SENSOR_BATTERY,
            name="Battery Charge",
            value_fn=lambda data: data.get("soe") if data else None,
        )
        sensor = TeslaUPSSensor(coordinator, desc, MagicMock())
        
        assert sensor.native_value is None


class TestAsyncSetupEntry:
    """Test sensor platform setup."""
    
    @pytest.mark.asyncio
    async def test_setup_entry_creates_sensors(self):
        """Test setup entry creates all sensor entities."""
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
            "provider": "Tesla Powerwall",
            "last_notified": "Never",
        }
        
        hass.data["tesla_ups"] = {entry.entry_id: coordinator}
        
        entities = []
        
        def mock_add_entities(new_entities):
            entities.extend(new_entities)
        
        await async_setup_entry(hass, entry, mock_add_entities)
        
        assert len(entities) == len(SENSOR_DESCRIPTIONS)
        
        # Verify all expected sensors are created
        keys = [e.entity_description.key for e in entities]
        assert SENSOR_BATTERY in keys
        assert SENSOR_STATUS in keys
        assert SENSOR_GRID_STATE in keys
        assert SENSOR_LAST_NOTIFICATION in keys
        assert SENSOR_PROVIDER in keys
        assert SENSOR_LAST_UPDATE in keys
