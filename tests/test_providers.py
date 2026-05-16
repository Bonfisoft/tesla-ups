"""Tests for the providers package: PowerwallProvider and load_provider()."""

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from providers import ConfigError, load_provider
from providers.base import BatteryStatus
from providers.powerwall import PowerwallProvider


class TestPowerwallProvider:
    def _make_soe_response(self, percentage: float) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"percentage": percentage}
        return mock_resp

    def _make_grid_response(self, grid_status: str) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"grid_status": grid_status, "grid_services_active": False}
        return mock_resp

    def test_fetch_status_grid_connected(self):
        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.side_effect = [
                self._make_soe_response(85.5),
                self._make_grid_response("SystemGridConnected"),
            ]
            provider = PowerwallProvider(base_url="http://fake")
            status = provider.fetch_status()

        assert isinstance(status, BatteryStatus)
        assert status.soe == 85.5
        assert status.grid_connected is True

    def test_fetch_status_grid_down(self):
        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.side_effect = [
                self._make_soe_response(42.0),
                self._make_grid_response("GridDown"),
            ]
            provider = PowerwallProvider(base_url="http://fake")
            status = provider.fetch_status()

        assert status.grid_connected is False
        assert status.soe == 42.0

    def test_fetch_status_rounds_soe(self):
        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.side_effect = [
                self._make_soe_response(77.777),
                self._make_grid_response("SystemGridConnected"),
            ]
            provider = PowerwallProvider(base_url="http://fake")
            status = provider.fetch_status()

        assert status.soe == 77.8

    def test_provider_name(self):
        provider = PowerwallProvider(base_url="http://fake")
        assert provider.provider_name == "Tesla Powerwall"

    def test_health_check_ok(self):
        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True)
            provider = PowerwallProvider(base_url="http://fake")
            assert provider.health_check() is True

    def test_health_check_failure(self):
        import requests as req
        with patch("providers.powerwall.requests.get", side_effect=req.RequestException("timeout")):
            provider = PowerwallProvider(base_url="http://fake")
            assert provider.health_check() is False


class TestLoadProvider:
    def test_load_powerwall_provider(self, tmp_path):
        cfg = tmp_path / "providers.yaml"
        cfg.write_text(textwrap.dedent("""\
            provider: powerwall
            config:
              base_url: http://fake:8675
              timeout: 3
        """))
        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True)
            provider = load_provider(str(cfg))

        assert isinstance(provider, PowerwallProvider)
        assert provider.provider_name == "Tesla Powerwall"

    def test_missing_config_file_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_provider(str(tmp_path / "nonexistent.yaml"))

    def test_unknown_provider_raises(self, tmp_path):
        cfg = tmp_path / "providers.yaml"
        cfg.write_text("provider: unknown_battery\n")
        with pytest.raises(ConfigError, match="Unknown provider"):
            load_provider(str(cfg))

    def test_missing_provider_key_raises(self, tmp_path):
        cfg = tmp_path / "providers.yaml"
        cfg.write_text("config:\n  timeout: 5\n")
        with pytest.raises(ConfigError, match="'provider' key is missing"):
            load_provider(str(cfg))

    def test_health_check_failure_does_not_raise(self, tmp_path):
        cfg = tmp_path / "providers.yaml"
        cfg.write_text(textwrap.dedent("""\
            provider: powerwall
            config:
              base_url: http://fake:8675
        """))
        import requests as req
        with patch("providers.powerwall.requests.get", side_effect=req.RequestException("down")):
            provider = load_provider(str(cfg))

        assert isinstance(provider, PowerwallProvider)
