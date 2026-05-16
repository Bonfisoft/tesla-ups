"""The Tesla Powerwall UPS Bridge integration."""

from __future__ import annotations

import logging
from typing import Any

# These imports require Home Assistant environment
from homeassistant.config_entries import ConfigEntry  # type: ignore  # noqa: F401
from homeassistant.const import Platform  # type: ignore  # noqa: F401
from homeassistant.core import HomeAssistant  # type: ignore  # noqa: F401
from homeassistant.exceptions import ConfigEntryNotReady  # type: ignore  # noqa: F401

from .const import CONF_BRIDGE_URL, DOMAIN
from .coordinator import TeslaUPSDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tesla Powerwall UPS Bridge from a config entry."""
    bridge_url = entry.data[CONF_BRIDGE_URL]

    # Create the coordinator
    coordinator = TeslaUPSDataUpdateCoordinator(hass, bridge_url)

    # Do an initial refresh to verify connectivity
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as exc:
        _LOGGER.error("Failed to connect to bridge at %s: %s", bridge_url, exc)
        raise ConfigEntryNotReady(f"Failed to connect to bridge: {exc}") from exc

    # Store the coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Start the SSE listener for real-time updates
    await coordinator.async_start_sse()

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info(
        "Tesla Powerwall UPS Bridge integration setup complete for %s", bridge_url
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: TeslaUPSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Stop the SSE listener
    await coordinator.async_stop_sse()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Remove from storage
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
