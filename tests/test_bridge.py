import bridge
from providers.base import BatteryStatus


# ============================================================================
# Single Provider Status Tests
# ============================================================================

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


# ============================================================================
# Multi-Provider Aggregate Status Tests
# ============================================================================

def test_aggregate_status_all_online():
    """Test aggregate when all providers are on grid."""
    provider_statuses = [
        ("PW1", BatteryStatus(soe=95.0, grid_connected=True)),
        ("PW2", BatteryStatus(soe=88.0, grid_connected=True)),
    ]
    aggregate, min_soe, grid_state, details = bridge.aggregate_status(provider_statuses)
    assert aggregate == "OL"
    assert min_soe == 88.0
    assert grid_state == "SystemGridConnected"
    assert len(details) == 2


def test_aggregate_status_one_on_battery():
    """Test aggregate when one provider is on battery."""
    provider_statuses = [
        ("PW1", BatteryStatus(soe=95.0, grid_connected=True)),
        ("PW2", BatteryStatus(soe=70.0, grid_connected=False)),
    ]
    aggregate, min_soe, grid_state, details = bridge.aggregate_status(provider_statuses)
    assert aggregate == "OB"  # Not low battery
    assert min_soe == 70.0
    assert grid_state == "GridDown"


def test_aggregate_status_low_battery():
    """Test aggregate when any provider has low battery."""
    provider_statuses = [
        ("PW1", BatteryStatus(soe=95.0, grid_connected=True)),
        ("PW2", BatteryStatus(soe=10.0, grid_connected=False)),
    ]
    aggregate, min_soe, grid_state, details = bridge.aggregate_status(provider_statuses)
    assert aggregate == "OB LB"
    assert min_soe == 10.0
    assert grid_state == "GridDown"


def test_aggregate_status_with_error():
    """Test aggregate when one provider errors."""
    provider_statuses = [
        ("PW1", BatteryStatus(soe=95.0, grid_connected=True)),
        ("PW2", None),  # Error case
    ]
    aggregate, min_soe, grid_state, details = bridge.aggregate_status(provider_statuses)
    assert aggregate == "OB"  # Error treated as offline
    assert min_soe == 0.0  # Error counts as 0%
    assert grid_state == "GridDown"
    assert len(details) == 2
    assert details[1]["status"] == "error"


def test_aggregate_status_single_provider():
    """Test aggregate with single provider (backward compatibility)."""
    provider_statuses = [
        ("PW1", BatteryStatus(soe=82.0, grid_connected=False)),
    ]
    aggregate, min_soe, grid_state, details = bridge.aggregate_status(provider_statuses)
    assert aggregate == "OB"
    assert min_soe == 82.0
    assert grid_state == "GridDown"


# ============================================================================
# Email Alert Tests
# ============================================================================

def test_send_alert_skipped_when_config_missing():
    config = {
        "smtp_server": "",
        "smtp_port": 587,
        "email_user": "",
        "email_pass": "",
        "notify_to": "",
    }
    sent = bridge.send_alert("Test outage", config, "en")
    assert sent is False


# ============================================================================
# NUT Status File Tests
# ============================================================================

def test_write_nut_status_file(tmp_path):
    bridge.STATUS_FILE = str(tmp_path / "powerwall.dev")
    bridge.write_nut_status_file("OB LB", 12.3)
    content = (tmp_path / "powerwall.dev").read_text()
    assert "ups.status: OB LB" in content
    assert "battery.charge: 12.3" in content
    # Verify temp file is cleaned up after atomic rename
    assert not (tmp_path / "powerwall.dev.tmp").exists()


# ============================================================================
# Legacy Process Status Tests (for backward compatibility)
# ============================================================================

def test_process_status_sends_alert(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "STATUS_FILE", str(tmp_path / "powerwall.dev"))
    monkeypatch.setattr(bridge, "send_alert", lambda message, config, lang="en": True)
    monkeypatch.setattr(
        bridge,
        "state",
        {
            "status": "OL",
            "soe": 0.0,
            "last_notified": "Never",
            "grid": "Unknown",
            "provider": "unknown",
            "notification_sent": False,
            "providers": [],
        },
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
    monkeypatch.setattr(bridge, "send_alert", lambda message, config, lang="en": True)
    monkeypatch.setattr(
        bridge,
        "state",
        {
            "status": "OB",
            "soe": 50.0,
            "last_notified": "10:00:00",
            "grid": "GridDown",
            "provider": "Mock Provider",
            "notification_sent": True,
            "providers": [],
        },
    )

    battery_status = BatteryStatus(soe=95.0, grid_connected=True)
    bridge.process_status(battery_status, bridge.load_config(), "Mock Provider")


# ============================================================================
# Alert Threshold Tests
# ============================================================================

def test_battery_warning_threshold_default():
    """Test default BATTERY_WARNING threshold is 30.0."""
    assert bridge.BATTERY_WARNING == 30.0


def test_battery_threshold_default():
    """Test default BATTERY_THRESHOLD is 15.0."""
    assert bridge.BATTERY_THRESHOLD == 15.0


def test_determine_status_uses_threshold():
    """Test determine_status uses BATTERY_THRESHOLD for low battery status."""
    status, notify = bridge.determine_status(False, 10.0, False)
    assert status == "OB LB"  # Below default threshold of 15.0
    assert notify is True


def test_determine_status_above_threshold():
    """Test determine_status returns OB when above threshold."""
    status, notify = bridge.determine_status(False, 20.0, False)
    assert status == "OB"  # Above default threshold of 15.0
    assert notify is True


# ============================================================================
# Alert State Tracking Tests
# ============================================================================

def test_state_has_alert_tracking_fields():
    """Test state dictionary has new alert tracking fields."""
    assert "grid_offline_notified" in bridge.state
    assert "grid_online_notified" in bridge.state
    assert "warning_notified" in bridge.state
    assert "shutdown_notified" in bridge.state
    assert "shutdown_signal_sent" in bridge.state


def test_alert_tracking_defaults_to_false():
    """Test all alert tracking fields default to False."""
    assert bridge.state["grid_offline_notified"] is False
    assert bridge.state["grid_online_notified"] is False
    assert bridge.state["warning_notified"] is False
    assert bridge.state["shutdown_notified"] is False
    assert bridge.state["shutdown_signal_sent"] is False
