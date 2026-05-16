"""Data coordinator for Tesla Powerwall UPS Bridge integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

# These imports require Home Assistant environment
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator  # type: ignore

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, EVENT_STATUS_UPDATE

_LOGGER = logging.getLogger(__name__)


class TeslaUPSDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data updates from Tesla UPS Bridge."""

    def __init__(
        self,
        hass: HomeAssistant,
        bridge_url: str,
    ) -> None:
        """Initialize the coordinator."""
        self.bridge_url = bridge_url.rstrip("/")
        self.sse_url = f"{self.bridge_url}/api/events"
        self.status_url = f"{self.bridge_url}/api/status"
        self._sse_task: asyncio.Task | None = None
        self._connected = False
        self._sse_available = True

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # We use SSE for updates, not polling
        )
        # Explicitly set update_interval to None after super().__init__
        self.update_interval = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data via REST API as fallback."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.status_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        data["connection_status"] = "polling"
                        return data
                    else:
                        raise Exception(f"HTTP {response.status}")
        except Exception as err:
            _LOGGER.error("Failed to fetch data from bridge: %s", err)
            return {
                "status": "UNKNOWN",
                "soe": 0.0,
                "grid": "Unknown",
                "provider": "unknown",
                "connection_status": "disconnected",
                "error": str(err),
            }

    async def async_start_sse(self) -> None:
        """Start the SSE listener in background."""
        if self._sse_task is None or self._sse_task.done():
            self._sse_task = self.hass.async_create_background_task(
                self._sse_listener(), f"{DOMAIN}_sse_listener"
            )

    async def async_stop_sse(self) -> None:
        """Stop the SSE listener."""
        if self._sse_task and not self._sse_task.done():
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
            self._sse_task = None

    async def _sse_listener(self) -> None:
        """Listen for SSE events from the bridge."""
        retry_delay = 5
        max_retry_delay = 60

        while True:
            try:
                _LOGGER.debug("Connecting to SSE endpoint: %s", self.sse_url)
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.sse_url,
                        headers={"Accept": "text/event-stream"},
                        timeout=aiohttp.ClientTimeout(total=None, sock_read=60),
                    ) as response:
                        if response.status != 200:
                            _LOGGER.warning(
                                "SSE endpoint returned %d, falling back to polling",
                                response.status,
                            )
                            self._sse_available = False
                            # Enable polling updates
                            self.update_interval = asyncio.timedelta(
                                seconds=DEFAULT_SCAN_INTERVAL
                            )
                            await self.async_request_refresh()
                            await asyncio.sleep(retry_delay)
                            continue

                        _LOGGER.info("SSE connection established")
                        self._connected = True
                        self._sse_available = True
                        # Disable polling since we have SSE
                        self.update_interval = None

                        # Read SSE stream line by line
                        buffer = ""
                        async for chunk in response.content.iter_chunked(1024):
                            if not chunk:
                                continue
                            buffer += chunk.decode("utf-8")

                            # Process complete lines
                            while "\n\n" in buffer:
                                message, buffer = buffer.split("\n\n", 1)
                                await self._process_sse_message(message)

            except asyncio.CancelledError:
                _LOGGER.debug("SSE listener cancelled")
                raise
            except Exception as err:
                _LOGGER.warning("SSE connection error: %s", err)
                self._connected = False

                # Fall back to polling if SSE fails
                if self._sse_available:
                    _LOGGER.info("Falling back to polling mode")
                    self._sse_available = False
                    self.update_interval = asyncio.timedelta(
                        seconds=DEFAULT_SCAN_INTERVAL
                    )
                    await self.async_request_refresh()

                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    async def _process_sse_message(self, message: str) -> None:
        """Process an SSE message."""
        data_line = None
        for line in message.strip().split("\n"):
            if line.startswith("data: "):
                data_line = line[6:]  # Remove 'data: ' prefix
                break

        if not data_line:
            return

        # Handle keepalive comments
        if data_line.startswith(":"):
            return

        try:
            event = json.loads(data_line)
            event_type = event.get("event", "")
            event_data = event.get("data", {})

            if event_type == EVENT_STATUS_UPDATE or event_type == "connected":
                # Add connection status to the data
                event_data["connection_status"] = "connected"
                self.async_set_updated_data(event_data)

        except json.JSONDecodeError as err:
            _LOGGER.debug("Failed to parse SSE data: %s - %s", data_line, err)

    @property
    def connection_status(self) -> str:
        """Return the current connection status."""
        if self.data:
            return self.data.get("connection_status", "unknown")
        return "unknown"

    @property
    def is_connected(self) -> bool:
        """Return True if connected via SSE or polling."""
        return self.connection_status in ("connected", "polling")
