"""Comprehensive tests for Tesla UPS integration __init__.py."""

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

from tesla_ups.const import DOMAIN, CONF_BRIDGE_URL
from tesla_ups import async_setup_entry, async_unload_entry, async_reload_entry, PLATFORMS
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady


class TestAsyncSetupEntry:
    """Test async_setup_entry function."""
    
    @pytest.mark.asyncio
    async def test_setup_entry_success(self):
        """Test successful setup of config entry."""
        hass = HomeAssistant()
        hass.data = {}
        
        entry = ConfigEntry(
            entry_id="test_entry",
            domain="tesla_ups",
            data={CONF_BRIDGE_URL: "http://test-bridge:8000"},
        )
        
        # Mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.async_start_sse = AsyncMock()
        
        # Mock hass.config_entries
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        with patch("tesla_ups.TeslaUPSDataUpdateCoordinator", return_value=mock_coordinator):
            result = await async_setup_entry(hass, entry)
        
        assert result is True
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
        mock_coordinator.async_start_sse.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_entry_connection_failure(self):
        """Test setup entry raises ConfigEntryNotReady on connection failure."""
        hass = HomeAssistant()
        hass.data = {}
        
        entry = ConfigEntry(
            entry_id="test_entry",
            domain="tesla_ups",
            data={CONF_BRIDGE_URL: "http://invalid:8000"},
        )
        
        # Mock coordinator that fails on first refresh
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        
        with patch("tesla_ups.TeslaUPSDataUpdateCoordinator", return_value=mock_coordinator):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, entry)
    
    @pytest.mark.asyncio
    async def test_setup_entry_stores_coordinator(self):
        """Test that coordinator is stored in hass.data."""
        hass = HomeAssistant()
        hass.data = {}
        
        entry = ConfigEntry(
            entry_id="test_entry",
            domain="tesla_ups",
            data={CONF_BRIDGE_URL: "http://test-bridge:8000"},
        )
        
        mock_coordinator = MagicMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.async_start_sse = AsyncMock()
        
        # Mock hass.config_entries
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        with patch("tesla_ups.TeslaUPSDataUpdateCoordinator", return_value=mock_coordinator):
            await async_setup_entry(hass, entry)
        
        # Verify coordinator is stored
        assert hass.data[DOMAIN][entry.entry_id] == mock_coordinator


class TestAsyncUnloadEntry:
    """Test async_unload_entry function."""
    
    @pytest.mark.asyncio
    async def test_unload_entry_success(self):
        """Test successful unload of config entry."""
        hass = HomeAssistant()
        hass.data = {DOMAIN: {}}
        
        entry = ConfigEntry(
            entry_id="test_entry",
            domain="tesla_ups",
            data={CONF_BRIDGE_URL: "http://test-bridge:8000"},
        )
        
        # Setup mock coordinator
        mock_coordinator = MagicMock()
        mock_coordinator.async_stop_sse = AsyncMock()
        mock_coordinator._sse_task = None
        hass.data[DOMAIN][entry.entry_id] = mock_coordinator
        
        # Mock hass.config_entries
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        
        result = await async_unload_entry(hass, entry)
        
        assert result is True
        mock_coordinator.async_stop_sse.assert_called_once()
        assert entry.entry_id not in hass.data[DOMAIN]
    
    @pytest.mark.asyncio
    async def test_unload_entry_failure(self):
        """Test unload returns False when platforms fail to unload."""
        hass = HomeAssistant()
        hass.data = {DOMAIN: {}}
        
        entry = ConfigEntry(
            entry_id="test_entry",
            domain="tesla_ups",
            data={CONF_BRIDGE_URL: "http://test-bridge:8000"},
        )
        
        mock_coordinator = MagicMock()
        mock_coordinator.async_stop_sse = AsyncMock()
        mock_coordinator._sse_task = None
        hass.data[DOMAIN][entry.entry_id] = mock_coordinator
        
        # Mock hass.config_entries
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
        
        result = await async_unload_entry(hass, entry)
        
        assert result is False
        mock_coordinator.async_stop_sse.assert_called_once()
        # Entry should still be in data since unload failed
        assert entry.entry_id in hass.data[DOMAIN]


class TestAsyncReloadEntry:
    """Test async_reload_entry function."""
    
    @pytest.mark.asyncio
    async def test_reload_entry(self):
        """Test reload entry calls unload then setup."""
        hass = HomeAssistant()
        hass.data = {DOMAIN: {}}
        
        entry = ConfigEntry(
            entry_id="test_entry",
            domain="tesla_ups",
            data={CONF_BRIDGE_URL: "http://test-bridge:8000"},
        )
        
        mock_unload = AsyncMock(return_value=True)
        mock_setup = AsyncMock(return_value=True)
        
        with patch("tesla_ups.async_unload_entry", mock_unload):
            with patch("tesla_ups.async_setup_entry", mock_setup):
                await async_reload_entry(hass, entry)
        
        mock_unload.assert_called_once_with(hass, entry)
        mock_setup.assert_called_once_with(hass, entry)


class TestPlatforms:
    """Test PLATFORMS constant."""
    
    def test_platforms_list(self):
        """Test PLATFORMS contains expected platforms."""
        assert Platform.SENSOR in PLATFORMS
        assert Platform.BINARY_SENSOR in PLATFORMS
        assert len(PLATFORMS) == 2
    
    def test_platforms_are_strings(self):
        """Test all platforms are string values."""
        for platform in PLATFORMS:
            assert isinstance(platform, (str, Platform))
