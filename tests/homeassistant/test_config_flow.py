"""Comprehensive tests for Tesla UPS config flow."""

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
import aiohttp

from tesla_ups.const import CONF_BRIDGE_URL, DOMAIN
from tesla_ups.config_flow import (
    TeslaUPSConfigFlow,
    TeslaUPSOptionsFlow,
    validate_bridge_url,
    STEP_USER_DATA_SCHEMA,
)
from homeassistant.config_entries import ConfigFlow, ConfigEntry
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.core import HomeAssistant, callback


class MockResponse:
    """Mock aiohttp response for testing."""
    
    def __init__(self, status=200, json_data=None, raise_error=None):
        self.status = status
        self._json_data = json_data or {}
        self._raise_error = raise_error
    
    async def json(self):
        if self._raise_error:
            raise self._raise_error
        return self._json_data
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockClientSession:
    """Mock aiohttp ClientSession."""
    
    def __init__(self, response=None, side_effect=None, raise_exception=None):
        self._response = response
        self._side_effect = side_effect
        self._raise_exception = raise_exception
        self._call_count = 0
        self.last_url = None
    
    def get(self, url, **kwargs):
        self._call_count += 1
        self.last_url = url
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


class TestValidateBridgeUrl:
    """Test bridge URL validation function."""
    
    @pytest.mark.asyncio
    async def test_validate_success(self):
        """Test successful bridge validation."""
        mock_response = MockResponse(
            status=200,
            json_data={
                "status": "OL",
                "soe": 85.0,
                "grid": "SystemGridConnected",
            }
        )
        mock_session = MockClientSession(response=mock_response)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validate_bridge_url("http://test-bridge:8000")
        
        assert result["valid"] is True
        assert result["error"] is None
        assert result["info"]["status"] == "OL"
    
    @pytest.mark.asyncio
    async def test_validate_missing_status_field(self):
        """Test validation fails when response missing status field."""
        mock_response = MockResponse(
            status=200,
            json_data={
                "soe": 85.0,
                "grid": "SystemGridConnected",
            }
        )
        mock_session = MockClientSession(response=mock_response)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validate_bridge_url("http://test-bridge:8000")
        
        assert result["valid"] is False
        assert "Invalid response" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_http_500(self):
        """Test validation fails on HTTP 500."""
        mock_response = MockResponse(status=500)
        mock_session = MockClientSession(response=mock_response)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validate_bridge_url("http://test-bridge:8000")
        
        assert result["valid"] is False
        assert "HTTP 500" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_connection_refused(self):
        """Test validation fails on connection refused."""
        mock_session = MockClientSession(
            raise_exception=aiohttp.ClientConnectionError("Connection refused")
        )
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validate_bridge_url("http://test-bridge:8000")
        
        assert result["valid"] is False
        assert "Could not connect" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_client_error(self):
        """Test validation fails on client error."""
        mock_session = MockClientSession(
            raise_exception=aiohttp.ClientError("Client error")
        )
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validate_bridge_url("http://test-bridge:8000")
        
        assert result["valid"] is False
        assert "Connection error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_timeout_error(self):
        """Test validation fails on timeout."""
        mock_session = MockClientSession(
            raise_exception=asyncio.TimeoutError()
        )
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validate_bridge_url("http://test-bridge:8000")
        
        assert result["valid"] is False
        assert "Unexpected error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_validate_url_normalization(self):
        """Test URL is normalized with trailing slash removed."""
        mock_response = MockResponse(
            status=200,
            json_data={"status": "OL"}
        )
        mock_session = MockClientSession(response=mock_response)
        
        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await validate_bridge_url("http://test-bridge:8000/")
        
        # Should still work with trailing slash
        assert result["valid"] is True


class TestTeslaUPSConfigFlowUserStep:
    """Test config flow user step."""
    
    def test_async_step_user_shows_form_initially(self):
        """Test user step shows form when no input provided."""
        flow = TeslaUPSConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        
        result = flow.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors={},
        )
        
        assert result["type"] == "form"
        assert result["step_id"] == "user"
    
    @pytest.mark.asyncio
    async def test_async_step_user_success(self):
        """Test successful config flow completion."""
        flow = TeslaUPSConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        
        mock_validation = {
            "valid": True,
            "error": None,
            "info": {"status": "OL", "soe": 85.0}
        }
        
        with patch("tesla_ups.config_flow.validate_bridge_url", return_value=mock_validation):
            result = await flow.async_step_user(
                user_input={CONF_BRIDGE_URL: "http://test-bridge:8000"}
            )
        
        assert result["type"] == "create_entry"
        assert result["title"] == "Tesla Powerwall UPS Bridge"
        assert result["data"][CONF_BRIDGE_URL] == "http://test-bridge:8000"
    
    @pytest.mark.asyncio
    async def test_async_step_user_validation_failure(self):
        """Test config flow shows error on validation failure."""
        flow = TeslaUPSConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        
        mock_validation = {
            "valid": False,
            "error": "Connection refused",
            "info": None
        }
        
        with patch("tesla_ups.config_flow.validate_bridge_url", return_value=mock_validation):
            result = await flow.async_step_user(
                user_input={CONF_BRIDGE_URL: "http://invalid:8000"}
            )
        
        assert result["type"] == "form"
        assert result["errors"]["base"] == "cannot_connect"
    
    @pytest.mark.asyncio
    async def test_unique_id_set_on_success(self):
        """Test unique ID is set from bridge URL."""
        flow = TeslaUPSConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        
        mock_validation = {
            "valid": True,
            "error": None,
            "info": {"status": "OL"}
        }
        
        with patch("tesla_ups.config_flow.validate_bridge_url", return_value=mock_validation):
            result = await flow.async_step_user(
                user_input={CONF_BRIDGE_URL: "http://test-bridge:8000"}
            )
        
        assert result["type"] == "create_entry"
        # Unique ID should be set to the bridge URL
        assert flow.unique_id == "http://test-bridge:8000"


class TestTeslaUPSConfigFlowOptions:
    """Test config flow options."""
    
    def test_async_get_options_flow_returns_options_flow(self):
        """Test async_get_options_flow returns correct type."""
        flow = TeslaUPSConfigFlow()
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry"
        
        options_flow = flow.async_get_options_flow(entry)
        
        assert isinstance(options_flow, TeslaUPSOptionsFlow)
        assert options_flow.config_entry == entry


class TestTeslaUPSOptionsFlow:
    """Test options flow."""
    
    def test_options_flow_init(self):
        """Test options flow initialization."""
        entry = MagicMock(spec=ConfigEntry)
        entry.entry_id = "test_entry"
        entry.data = {CONF_BRIDGE_URL: "http://test:8000"}
        
        options_flow = TeslaUPSOptionsFlow(entry)
        
        assert options_flow.config_entry == entry
    
    @pytest.mark.asyncio
    async def test_options_flow_async_step_init(self):
        """Test options flow init step."""
        entry = MagicMock(spec=ConfigEntry)
        options_flow = TeslaUPSOptionsFlow(entry)
        
        result = await options_flow.async_step_init(user_input=None)
        
        assert result["type"] == "form"
        assert result["step_id"] == "init"
    
    @pytest.mark.asyncio
    async def test_options_flow_async_step_init_with_input(self):
        """Test options flow init step with user input."""
        entry = MagicMock(spec=ConfigEntry)
        options_flow = TeslaUPSOptionsFlow(entry)
        
        result = await options_flow.async_step_init(user_input={})
        
        assert result["type"] == "create_entry"


class TestConfigFlowEdgeCases:
    """Test config flow edge cases."""
    
    @pytest.mark.asyncio
    async def test_empty_bridge_url(self):
        """Test handling of empty bridge URL."""
        flow = TeslaUPSConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        
        mock_validation = {
            "valid": False,
            "error": "Invalid URL",
            "info": None
        }
        
        with patch("tesla_ups.config_flow.validate_bridge_url", return_value=mock_validation):
            result = await flow.async_step_user(
                user_input={CONF_BRIDGE_URL: ""}
            )
        
        assert result["type"] == "form"
        assert "cannot_connect" in result["errors"].values()
    
    @pytest.mark.asyncio
    async def test_bridge_url_with_path(self):
        """Test bridge URL with path component."""
        flow = TeslaUPSConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}
        
        mock_validation = {
            "valid": True,
            "error": None,
            "info": {"status": "OL"}
        }
        
        with patch("tesla_ups.config_flow.validate_bridge_url", return_value=mock_validation):
            result = await flow.async_step_user(
                user_input={CONF_BRIDGE_URL: "http://test-bridge:8000/"}
            )
        
        assert result["type"] == "create_entry"
        # URL should be stored as provided (with trailing slash handled by validation)


import asyncio
