"""Shared fixtures for Home Assistant integration tests."""

import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOMEASSISTANT_DIR = os.path.join(PROJECT_ROOT, "homeassistant")
MOCKS_DIR = os.path.join(os.path.dirname(__file__), "mocks")

# Add mocks directory FIRST (before any real homeassistant imports)
sys.path.insert(0, MOCKS_DIR)

# Add homeassistant directory to path for tesla_ imports
sys.path.insert(0, HOMEASSISTANT_DIR)

import pytest
import asyncio


@pytest.fixture
def mock_coordinator_data():
    """Return mock coordinator data for testing."""
    return {
        "status": "OL",
        "soe": 85.5,
        "grid": "SystemGridConnected",
        "provider": "Tesla Powerwall",
        "last_notified": "12:30:45",
        "connection_status": "connected",
        "notification_sent": False,
    }


@pytest.fixture
def mock_coordinator_on_battery():
    """Return mock coordinator data simulating grid outage."""
    return {
        "status": "OB",
        "soe": 65.0,
        "grid": "GridDown",
        "provider": "Tesla Powerwall",
        "last_notified": "14:20:10",
        "connection_status": "connected",
        "notification_sent": True,
    }


@pytest.fixture
def mock_coordinator_low_battery():
    """Return mock coordinator data simulating low battery during outage."""
    return {
        "status": "OB LB",
        "soe": 12.0,
        "grid": "GridDown",
        "provider": "Tesla Powerwall",
        "last_notified": "15:45:00",
        "connection_status": "connected",
        "notification_sent": True,
    }


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    from homeassistant.config_entries import ConfigEntry
    entry = ConfigEntry(
        entry_id="test_entry_id",
        domain="tesla_ups",
        data={"bridge_url": "http://test-bridge:8000"},
        title="Tesla Powerwall UPS Bridge"
    )
    return entry


@pytest.fixture
def mock_hass():
    """Return a mock HomeAssistant instance."""
    from homeassistant.core import HomeAssistant
    hass = HomeAssistant()
    hass.config_entries = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_coordinator(mock_coordinator_data):
    """Return a mock coordinator with data."""
    from tesla_ups.coordinator import TeslaUPSDataUpdateCoordinator
    from homeassistant.core import HomeAssistant
    
    hass = HomeAssistant()
    coordinator = MagicMock(spec=TeslaUPSDataUpdateCoordinator)
    coordinator.data = mock_coordinator_data
    coordinator.last_update_success = True
    coordinator.bridge_url = "http://test-bridge:8000"
    coordinator.connection_status = "connected"
    coordinator.async_start_sse = AsyncMock()
    coordinator.async_stop_sse = AsyncMock()
    return coordinator


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
