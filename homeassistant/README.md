# Tesla Powerwall UPS Bridge - Home Assistant Integration

This custom component integrates the Tesla Powerwall UPS Bridge with Home Assistant, providing real-time monitoring of your Tesla Powerwall battery and grid status.

## Features

- **Real-time updates** via Server-Sent Events (SSE) from the bridge
- **Sensors**:
  - Battery charge percentage
  - UPS status (OL = on line, OB = on battery, OB LB = on battery low)
  - Grid state (connected or down)
  - Last notification time
  - Provider name
  - Last update timestamp
- **Binary Sensors**:
  - On battery (grid outage detection)
  - Low battery alert
- **Automatic fallback** to polling if SSE connection fails
- **Device registry** integration for easy entity management

## Installation

1. Copy the `tesla_ups` folder to your Home Assistant `custom_components` directory:
   ```bash
   cp -r homeassistant/tesla_ups /config/custom_components/
   ```

2. Restart Home Assistant

3. Go to **Settings > Devices & Services > Add Integration**

4. Search for "Tesla Powerwall UPS Bridge"

5. Enter the bridge URL (e.g., `http://homeassistant.local:8000` or `http://192.168.1.100:8000`)

## Configuration

The integration is configured entirely through the UI. During setup, you'll need:

- **Bridge URL**: The URL where your Tesla Powerwall UPS Bridge is running (default: `http://homeassistant.local:8000`)

## Architecture

```
Tesla Powerwall -> pypowerwall proxy -> bridge.py -> SSE endpoint
                                                    |
                                                    v
                                           Home Assistant (this integration)
                                                    |
                                                    v
                                              Real-time sensors
```

## Requirements

- Home Assistant 2023.7.0 or later
- Tesla Powerwall UPS Bridge running and accessible from Home Assistant
- The bridge must have the SSE endpoint enabled (added in this implementation)

## Troubleshooting

### Entities not updating

Check the Home Assistant logs for connection errors. The integration will:
1. First try to connect via SSE for real-time updates
2. Fall back to polling every 15 seconds if SSE fails
3. Show "unavailable" if both methods fail

### Bridge not reachable

Ensure:
- The bridge container is running (`docker ps` on the host)
- The bridge URL is correct and accessible from Home Assistant
- No firewall rules blocking port 8000 between HA and the bridge

## File Structure

```
custom_components/tesla_ups/
├── __init__.py          # Integration setup and teardown
├── binary_sensor.py     # Binary sensors (on battery, low battery)
├── config_flow.py       # UI configuration flow
├── const.py            # Constants and configuration keys
├── coordinator.py       # SSE client and data coordinator
├── manifest.json       # Integration metadata
├── sensor.py           # Sensors (battery %, status, grid state)
└── strings.json        # UI translations
```

## Acknowledgments

This integration relies on several excellent open source projects:

- **[PyPowerwall](https://github.com/jasonacox/pypowerwall)** by Jason Cox - Tesla Powerwall proxy
- **[NUT UPS Daemon](https://github.com/instantlinux/docker-nut-upsd)** by Rich Braun - UPS monitoring
- **Home Assistant** - Integration framework

See [ATTRIBUTIONS.md](../ATTRIBUTIONS.md) for complete third-party credits and licenses.
