# Home Assistant Integration Architecture

## Overview

The Tesla Powerwall UPS Bridge Home Assistant integration provides real-time monitoring of Tesla Powerwall battery systems. It connects to the bridge service using Server-Sent Events (SSE) for push-based updates with automatic fallback to polling.

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Home Assistant Instance                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Tesla UPS Integration                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │   │
│  │  │   Sensors    │  │ Binary       │  │    Data Coordinator      │ │   │
│  │  │  (6 entities)│  │ Sensors      │  │  ┌──────────────────────┐ │ │   │
│  │  │              │  │ (2 entities) │  │  │   SSE Listener       │ │ │   │
│  │  │ • Battery %  │  │              │  │  │  - Event streaming    │ │ │   │
│  │  │ • UPS Status │  │ • On Battery │  │  │  - Reconnection      │ │ │   │
│  │  │ • Grid State │  │ • Low Batt   │  │  │  - Fallback polling  │ │ │   │
│  │  │ • Last Notify│  │              │  │  └──────────────────────┘ │ │   │
│  │  │ • Provider   │  │              │  │  ┌──────────────────────┐ │ │   │
│  │  │ • Last Update│  │              │  │  │   REST API Client    │ │ │   │
│  │  └──────────────┘  └──────────────┘  │  │  - Polling fallback  │ │ │   │
│  │                                        │  │  - Initial fetch     │ │ │   │
│  │  ┌──────────────┐                     │  └──────────────────────┘ │ │   │
│  │  │ Config Flow  │                     └─────────────────────────────┘ │   │
│  │  │ (UI Setup)   │                                                  │   │
│  │  └──────────────┘                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼ SSE / REST                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Tesla Powerwall UPS Bridge                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  FastAPI Application                                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │   │
│  │  │ /api/status  │  │ /api/events  │  │ Background Poller        │  │   │
│  │  │ (REST)       │  │ (SSE)        │  │  ┌────────────────────┐  │  │   │
│  │  │              │  │              │  │  │ Polls every 15s    │  │  │   │
│  │  │ Returns:     │  │ Streams:     │  │  │ Updates NUT file   │  │  │   │
│  │  │ • status     │  │ • status_    │  │  │ Broadcasts SSE   │  │  │   │
│  │  │ • soe        │  │   update     │  │  │ Sends alerts       │  │  │   │
│  │  │ • grid       │  │ • connected  │  │  └────────────────────┘  │  │   │
│  │  │ • provider   │  │              │  │                           │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼ HTTP
┌─────────────────────────────────────────────────────────────────────────────┐
│                         pypowerwall Proxy                                   │
│                    (Tesla Powerwall API)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Flow

### 1. Configuration Flow (`config_flow.py`)

```text
User opens HA Settings
         │
         ▼
   Add Integration
         │
         ▼
  ┌──────────────┐
  │  User Form   │ ── Enter bridge URL (e.g., http://bridge:8000)
  └──────────────┘
         │
         ▼
  ┌──────────────┐
  │   Validate   │ ── Test connection to /api/status
  │   Bridge URL │
  └──────────────┘
         │
    ┌────┴────┐
    │         │
  Success   Failure
    │         │
    ▼         ▼
 Create    Show error
 Config    "cannot_connect"
 Entry
```

### 2. Data Flow - SSE Mode (Preferred)

```text
┌─────────────────┐     ┌─────────────┐     ┌─────────────────┐
│  Bridge Polls   │────▶│  State      │────▶│  Broadcast to   │
│  Powerwall      │     │  Update     │     │  SSE Queue      │
│  (every 15s)    │     │             │     │                 │
└─────────────────┘     └─────────────┘     └─────────────────┘
                                                      │
                              ┌───────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Coordinator    │
                    │  SSE Listener   │ ◀─── Persistent connection
                    │                 │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ async_set_      │
                    │ updated_data()  │
                    └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │  Sensor   │   │  Sensor   │   │  Binary   │
        │  Battery  │   │  Status   │   │  Sensor   │
        │  %        │   │           │   │  On Batt  │
        └───────────┘   └───────────┘   └───────────┘
```

### 3. Data Flow - Polling Mode (Fallback)

```text
When SSE fails:

┌─────────────────┐
│  SSE Connection │─── Connection error
│  Attempt        │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Enable Polling │─── Set update_interval = 15s
│  Mode           │
└─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Timer Triggers │────▶│  REST API Call │─── GET /api/status
│  (every 15s)    │     │                │
└─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Update     │
                        │  Entities   │
                        └─────────────┘
```

## Class Hierarchy

```text
homeassistant.helpers.update_coordinator.DataUpdateCoordinator
                              │
                              │ inherits
                              ▼
                  TeslaUPSDataUpdateCoordinator
                              │
                              │ uses
                              ▼
                    ┌─────────────────────┐
                    │   async_start_sse() │─── SSE listener task
                    │   async_stop_sse()  │
                    │   _async_update_    │─── REST fallback
                    │   data()            │
                    └─────────────────────┘
                              │
                              │ provides data to
                              ▼
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────┐
│  Coordinator  │   │  Coordinator  │   │  Coordinator      │
│  Entity       │◄──┤  Entity       │◄──┤  Entity           │
│  (sensor.py)  │   │  (sensor.py)  │   │  (binary_sensor.py)│
└───────────────┘   └───────────────┘   └───────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────┐
│  TeslaUPS     │   │  TeslaUPS     │   │  TeslaUPS         │
│  Sensor       │   │  Sensor       │   │  BinarySensor     │
│               │   │               │   │                   │
│ • native_     │   │ • native_     │   │ • is_on           │
│   value       │   │   value       │   │ • icon (dynamic)  │
│ • icon        │   │ • icon        │   │ • device_class    │
│   (dynamic)   │   │   (dynamic)   │   │                   │
└───────────────┘   └───────────────┘   └───────────────────┘
```

## Entity Descriptions

### Sensors (`sensor.py`)

| Entity | Key | Unit | Device Class | State Class | Dynamic Icon |
| -------- | ----- | ------ | -------------- | ------------- | -------------- |
| Battery Charge | `battery_charge` | % | BATTERY | MEASUREMENT | No |
| UPS Status | `ups_status` | - | - | - | Yes (plug/battery/alert) |
| Grid State | `grid_state` | - | - | - | Yes (tower on/off) |
| Last Notification | `last_notification` | - | - | - | No |
| Provider | `provider` | - | - | - | No (disabled by default) |
| Last Update | `last_update` | - | - | - | No (disabled by default) |

### Binary Sensors (`binary_sensor.py`)

| Entity | Key | Device Class | Dynamic Icon |
| -------- | ----- | -------------- | -------------- |
| On Battery | `on_battery` | POWER | Yes (plug-off/battery) |
| Low Battery | `low_battery` | BATTERY | Yes (battery/alert) |

## SSE Protocol

### Connection

```text
GET /api/events HTTP/1.1
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

### Event Format

```text
data: {"event": "status_update", "data": {"status": "OB", "soe": 65.0, ...}, "timestamp": 1234567890}

:data: {"event": "connected", "data": {"status": "OL", "soe": 85.0, ...}}

:keepalive

```

### Event Types

| Event | Description | Trigger |
| ------- | ------------- | --------- |
| `connected` | Initial state on connection | Client connects |
| `status_update` | State has changed | Bridge poll cycle |

## Error Handling

### SSE Connection Failures

```text
┌─────────────────┐
│  Connection     │
│  Attempt        │
└─────────────────┘
         │
    ┌────┴────┐
    │         │
  Success   Failure
    │         │
    ▼         ▼
  SSE Mode  ┌───────────────┐
            │  Exponential  │
            │  Backoff      │─── Retry after 5s, 10s, 20s, ..., 60s max
            │  (max 60s)    │
            └───────────────┘
                      │
            ┌─────────┴─────────┐
            │                   │
       After 3 failures    After max retries
            │                   │
            ▼                   ▼
    ┌───────────────┐   ┌───────────────┐
    │  Continue     │   │  Fallback to  │
    │  Retry        │   │  Polling Mode │
    └───────────────┘   └───────────────┘
```

### Entity Availability

```text
┌─────────────────┐
│  last_update_   │─── Check coordinator
│  success        │
└─────────────────┘
         │
    ┌────┴────┐
    │         │
   True      False
    │         │
    ▼         ▼
┌───────┐  ┌───────┐
│ State │  │ "unavailable" │
│ Value │  └───────┘
└───────┘
```

## Integration Lifecycle

### Setup

```text
HA Startup / Integration Added
              │
              ▼
       ┌──────────────┐
       │ async_setup_ │
       │ entry()      │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Create       │
       │ Coordinator  │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Initial      │─── Verify bridge reachable
       │ Refresh      │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Start SSE    │─── Background task
       │ Listener     │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Setup        │─── sensor, binary_sensor
       │ Platforms    │
       └──────────────┘
```

### Teardown

```text
HA Shutdown / Integration Removed
              │
              ▼
       ┌──────────────┐
       │ async_unload_│
       │ entry()      │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Stop SSE     │─── Cancel task
       │ Listener     │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Unload       │
       │ Platforms    │
       └──────────────┘
              │
              ▼
       ┌──────────────┐
       │ Clean up     │
       │ Resources    │
       └──────────────┘
```

## Device Registry

```text
Device: Tesla Powerwall UPS Bridge
├── Manufacturer: Tesla
├── Model: Powerwall
├── SW Version: 1.0.0
├── Identifiers: {(DOMAIN, entry_id)}
│
├── Entities:
│   ├── sensor.tesla_ups_battery_charge
│   ├── sensor.tesla_ups_ups_status
│   ├── sensor.tesla_ups_grid_state
│   ├── sensor.tesla_ups_last_notification
│   ├── sensor.tesla_ups_provider (disabled)
│   ├── sensor.tesla_ups_last_update (disabled)
│   ├── binary_sensor.tesla_ups_on_battery
│   └── binary_sensor.tesla_ups_low_battery
```

## Performance Considerations

1. **SSE Keepalive**: 30-second timeout with `:keepalive` comments prevents connection drops
2. **Reconnection Backoff**: Exponential backoff prevents hammering the bridge
3. **No Polling in SSE Mode**: CPU/network efficient when SSE is active
4. **Entity Update Debouncing**: Only update entities when data actually changes
5. **Lazy Platform Loading**: Platforms loaded only after coordinator is ready
