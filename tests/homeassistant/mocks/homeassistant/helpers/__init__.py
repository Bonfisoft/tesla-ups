"""Mock Home Assistant helpers module."""

from unittest.mock import MagicMock


class EntityPlatform:
    """Mock EntityPlatform."""
    pass


class AddEntitiesCallback:
    """Mock AddEntitiesCallback type."""
    pass


def async_dispatcher_connect(hass, signal, target):
    """Mock dispatcher connect."""
    return MagicMock()


def async_dispatcher_send(hass, signal, *args):
    """Mock dispatcher send."""
    pass
