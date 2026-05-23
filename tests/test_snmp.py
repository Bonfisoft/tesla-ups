"""Tests for NUT SNMP agent."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock pysnmp modules before importing nut_snmp_agent
sys.modules['pysnmp'] = MagicMock()
sys.modules['pysnmp.entity'] = MagicMock()
sys.modules['pysnmp.entity.rfc3413'] = MagicMock()
sys.modules['pysnmp.carrier'] = MagicMock()
sys.modules['pysnmp.carrier.asyncore'] = MagicMock()
sys.modules['pysnmp.carrier.asyncore.dgram'] = MagicMock()
sys.modules['pysnmp.carrier.udp'] = MagicMock()
sys.modules['pysnmp.carrier.udp.dgram'] = MagicMock()
sys.modules['pysnmp.smi'] = MagicMock()
sys.modules['pysnmp.smi.rfc1902'] = MagicMock()

# Import the module under test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "nut-snmp"))

try:
    from nut_snmp_agent import get_nut_data, create_snmp_agent
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False
    get_nut_data = None
    create_snmp_agent = None

# Skip all SNMP tests if pysnmp is not available or has incompatible API
pytestmark = pytest.mark.skipif(not SNMP_AVAILABLE,
    reason="SNMP tests require pysnmp 4.x, 7.x has incompatible API")


class TestGetNutData:
    """Test the NUT data retrieval function."""

    def test_get_nut_data_success(self, monkeypatch):
        """Test successful NUT data retrieval."""
        monkeypatch.setenv("NUT_HOST", "localhost")
        monkeypatch.setenv("NUT_PORT", "3493")

        # Mock socket connection
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            data = get_nut_data()

        assert data["battery.charge"] == 85
        assert data["ups.status"] == "OL"
        assert data["ups.mfr"] == "Tesla"
        assert mock_sock.connect.called
        assert mock_sock.close.called

    def test_get_nut_data_connection_failure(self, monkeypatch):
        """Test NUT connection failure handling."""
        monkeypatch.setenv("NUT_HOST", "invalid-host")
        monkeypatch.setenv("NUT_PORT", "3493")

        # Mock socket to raise connection error
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect.side_effect = ConnectionRefusedError("Connection refused")
            mock_socket.return_value = mock_sock

            data = get_nut_data()

        # Should return error values
        assert data["battery.charge"] == 0
        assert data["ups.status"] == "OB"
        assert data["ups.mfr"] == "Unknown"

    def test_get_nut_data_default_values(self):
        """Test that default values are returned when NUT is unavailable."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect.side_effect = TimeoutError("Timeout")
            mock_socket.return_value = mock_sock

            data = get_nut_data()

        assert "battery.charge" in data
        assert "ups.status" in data
        assert "battery.voltage" in data
        assert "ups.mfr" in data
        assert "ups.model" in data


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_default_environment_values(self, monkeypatch):
        """Test default values when env vars not set."""
        # Clear environment
        for key in ["NUT_HOST", "NUT_PORT", "NUT_USER", "NUT_PASS", "SNMP_COMMUNITY"]:
            monkeypatch.delenv(key, raising=False)

        # Reload module to get defaults
        import importlib
        import nut_snmp_agent

        importlib.reload(nut_snmp_agent)

        assert nut_snmp_agent.NUT_HOST == "nut-upsd"
        assert nut_snmp_agent.NUT_PORT == 3493
        assert nut_snmp_agent.NUT_USER == "admin"
        assert nut_snmp_agent.NUT_PASS == "admin"
        assert nut_snmp_agent.SNMP_COMMUNITY == "public"

    def test_custom_environment_values(self, monkeypatch):
        """Test custom env var values."""
        monkeypatch.setenv("NUT_HOST", "custom-nut")
        monkeypatch.setenv("NUT_PORT", "1234")
        monkeypatch.setenv("NUT_USER", "custom-user")
        monkeypatch.setenv("NUT_PASS", "custom-pass")
        monkeypatch.setenv("SNMP_COMMUNITY", "custom-community")

        import importlib
        import nut_snmp_agent

        importlib.reload(nut_snmp_agent)

        assert nut_snmp_agent.NUT_HOST == "custom-nut"
        assert nut_snmp_agent.NUT_PORT == 1234
        assert nut_snmp_agent.NUT_USER == "custom-user"
        assert nut_snmp_agent.NUT_PASS == "custom-pass"
        assert nut_snmp_agent.SNMP_COMMUNITY == "custom-community"


class TestSNMPAgent:
    """Test SNMP agent creation."""

    @patch("nut_snmp_agent.config.addTransport")
    @patch("nut_snmp_agent.config.addV1System")
    @patch("nut_snmp_agent.config.addVacmUser")
    @patch("nut_snmp_agent.engine.SnmpEngine")
    def test_create_snmp_agent(
        self, mock_engine, mock_vacm, mock_v1, mock_transport, monkeypatch
    ):
        """Test SNMP agent creation with proper configuration."""
        monkeypatch.setenv("SNMP_COMMUNITY", "test-community")

        mock_snmp_engine = MagicMock()
        mock_engine.return_value = mock_snmp_engine

        result = create_snmp_agent()

        # Verify SNMP engine was created
        assert mock_engine.called

        # Verify transport was configured
        assert mock_transport.called

        # Verify V1 system was added
        assert mock_v1.called

        # Verify VACM user was added
        assert mock_vacm.called

        # Verify agent was returned
        assert result == mock_snmp_engine


class TestSNMPDataTypes:
    """Test SNMP data type conversions."""

    def test_battery_charge_is_numeric(self):
        """Verify battery charge is numeric value."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            data = get_nut_data()

        assert isinstance(data["battery.charge"], (int, float))
        assert 0 <= data["battery.charge"] <= 100

    def test_ups_status_format(self):
        """Verify UPS status format matches NUT standard."""
        with patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock

            data = get_nut_data()

        # NUT status format: OL (online), OB (on battery), etc.
        assert isinstance(data["ups.status"], str)
        assert len(data["ups.status"]) >= 2
