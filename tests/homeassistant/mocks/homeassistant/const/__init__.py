"""Mock Home Assistant constants module."""

from enum import Enum


class Platform(str, Enum):
    """Mock Platform enum."""
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    LIGHT = "light"


# Common constants
PERCENTAGE = "%"
CONF_URL = "url"
CONF_HOST = "host"
CONF_PORT = "port"
