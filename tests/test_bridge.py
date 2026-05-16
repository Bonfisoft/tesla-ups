import bridge
from providers.base import BatteryStatus


def test_determine_status_online():
    status, notify = bridge.determine_status(True, 100.0, False)
    assert status == "OL"
    assert notify is False


def test_determine_status_outage_not_notified():
    status, notify = bridge.determine_status(False, 50.0, False)
    assert status == "OB"
    assert notify is True


def test_determine_status_low_battery():
    status, notify = bridge.determine_status(False, 15.0, False)
    assert status == "OB LB"
    assert notify is True


def test_send_alert_skipped_when_config_missing():
    config = {"smtp_server": "", "smtp_port": 587, "email_user": "", "email_pass": "", "notify_to": ""}
    sent = bridge.send_alert("Test outage", config)
    assert sent is False


def test_write_nut_status_file(tmp_path):
    bridge.STATUS_FILE = str(tmp_path / "powerwall.dev")
    bridge.write_nut_status_file("OB LB", 12.3)
    content = (tmp_path / "powerwall.dev").read_text()
    assert "ups.status: OB LB" in content
    assert "battery.charge: 12.3" in content


def test_process_status_sends_alert(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "STATUS_FILE", str(tmp_path / "powerwall.dev"))
    monkeypatch.setattr(bridge, "send_alert", lambda message, config: True)
    monkeypatch.setattr(
        bridge,
        "state",
        {"status": "OL", "soe": 0.0, "last_notified": "Never", "grid": "Unknown", "provider": "unknown", "notification_sent": False},
    )

    battery_status = BatteryStatus(soe=82.3, grid_connected=False)
    bridge.process_status(battery_status, bridge.load_config(), "Mock Provider")

    assert bridge.state["status"] == "OB"
    assert bridge.state["soe"] == 82.3
    assert bridge.state["provider"] == "Mock Provider"
    assert bridge.state["grid"] == "GridDown"
    assert bridge.state["notification_sent"] is True
    assert (tmp_path / "powerwall.dev").exists()


def test_process_status_clears_notification_on_grid_restore(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "STATUS_FILE", str(tmp_path / "powerwall.dev"))
    monkeypatch.setattr(bridge, "send_alert", lambda message, config: True)
    monkeypatch.setattr(
        bridge,
        "state",
        {"status": "OB", "soe": 50.0, "last_notified": "10:00:00", "grid": "GridDown", "provider": "Mock Provider", "notification_sent": True},
    )

    battery_status = BatteryStatus(soe=95.0, grid_connected=True)
    bridge.process_status(battery_status, bridge.load_config(), "Mock Provider")

    assert bridge.state["status"] == "OL"
    assert bridge.state["grid"] == "SystemGridConnected"
    assert bridge.state["notification_sent"] is False
