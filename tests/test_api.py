from fastapi.testclient import TestClient

import bridge
from providers.base import BatteryProvider, BatteryStatus


class MockProvider(BatteryProvider):
    @property
    def provider_name(self) -> str:
        return "Mock Provider"

    def fetch_status(self) -> BatteryStatus:
        return BatteryStatus(soe=99.0, grid_connected=True)


def test_api_status_endpoint_returns_state(monkeypatch):
    monkeypatch.setattr(bridge, "load_providers", lambda *a, **kw: [MockProvider()])
    monkeypatch.setattr(bridge, "background_poller", lambda: None)
    client = TestClient(bridge.app)

    bridge.state.update({
        "status": "OL",
        "grid": "SystemGridConnected",
        "soe": 99.0,
        "last_notified": "Never",
        "provider": "Mock Provider",
        "providers": [{"name": "Mock Provider", "soe": 99.0, "grid_connected": True}],
    })
    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["status"] == "OL"
    assert response.json()["soe"] == 99.0


def test_dashboard_endpoint_returns_html(monkeypatch):
    monkeypatch.setattr(bridge, "load_providers", lambda *a, **kw: [MockProvider()])
    monkeypatch.setattr(bridge, "background_poller", lambda: None)
    client = TestClient(bridge.app)

    bridge.state.update({
        "status": "OB",
        "grid": "GridDown",
        "soe": 45.0,
        "last_notified": "Never",
        "provider": "Mock Provider",
        "providers": [{"name": "Mock Provider", "soe": 45.0, "grid_connected": False}],
    })
    response = client.get("/")

    assert response.status_code == 200
    assert "UPS Bridge Status" in response.text
    assert "Battery: 45.0%" in response.text
