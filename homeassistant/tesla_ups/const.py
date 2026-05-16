"""Constants for the Tesla Powerwall UPS Bridge integration."""

DOMAIN = "tesla_ups"

CONF_BRIDGE_URL = "bridge_url"
DEFAULT_SCAN_INTERVAL = 15

# Entity naming
MANUFACTURER = "Tesla"
MODEL = "Powerwall"

# Sensor entity keys
SENSOR_BATTERY = "battery_charge"
SENSOR_STATUS = "ups_status"
SENSOR_GRID_STATE = "grid_state"
SENSOR_LAST_NOTIFICATION = "last_notification"
SENSOR_PROVIDER = "provider"
SENSOR_LAST_UPDATE = "last_update"

# Binary sensor entity keys
BINARY_ON_BATTERY = "on_battery"
BINARY_LOW_BATTERY = "low_battery"

# UPS Status values
STATUS_ONLINE = "OL"
STATUS_ON_BATTERY = "OB"
STATUS_LOW_BATTERY = "OB LB"

# Grid states
GRID_CONNECTED = "SystemGridConnected"
GRID_DOWN = "GridDown"

# SSE Events
EVENT_CONNECTED = "connected"
EVENT_STATUS_UPDATE = "status_update"
