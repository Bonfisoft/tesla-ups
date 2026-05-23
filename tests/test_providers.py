"""Tests for the providers package: PowerwallProvider and load_provider()."""

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from providers import ConfigError, load_provider, load_providers
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


class TestLoadProviders:
    """Test the multi-provider factory with environment variables."""

    def test_load_single_provider_from_env(self, monkeypatch):
        """Test loading a single provider from environment variables."""
        monkeypatch.setenv("PROVIDER_1_TYPE", "powerwall")
        monkeypatch.setenv("PROVIDER_1_PROXY_URL", "http://fake:8675/api/status")
        monkeypatch.setenv("PROVIDER_1_TIMEOUT", "5")

        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True)
            providers = load_providers()

        assert len(providers) == 1
        assert isinstance(providers[0], PowerwallProvider)

    def test_load_multiple_providers_from_env(self, monkeypatch):
        """Test loading multiple providers from environment variables."""
        monkeypatch.setenv("PROVIDER_1_TYPE", "powerwall")
        monkeypatch.setenv("PROVIDER_1_PROXY_URL", "http://pw1:8675/api/status")
        monkeypatch.setenv("PROVIDER_2_TYPE", "powerwall")
        monkeypatch.setenv("PROVIDER_2_PROXY_URL", "http://pw2:8675/api/status")

        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True)
            providers = load_providers()

        assert len(providers) == 2
        assert all(isinstance(p, PowerwallProvider) for p in providers)

    def test_load_provider_missing_proxy_url_raises(self, monkeypatch):
        """Test that missing PROXY_URL raises ConfigError."""
        import os
        for key in list(os.environ.keys()):
            if key.startswith("PROVIDER") or key == "PROXY_URL":
                monkeypatch.delenv(key, raising=False)

        with pytest.raises(ConfigError, match="PROXY_URL"):
            load_providers()

    def test_unknown_provider_type_raises(self, monkeypatch):
        """Test that unknown provider type raises ConfigError."""
        monkeypatch.setenv("PROVIDER_1_TYPE", "unknown_type")
        monkeypatch.setenv("PROVIDER_1_PROXY_URL", "http://fake:8675/api/status")

        with pytest.raises(ConfigError, match="Unknown provider"):
            load_providers()

    def test_health_check_failure_does_not_raise(self, monkeypatch):
        """Test that health check failure doesn't prevent provider loading."""
        monkeypatch.setenv("PROVIDER_1_TYPE", "powerwall")
        monkeypatch.setenv("PROVIDER_1_PROXY_URL", "http://fake:8675/api/status")

        import requests as req
        with patch("providers.powerwall.requests.get", side_effect=req.RequestException("down")):
            providers = load_providers()

        assert len(providers) == 1
        assert isinstance(providers[0], PowerwallProvider)

    def test_load_provider_backward_compatible(self, monkeypatch):
        """Test legacy single provider loading (backward compatibility)."""
        monkeypatch.setenv("PROXY_URL", "http://legacy:8675/api/status")

        with patch("providers.powerwall.requests.get") as mock_get:
            mock_get.return_value = MagicMock(ok=True)
            provider = load_provider()

        assert isinstance(provider, PowerwallProvider)
