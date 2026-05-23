"""Tests for REPORTING_MODE configuration and service startup."""

import os
from unittest.mock import MagicMock, patch

import pytest

import bridge


class TestStartReportingServices:
    """Tests for start_reporting_services function."""

    def test_default_mode_is_nut(self, monkeypatch):
        """Test that default mode is 'nut' when REPORTING_MODE not set."""
        monkeypatch.delenv("REPORTING_MODE", raising=False)

        with patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch('subprocess.Popen') as mock_popen, \
             patch.object(bridge, 'write_nut_status_file'):

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            result = bridge.start_reporting_services()

            # Only native NUT server should start (default mode)
            mock_server_class.assert_called_once()
            mock_popen.assert_not_called()
            assert result is mock_server

    def test_nut_mode_only(self, monkeypatch):
        """Test that mode 'nut' starts only NUT server."""
        monkeypatch.setenv("REPORTING_MODE", "nut")

        with patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch('subprocess.Popen') as mock_popen, \
             patch.object(bridge, 'write_nut_status_file') as mock_write:

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            result = bridge.start_reporting_services()

            # Only NUT server should start
            mock_server_class.assert_called_once()
            mock_popen.assert_not_called()
            mock_write.assert_not_called()  # Not in snmp mode
            assert result is mock_server

    def test_snmp_mode_only(self, monkeypatch):
        """Test that mode 'snmp' starts SNMP agent only."""
        monkeypatch.setenv("REPORTING_MODE", "snmp")

        with patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch('subprocess.Popen') as mock_popen, \
             patch.object(bridge, 'write_nut_status_file') as mock_write:

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            result = bridge.start_reporting_services()

            # Only SNMP should start, NUT server should not
            mock_server_class.assert_not_called()
            mock_popen.assert_called_once()
            # In SNMP mode, no NUT file is written (pure SNMP)
            mock_write.assert_not_called()
            assert result is None

    def test_upsd_mode(self, monkeypatch):
        """Test that mode 'upsd' writes NUT files only - no SNMP, no native NUT server."""
        monkeypatch.setenv("REPORTING_MODE", "upsd")

        with patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch('subprocess.Popen') as mock_popen, \
             patch.object(bridge, 'write_nut_status_file') as mock_write:

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            result = bridge.start_reporting_services()

            # Neither SNMP nor native NUT server should start
            mock_server_class.assert_not_called()
            mock_popen.assert_not_called()
            # In upsd mode, we only write NUT file for external nut-upsd container
            mock_write.assert_called_once_with("OL", 100.0)
            assert result is None


    def test_mode_case_insensitive(self, monkeypatch):
        """Test that mode is case insensitive."""
        monkeypatch.setenv("REPORTING_MODE", "NUT")

        with patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch('subprocess.Popen') as mock_popen:

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            bridge.start_reporting_services()

            # Should work with uppercase
            mock_server_class.assert_called_once()
            mock_popen.assert_not_called()

    def test_invalid_mode_fallback(self, monkeypatch):
        """Test that invalid mode falls back to 'nut'."""
        monkeypatch.setenv("REPORTING_MODE", "invalid")

        with patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch('subprocess.Popen') as mock_popen, \
             patch.object(bridge, 'write_nut_status_file'):

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            result = bridge.start_reporting_services()

            # Should fall back to nut (native NUT protocol)
            mock_server_class.assert_called_once()
            mock_popen.assert_not_called()

    def test_nut_server_port_env(self, monkeypatch):
        """Test that NUT_SERVER_PORT environment variable is used."""
        monkeypatch.setenv("REPORTING_MODE", "nut")
        monkeypatch.setenv("NUT_SERVER_PORT", "3494")

        with patch.object(bridge, 'NUTServer') as mock_server_class:
            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            bridge.start_reporting_services()

            mock_server_class.assert_called_once_with(host="0.0.0.0", port=3494)

    def test_nut_server_failure_logged(self, monkeypatch):
        """Test that NUT server failure is logged but doesn't crash."""
        monkeypatch.setenv("REPORTING_MODE", "nut")

        with patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch('subprocess.Popen') as mock_popen:

            mock_server_class.side_effect = OSError("Port in use")

            result = bridge.start_reporting_services()

            # Should return None on failure
            assert result is None
            mock_popen.assert_not_called()

    def test_snmp_failure_logged(self, monkeypatch):
        """Test that SNMP agent failure is logged but doesn't crash."""
        monkeypatch.setenv("REPORTING_MODE", "snmp")

        with patch('subprocess.Popen') as mock_popen, \
             patch.object(bridge, 'write_nut_status_file'):

            mock_popen.side_effect = OSError("Cannot start process")

            result = bridge.start_reporting_services()

            # Should still complete
            assert result is None


class TestNUTServerLifecycle:
    """Tests for NUT server startup and shutdown in lifespan."""

    def test_lifespan_creates_and_cleans_up_nut_server(self, monkeypatch):
        """Test that lifespan manager starts and stops NUT server."""
        monkeypatch.setenv("REPORTING_MODE", "nut")

        with patch.object(bridge, 'load_providers'), \
             patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch.object(bridge, 'threading') as mock_threading, \
             patch.object(bridge, 'background_poller'):

            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            # Create async generator for lifespan
            async def run_lifespan():
                gen = bridge.lifespan(bridge.app)
                await gen.__aenter__()
                await gen.__aexit__(None, None, None)

            import asyncio
            asyncio.run(run_lifespan())

            # Server should be started and stopped
            mock_server.start.assert_called_once()
            mock_server.stop.assert_called_once()

    def test_lifespan_handles_no_nut_server(self, monkeypatch):
        """Test that lifespan handles snmp mode (no NUT server)."""
        monkeypatch.setenv("REPORTING_MODE", "snmp")

        with patch.object(bridge, 'load_providers'), \
             patch.object(bridge, 'NUTServer') as mock_server_class, \
             patch.object(bridge, 'threading') as mock_threading, \
             patch.object(bridge, 'background_poller'), \
             patch('subprocess.Popen'), \
             patch.object(bridge, 'write_nut_status_file'):

            mock_server_class.return_value = None

            async def run_lifespan():
                gen = bridge.lifespan(bridge.app)
                await gen.__aenter__()
                await gen.__aexit__(None, None, None)

            import asyncio
            asyncio.run(run_lifespan())

            # Should complete without error even with no NUT server
            assert bridge.nut_server is None
