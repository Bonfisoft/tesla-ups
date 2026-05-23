# Installation Guide

## Prerequisites

Before installing the Home Assistant integration, ensure you have:

1. **Home Assistant** version 2023.7.0 or later (Core, Container, or OS)
2. **Tesla Powerwall UPS Bridge** running and accessible from Home Assistant
3. **Network connectivity** between Home Assistant and the bridge (port 8100)

## Quick Start

### Step 1: Verify Bridge is Running

Before installing the integration, confirm your bridge is accessible:

```bash
# From Home Assistant container/host
curl http://<bridge-ip>:8100/api/status
```

Expected response:

```json
{
  "status": "OL",
  "soe": 85.5,
  "grid": "SystemGridConnected",
  "provider": "Tesla Powerwall",
  "last_notified": "12:30:45"
}
```

### Step 2: Install the Integration

#### Method A: Manual Installation (Recommended)

1. **Copy files to custom_components:**

   ```bash
   # On Home Assistant host
   mkdir -p /config/custom_components/tesla_ups
   
   # Copy all files from the homeassistant/tesla_ups directory
   cp -r /path/to/tesla-ups/homeassistant/tesla_ups/* /config/custom_components/tesla_ups/
   ```

2. **Verify file structure:**

   ```text
   /config/custom_components/tesla_ups/
   ├── __init__.py
   ├── binary_sensor.py
   ├── config_flow.py
   ├── const.py
   ├── coordinator.py
   ├── manifest.json
   ├── sensor.py
   ├── strings.json
   └── README.md (optional)
   ```

3. **Restart Home Assistant:**

   - Go to **Settings > System > Restart**
   - Or use the Developer Tools > YAML > Restart

#### Method B: Samba/Share Installation

If using Home Assistant OS with Samba share:

1. Open the Samba share at `\\homeassistant\config`
2. Navigate to `custom_components` folder
3. Create `tesla_ups` folder
4. Copy all integration files into it
5. Restart Home Assistant via the UI

#### Method C: VS Code Server/Terminal

If using the VS Code Server add-on or Terminal:

```bash
cd /config/custom_components
mkdir -p tesla_ups
cd tesla_ups

# Copy or create each file
# (Paste content from the repository files)
```

### Step 3: Configure the Integration

1. **Open Home Assistant UI**

2. **Navigate to:**

   ```text
   Settings > Devices & Services > Add Integration
   ```

3. **Search for:** `Tesla Powerwall UPS Bridge`

4. **Enter configuration:**
   - **Bridge URL**: The URL where your bridge is running
     - Local network: `http://192.168.1.100:8100`
     - Docker internal: `http://powerwall-bridge:8100`
     - With reverse proxy: `https://ups-bridge.yourdomain.com`

5. **Submit** - The integration will test the connection

6. **Success!** - Entities will appear automatically

### Step 4: Verify Installation

1. **Check for device:**

   ```text
   Settings > Devices & Services > Tesla Powerwall UPS Bridge
   ```

2. **View entities:**
   - Go to **Settings > Devices & Services > Entities**
   - Filter by "Tesla UPS"

3. **Expected entities (8 total):**

   **Sensors:**
   - `sensor.tesla_ups_battery_charge` - Battery percentage
   - `sensor.tesla_ups_ups_status` - UPS status (OL/OB/OB LB)
   - `sensor.tesla_ups_grid_state` - Grid connection state
   - `sensor.tesla_ups_last_notification` - Last alert timestamp
   - `sensor.tesla_ups_provider` - Provider name (disabled by default)
   - `sensor.tesla_ups_last_update` - Last data update (disabled by default)

   **Binary Sensors:**
   - `binary_sensor.tesla_ups_on_battery` - Grid outage detection
   - `binary_sensor.tesla_ups_low_battery` - Low battery alert

## Docker Compose Setup

If running both Home Assistant and the bridge in Docker:

### Option 1: Same Docker Network (Recommended)

```yaml
# docker-compose.yml
version: '3.8'

services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: unless-stopped
    volumes:
      - ./ha-config:/config
      - /etc/localtime:/etc/localtime:ro
    networks:
      - ups_network
    # ... other HA config

  powerwall-bridge:
    build: ./tesla-ups
    container_name: powerwall-bridge
    restart: always
    networks:
      - ups_network
    ports:
      - "8100:8100"

networks:
  ups_network:
    driver: bridge
```

**Bridge URL for HA:** `http://powerwall-bridge:8100`

### Option 2: External Bridge

If bridge is on another host:

**Bridge URL for HA:** `http://<bridge-host-ip>:8100`

## Troubleshooting

### Integration Not Found

**Symptom:** "Tesla Powerwall UPS Bridge" doesn't appear in Add Integration

**Solutions:**

1. **Check file location:**

   ```bash
   ls -la /config/custom_components/tesla_ups/
   # Should show all 8+ files
   ```

2. **Verify manifest.json exists and is valid**

3. **Check Home Assistant logs:**

   ```text
   Settings > System > Logs
   ```

   Look for errors loading custom components

4. **Hard refresh:** Clear browser cache and reload HA

5. **Check permissions:**

   ```bash
   chmod -R 755 /config/custom_components/tesla_ups/
   ```

### Cannot Connect Error

**Symptom:** "Failed to connect" during setup

**Solutions:**

1. **Verify bridge URL:**

   ```bash
   curl http://<bridge-url>:8100/api/status
   ```

2. **Check network connectivity:**

   ```bash
   # From HA container
   ping <bridge-ip>
   nc -zv <bridge-ip> 8100
   ```

3. **Firewall rules:** Ensure port 8100 is open

4. **Docker network:** If both in Docker, use service name, not IP

### Entities Not Updating

**Symptom:** Entities show "unavailable" or stale data

**Solutions:**

1. **Check bridge logs:**

   ```bash
   docker logs powerwall-bridge
   ```

2. **Verify SSE endpoint:**

   ```bash
   curl -N http://<bridge-url>:8100/api/events
   ```

3. **Restart integration:**

   ```text
   Settings > Devices & Services > Tesla Powerwall UPS Bridge
   > Three dots > Reload
   ```

4. **Check HA logs for errors**

### Duplicate Entries

**Symptom:** "Device is already configured" error

**Solution:**

1. Remove existing entry:

   ```text
   Settings > Devices & Services > Tesla Powerwall UPS Bridge
   > Three dots > Delete
   ```

2. Restart HA

3. Re-add integration

## Uninstallation

1. **Remove integration from UI:**

   ```text
   Settings > Devices & Services > Tesla Powerwall UPS Bridge
   > Three dots > Delete
   ```

2. **Remove files:**

   ```bash
   rm -rf /config/custom_components/tesla_ups/
   ```

3. **Restart Home Assistant**

## Advanced Installation

### Development/Testing Installation

For testing changes without restarting HA:

1. Enable debug logging in `configuration.yaml`:

   ```yaml
   logger:
     logs:
       custom_components.tesla_ups: debug
   ```

2. Use the `custom_components` reload service:

   ```yaml
   service: homeassistant.reload_config_entry
   target:
     entity_id: sensor.tesla_ups_battery_charge
   ```

### Multiple Bridge Instances

To monitor multiple Powerwalls:

1. Add first bridge normally
2. Add second bridge:

   ```text
   Settings > Devices & Services > Add Integration
   > Tesla Powerwall UPS Bridge
   ```

3. Enter different bridge URL

Each creates a separate device with its own entities.

## Verification Checklist

- [ ] Files copied to `/config/custom_components/tesla_ups/`
- [ ] `manifest.json` is present and valid JSON
- [ ] Home Assistant restarted
- [ ] Integration appears in Add Integration list
- [ ] Bridge URL is accessible from HA
- [ ] Configuration completes without errors
- [ ] 8 entities appear in the device
- [ ] Entities show live data (not "unavailable")
- [ ] SSE endpoint is accessible (`/api/events`)

## Next Steps

After installation:

1. [Read the Configuration Guide](CONFIGURATION.md)
2. [Review Architecture Documentation](ARCHITECTURE.md)
3. Set up automations for outage notifications
4. Add entities to your dashboard
