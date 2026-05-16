"""Comprehensive tests for Tesla UPS data coordinator."""

import sys
import os
import asyncio
import json

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
import aiohttp

from tesla_ups.coordinator import TeslaUPSDataUpdateCoordinator
from tesla_ups.const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    EVENT_STATUS_UPDATE,
    EVENT_CONNECTED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


class MockResponse:
    """Mock aiohttp response for testing."""
    
    def __init__(self, status=200, json_data=None, text=None, raise_error=None):
        self.status = status
        self._json_data = json_data
        self._text = text
        self._raise_error = raise_error
        self.content = MagicMock()
    
    async def json(self):
        if self._raise_error:
            raise self._raise_error
        return self._json_data or {}
    
    async def text(self):
        return self._text or ""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockClientSession:
    """Mock aiohttp ClientSession for testing."""
    
    def __init__(self, response=None, side_effect=None, raise_exception=None):
        self._response = response
        self._side_effect = side_effect
        self._raise_exception = raise_exception
        self._call_count = 0
    
    def get(self, url, **kwargs):
        self._call_count += 1
        if self._raise_exception:
            raise self._raise_exception
        if self._side_effect:
            if isinstance(self._side_effect, list):
                result = self._side_effect[min(self._call_count - 1, len(self._side_effect) - 1)]
                if isinstance(result, Exception):
                    raise result
                return result
            elif callable(self._side_effect):
                return self._side_effect(url, **kwargs)
        return self._response or MockResponse()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestTeslaUPSDataUpdateCoordinatorInit:
    """Test coordinator initialization."""
    
    def test_coordinator_init_basic(self):
        """Test basic coordinator initialization."""
        hass = HomeAssistant()
        
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        assert coordinator.bridge_url == "http://test-bridge:8000"
        assert coordinator.sse_url == "http://test-bridge:8000/api/events"
        assert coordinator.status_url == "http://test-bridge:8000/api/status"
        assert coordinator.update_interval is None
        assert coordinator.name == DOMAIN
    
    def test_coordinator_init_with_trailing_slash(self):
        """Test coordinator strips trailing slash from URL."""
        hass = HomeAssistant()
        
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000/",
        )
        
        assert coordinator.bridge_url == "http://test-bridge:8000"
        assert coordinator.sse_url == "http://test-bridge:8000/api/events"
    
    def test_coordinator_inherits_from_data_update_coordinator(self):
        """Test coordinator inherits from DataUpdateCoordinator."""
        hass = HomeAssistant()
        
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        assert isinstance(coordinator, DataUpdateCoordinator)


class TestTeslaUPSDataUpdateCoordinatorUpdateData:
    """Test coordinator REST API data update."""
    
    @pytest.mark.asyncio
    async def test_update_data_success(self):
        """Test successful data fetch via REST API."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        mock_response = MockResponse(
            status=200,
            json_data={
                "status": "OL",
                "soe": 85.5,
                "grid": "SystemGridConnected",
                "provider": "Tesla Powerwall",
            }
        )
        mock_session = MockClientSession(response=mock_response)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            data = await coordinator._async_update_data()
        
        assert data["status"] == "OL"
        assert data["soe"] == 85.5
        assert data["connection_status"] == "polling"
    
    @pytest.mark.asyncio
    async def test_update_data_http_error(self):
        """Test data fetch handles HTTP error gracefully."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        mock_response = MockResponse(status=500)
        mock_session = MockClientSession(response=mock_response)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            data = await coordinator._async_update_data()
        
        assert data["status"] == "UNKNOWN"
        assert data["connection_status"] == "disconnected"
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_update_data_connection_error(self):
        """Test data fetch handles connection error gracefully."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        mock_session = MockClientSession(raise_exception=aiohttp.ClientConnectionError("Connection refused"))
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            data = await coordinator._async_update_data()
        
        assert data["status"] == "UNKNOWN"
        assert data["connection_status"] == "disconnected"
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_update_data_timeout_error(self):
        """Test data fetch handles timeout error gracefully."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        mock_session = MockClientSession(raise_exception=asyncio.TimeoutError())
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            data = await coordinator._async_update_data()
        
        assert data["status"] == "UNKNOWN"
        assert data["connection_status"] == "disconnected"


class TestTeslaUPSDataUpdateCoordinatorSSE:
    """Test coordinator SSE functionality."""
    
    @pytest.mark.asyncio
    async def test_start_sse_creates_background_task(self):
        """Test starting SSE creates a background task."""
        hass = HomeAssistant()
        hass.async_create_background_task = MagicMock(return_value=MagicMock())
        
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        await coordinator.async_start_sse()
        
        hass.async_create_background_task.assert_called_once()
        assert coordinator._sse_task is not None
    
    @pytest.mark.asyncio
    async def test_stop_sse_cancels_task(self):
        """Test stopping SSE cancels the background task."""
        hass = HomeAssistant()
        
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        # Create a real async task that we can cancel
        async def dummy_task():
            await asyncio.sleep(10)
        
        task = asyncio.create_task(dummy_task())
        coordinator._sse_task = task
        
        await coordinator.async_stop_sse()
        
        # Task should be cancelled
        assert task.cancelled() or task.done()
    
    @pytest.mark.asyncio
    async def test_process_sse_message_status_update(self):
        """Test processing SSE status_update message."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        # Mock async_set_updated_data
        coordinator.async_set_updated_data = MagicMock()
        
        event_data = {
            "status": "OB",
            "soe": 65.0,
            "grid": "GridDown",
        }
        sse_message = f"data: {json.dumps({'event': EVENT_STATUS_UPDATE, 'data': event_data})}"
        
        await coordinator._process_sse_message(sse_message)
        
        coordinator.async_set_updated_data.assert_called_once()
        called_data = coordinator.async_set_updated_data.call_args[0][0]
        assert called_data["connection_status"] == "connected"
    
    @pytest.mark.asyncio
    async def test_process_sse_message_connected(self):
        """Test processing SSE connected message."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        coordinator.async_set_updated_data = MagicMock()
        
        event_data = {
            "status": "OL",
            "soe": 90.0,
            "grid": "SystemGridConnected",
        }
        sse_message = f"data: {json.dumps({'event': EVENT_CONNECTED, 'data': event_data})}"
        
        await coordinator._process_sse_message(sse_message)
        
        coordinator.async_set_updated_data.assert_called_once()
        called_data = coordinator.async_set_updated_data.call_args[0][0]
        assert called_data["connection_status"] == "connected"
    
    @pytest.mark.asyncio
    async def test_process_sse_message_invalid_json(self):
        """Test processing invalid SSE message."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        coordinator.async_set_updated_data = MagicMock()
        
        sse_message = "data: invalid json here"
        
        await coordinator._process_sse_message(sse_message)
        
        # Should not call async_set_updated_data for invalid JSON
        coordinator.async_set_updated_data.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_sse_message_keepalive(self):
        """Test processing SSE keepalive message."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        
        coordinator.async_set_updated_data = MagicMock()
        
        sse_message = ":keepalive"
        
        await coordinator._process_sse_message(sse_message)
        
        # Should not call async_set_updated_data for keepalive
        coordinator.async_set_updated_data.assert_not_called()


class TestTeslaUPSDataUpdateCoordinatorProperties:
    """Test coordinator properties."""
    
    def test_connection_status_connected(self):
        """Test connection_status property when connected."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        coordinator.data = {"connection_status": "connected"}
        
        assert coordinator.connection_status == "connected"
        assert coordinator.is_connected is True
    
    def test_connection_status_polling(self):
        """Test connection_status property when polling."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        coordinator.data = {"connection_status": "polling"}
        
        assert coordinator.connection_status == "polling"
        assert coordinator.is_connected is True
    
    def test_connection_status_disconnected(self):
        """Test connection_status property when disconnected."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        coordinator.data = {"connection_status": "disconnected"}
        
        assert coordinator.connection_status == "disconnected"
        assert coordinator.is_connected is False
    
    def test_connection_status_unknown(self):
        """Test connection_status property when data is None."""
        hass = HomeAssistant()
        coordinator = TeslaUPSDataUpdateCoordinator(
            hass=hass,
            bridge_url="http://test-bridge:8000",
        )
        coordinator.data = None
        
        assert coordinator.connection_status == "unknown"
        assert coordinator.is_connected is False


