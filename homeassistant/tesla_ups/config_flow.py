"""Config flow for Tesla Powerwall UPS Bridge integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

# These imports require Home Assistant environment
from homeassistant import config_entries  # type: ignore
from homeassistant.core import callback  # type: ignore
from homeassistant.data_entry_flow import FlowResult  # type: ignore

from .const import CONF_BRIDGE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_BRIDGE_URL = "http://homeassistant.local:8000"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BRIDGE_URL, default=DEFAULT_BRIDGE_URL): str,
    }
)


async def validate_bridge_url(bridge_url: str) -> dict[str, Any]:
    """Validate the bridge URL by connecting to the status endpoint.

    Returns a dict with keys:
    - valid: bool - whether the URL is valid and reachable
    - error: str | None - error message if not valid
    - info: dict | None - bridge info if valid
    """
    url = bridge_url.rstrip("/")
    status_url = f"{url}/api/status"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(status_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check if the response has expected fields
                    if "status" in data:
                        return {
                            "valid": True,
                            "error": None,
                            "info": data,
                        }
                    else:
                        return {
                            "valid": False,
                            "error": "Invalid response format from bridge",
                            "info": None,
                        }
                else:
                    return {
                        "valid": False,
                        "error": f"Bridge returned HTTP {response.status}",
                        "info": None,
                    }
    except aiohttp.ClientConnectionError:
        return {
            "valid": False,
            "error": "Could not connect to bridge. Check the URL and ensure the bridge is running.",
            "info": None,
        }
    except aiohttp.ClientError as err:
        return {
            "valid": False,
            "error": f"Connection error: {err}",
            "info": None,
        }
    except Exception as err:
        return {
            "valid": False,
            "error": f"Unexpected error: {err}",
            "info": None,
        }


class TeslaUPSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla Powerwall UPS Bridge."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            bridge_url = user_input[CONF_BRIDGE_URL]

            # Validate the bridge URL
            validation = await validate_bridge_url(bridge_url)

            if validation["valid"]:
                # Check if already configured
                await self.async_set_unique_id(bridge_url)
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(
                    title="Tesla Powerwall UPS Bridge",
                    data={CONF_BRIDGE_URL: bridge_url},
                )
            else:
                errors["base"] = "cannot_connect"
                _LOGGER.error("Failed to validate bridge: %s", validation["error"])

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TeslaUPSOptionsFlow:
        """Return the options flow handler."""
        return TeslaUPSOptionsFlow(config_entry)


class TeslaUPSOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Tesla Powerwall UPS Bridge."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
