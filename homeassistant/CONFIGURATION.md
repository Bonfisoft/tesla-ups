# Configuration Reference

## Overview

The Tesla Powerwall UPS Bridge integration is configured entirely through the Home Assistant UI. This document describes all configuration options, entity behaviors, and customization possibilities.

## Configuration Flow

### Initial Setup

During initial setup (via `Settings > Devices & Services > Add Integration`), the following parameter is required:

| Parameter      | Required | Default                           | Description                              |
|-----------     |----------|---------                          |-------------                             |
| **Bridge URL** | Yes      | `http://homeassistant.local:8000` | Full URL to the Tesla UPS Bridge service |

### Bridge URL Formats

| Scenario                       | Example URL                      |
|----------                      | -------------                    |
| Local network IP               | `http://192.168.1.100:8000`      |
| Docker hostname (same network) | `http://powerwall-bridge:8000`   |
| Home Assistant OS add-on       | `http://ccab4aaf-tesla-ups:8000` |
| Reverse proxy (HTTPS)          | `https://ups.example.com`        |
| External domain with port      | `http://ups.example.com:8000`    |

**URL Requirements:**

- Must include protocol (`http://` or `https://`)
- Must include port if non-standard (8000 is standard)
- No trailing slash required (will be normalized)

## Entity Configuration

### Sensor Entities

#### sensor.tesla_ups_battery_charge

| Attribute | Value |
|-----------|-------|
| **Name** | Battery Charge |
| **Entity ID** | `sensor.tesla_ups_battery_charge` |
| **State Class** | measurement |
| **Device Class** | battery |
| **Unit** | % |
| **Icon** | Battery icon (dynamic based on level) |

**State Values:** 0.0 - 100.0 (percentage)

#### sensor.tesla_ups_ups_status

| Attribute | Value |
|-----------|-------|
| **Name** | UPS Status |
| **Entity ID** | `sensor.tesla_ups_ups_status` |
| **Device Class** | None |
| **Icon** | Dynamic (see below) |

**State Values:**

| Value | Meaning | Icon |
|-------|---------|------|
| `OL` | On Line (grid power) | `mdi:power-plug` |
| `OB` | On Battery (outage) | `mdi:battery` |
| `OB LB` | On Battery Low (< 15%) | `mdi:battery-alert` |
| `UNKNOWN` | Connection lost | `mdi:power-plug-off` |

#### sensor.tesla_ups_grid_state

| Attribute | Value |
|-----------|-------|
| **Name** | Grid State |
| **Entity ID** | `sensor.tesla_ups_grid_state` |
| **Icon** | Dynamic (see below) |

**State Values:**

| Value | Meaning | Icon |
|-------|---------|------|
| `SystemGridConnected` | Grid connected | `mdi:transmission-tower` |
| `GridDown` | Grid outage | `mdi:transmission-tower-off` |
| `Unknown` | State unknown | `mdi:help-circle` |

#### sensor.tesla_ups_last_notification

| Attribute | Value |
|-----------|-------|
| **Name** | Last Notification |
| **Entity ID** | `sensor.tesla_ups_last_notification` |
| **Icon** | `mdi:email-send` |

**State Values:** Time string (e.g., `14:30:25`) or `Never`

**Purpose:** Tracks when the bridge last sent an email notification about a grid outage.

#### sensor.tesla_ups_provider

| Attribute | Value |
|-----------|-------|
| **Name** | Provider |
| **Entity ID** | `sensor.tesla_ups_provider` |
| **Icon** | `mdi:information` |
| **Enabled by default** | No |

**State Values:** Provider name (e.g., `Tesla Powerwall`)

#### sensor.tesla_ups_last_update

| Attribute | Value |
|-----------|-------|
| **Name** | Last Update |
| **Entity ID** | `sensor.tesla_ups_last_update` |
| **Icon** | `mdi:clock-outline` |
| **Enabled by default** | No |

**State Values:** ISO timestamp or `None`

### Binary Sensor Entities

#### binary_sensor.tesla_ups_on_battery

| Attribute | Value |
|-----------|-------|
| **Name** | On Battery |
| **Entity ID** | `binary_sensor.tesla_ups_on_battery` |
| **Device Class** | power |
| **Icon (off)** | `mdi:power-plug-off` |
| **Icon (on)** | `mdi:battery` |

**Behavior:**

- `on` when grid is down (status is `OB` or `OB LB`)
- `off` when grid is connected (status is `OL`)

**Use Case:** Trigger automations during outages

#### binary_sensor.tesla_ups_low_battery

| Attribute | Value |
|-----------|-------|
| **Name** | Low Battery |
| **Entity ID** | `binary_sensor.tesla_ups_low_battery` |
| **Device Class** | battery |
| **Icon (off)** | `mdi:battery` |
| **Icon (on)** | `mdi:battery-alert` |

**Behavior:**

- `on` when battery is ≤ 15% AND on battery power
- `off` otherwise

**Use Case:** Critical alert before battery depletion

## Device Information

The integration creates a single device with the following properties:

| Property | Value |
|----------|-------|
| **Device Name** | Tesla Powerwall UPS Bridge |
| **Manufacturer** | Tesla |
| **Model** | Powerwall |
| **SW Version** | 1.0.0 |

All entities are associated with this device for easy management.

## Data Update Behavior

### Update Methods

The integration uses two methods to receive data:

1. **Server-Sent Events (SSE)** - Primary method
   - Persistent connection to `/api/events`
   - Real-time updates as soon as bridge detects changes
   - No polling overhead
   - Automatic reconnection with exponential backoff

2. **REST API Polling** - Fallback method
   - Activates if SSE connection fails
   - Polls every 15 seconds
   - Same data format as SSE
   - Automatically reverts to SSE when available

### Connection Status

The coordinator tracks connection state:

| Status | Meaning | Update Method |
|--------|---------|---------------|
| `connected` | SSE active | Real-time SSE |
| `polling` | SSE failed, using REST | 15s polling |
| `disconnected` | Cannot reach bridge | Entities unavailable |

## YAML Configuration Examples

### Automation Examples

#### Alert on Grid Outage

```yaml
alias: "Grid Outage Alert"
trigger:
  - platform: state
    entity_id: binary_sensor.tesla_ups_on_battery
    to: "on"
action:
  - service: notify.mobile_app_phone
    data:
      title: "Power Outage!"
      message: "Grid is down. Battery at {{ states('sensor.tesla_ups_battery_charge') }}%"
      data:
        priority: high
```

#### Critical Battery Alert

```yaml
alias: "Critical Battery Alert"
trigger:
  - platform: state
    entity_id: binary_sensor.tesla_ups_low_battery
    to: "on"
action:
  - service: notify.mobile_app_phone
    data:
      title: "CRITICAL: Low Battery"
      message: "Battery at {{ states('sensor.tesla_ups_battery_charge') }}%. Save your work!"
      data:
        priority: critical
```

#### Grid Restore Notification

```yaml
alias: "Grid Restored"
trigger:
  - platform: state
    entity_id: binary_sensor.tesla_ups_on_battery
    to: "off"
    from: "on"
action:
  - service: notify.mobile_app_phone
    data:
      title: "Power Restored"
      message: "Grid is back. Battery at {{ states('sensor.tesla_ups_battery_charge') }}%"
```

### Dashboard Card Examples

#### Battery Status Card

```yaml
type: entities
title: Tesla Powerwall Status
entities:
  - entity: sensor.tesla_ups_battery_charge
    name: Battery
  - entity: sensor.tesla_ups_ups_status
    name: UPS Status
  - entity: binary_sensor.tesla_ups_on_battery
    name: On Battery Power
  - entity: binary_sensor.tesla_ups_low_battery
    name: Low Battery Alert
  - entity: sensor.tesla_ups_grid_state
    name: Grid Connection
```

#### Battery Gauge

```yaml
type: gauge
entity: sensor.tesla_ups_battery_charge
name: Powerwall Battery
min: 0
max: 100
severity:
  green: 50
  yellow: 20
  red: 15
```

#### Conditional Status Card

```yaml
type: conditional
conditions:
  - entity: binary_sensor.tesla_ups_on_battery
    state: "on"
card:
  type: markdown
  content: |
    ## ⚠️ GRID OUTAGE
    Your home is running on battery power.

    **Battery:** {{ states('sensor.tesla_ups_battery_charge') }}%
    **Status:** {{ states('sensor.tesla_ups_ups_status') }}
```

## Advanced Configuration

### Customizing Entity Names

Entities can be renamed via the UI:

1. Go to **Settings > Devices & Services > Entities**
2. Find the entity (e.g., `sensor.tesla_ups_battery_charge`)
3. Click the entity
4. Click the gear icon
5. Change the **Name** field

### Enabling Disabled Entities

Some entities are disabled by default:

1. Go to **Settings > Devices & Services > Entities**
2. Click the filter icon
3. Select "Show disabled entities"
4. Find the disabled entity
5. Click it, then click **Enable**

### Changing Update Interval (Polling Mode)

When SSE fails and polling is active, the interval is fixed at 15 seconds. To monitor this:

```yaml
sensor:
  - platform: template
    sensors:
      tesla_ups_update_method:
        friendly_name: "Update Method"
        value_template: >
          {% if state_attr('sensor.tesla_ups_battery_charge', 'connection_status') == 'connected' %}
            Real-time (SSE)
          {% else %}
            Polling (15s)
          {% endif %}
```

### Multiple Bridge Instances

To monitor multiple Powerwalls:

1. Add first bridge:

   ```
   Settings > Devices & Services > Add Integration
   > Tesla Powerwall UPS Bridge
   > URL: http://bridge1:8000
   ```

2. Add second bridge:

   ```
   Settings > Devices & Services > Add Integration
   > Tesla Powerwall UPS Bridge
   > URL: http://bridge2:8000
   ```

Each creates separate devices with prefixed entities.

## Troubleshooting Configuration

### Verify Bridge Connection

Test from Home Assistant container:

```bash
# Test REST endpoint
curl -s http://<bridge-url>:8000/api/status | jq

# Test SSE endpoint (should stream events)
curl -N http://<bridge-url>:8000/api/events

# Check bridge health
curl -s http://<bridge-url>:8000/api/status | jq '.provider'
```

### Check Entity State Attributes

In **Developer Tools > States**, look for:

```yaml
entity_id: sensor.tesla_ups_battery_charge
state: "85.5"
attributes:
  unit_of_measurement: "%"
  device_class: battery
  friendly_name: Battery Charge
```

### Debug Logging

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tesla_ups: debug
    custom_components.tesla_ups.coordinator: debug
```

Then check logs:

```
Settings > System > Logs > Load Full Home Assistant Log
```

Look for:

- `SSE connection established`
- `Falling back to polling mode`
- `Failed to fetch data from bridge`

## Migration Notes

### From Manual YAML Configuration

If you previously used REST sensors in YAML:

1. Remove old REST sensor configuration
2. Install this integration
3. Re-create any custom template sensors referencing the old sensors

### Changing Bridge URL

To update the bridge URL:

1. Remove the integration:

   ```
   Settings > Devices & Services > Tesla Powerwall UPS Bridge
   > Three dots > Delete
   ```

2. Re-add with new URL

## Configuration Limits

| Limit | Value |
|-------|-------|
| Max bridges per HA instance | Unlimited (unique URLs) |
| Update frequency (SSE) | Real-time (as fast as bridge polls) |
| Update frequency (polling) | 15 seconds (fixed) |
| Reconnection backoff | 5s → 10s → 20s → ... → 60s max |
| SSE keepalive timeout | 30 seconds |

## Security Considerations

### Network Security

- Bridge runs on port 8000 by default
- No authentication on bridge API (designed for internal networks)
- Use firewall rules to restrict access if needed
- For external access, use reverse proxy with HTTPS

### Home Assistant Security

- Integration runs with same permissions as HA
- No secrets stored (only bridge URL)
- Config entry stored in `.storage/core.config_entries`

## API Reference

### Bridge Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/status` | GET | Initial data fetch, fallback polling |
| `/api/events` | GET | Server-Sent Events stream |

### Data Schema

```json
{
  "status": "OL|OB|OB LB",
  "soe": 85.5,
  "grid": "SystemGridConnected|GridDown",
  "provider": "Tesla Powerwall",
  "last_notified": "14:30:25",
  "connection_status": "connected|polling|disconnected"
}
```

## See Also

- [Installation Guide](INSTALLATION.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [Main Project README](../README.md)
