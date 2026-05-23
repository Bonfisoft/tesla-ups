"""Tesla Powerwall battery provider via the pypowerwall proxy API."""

import requests

from providers.base import BatteryProvider, BatteryStatus

_GRID_CONNECTED_VALUE = "SystemGridConnected"


class PowerwallProvider(BatteryProvider):
    """Fetches battery state from a pypowerwall proxy HTTP endpoint.

    Uses two dedicated endpoints:
      - ``<base_url>/api/system_status/soe``          → battery percentage
      - ``<base_url>/api/system_status/grid_status``  → grid connection state
    """

    def __init__(self, base_url: str, timeout: int = 5) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "Tesla Powerwall"

    def fetch_status(self) -> BatteryStatus:
        """Fetch SOE and grid status from the proxy and return a BatteryStatus."""
        soe_resp = requests.get(
            f"{self._base_url}/api/system_status/soe", timeout=self._timeout
        )
        soe_resp.raise_for_status()
        try:
            soe_data = soe_resp.json()
        except ValueError as exc:
            raise ValueError(f"Invalid JSON from SOE endpoint: {soe_resp.text[:200]}") from exc
        if soe_data is None:
            raise ValueError("Empty response from SOE endpoint")
        soe = round(float(soe_data.get("percentage", 0.0)), 1)

        grid_resp = requests.get(
            f"{self._base_url}/api/system_status/grid_status", timeout=self._timeout
        )
        grid_resp.raise_for_status()
        try:
            grid_data = grid_resp.json()
        except ValueError as exc:
            raise ValueError(f"Invalid JSON from grid status endpoint: {grid_resp.text[:200]}") from exc
        if grid_data is None:
            raise ValueError("Empty response from grid status endpoint")
        grid_connected = grid_data.get("grid_status", "") == _GRID_CONNECTED_VALUE

        return BatteryStatus(soe=soe, grid_connected=grid_connected)

    def health_check(self) -> bool:
        """Return True if the SOE endpoint responds successfully."""
        try:
            response = requests.get(
                f"{self._base_url}/api/system_status/soe", timeout=self._timeout
            )
            return response.ok
        except requests.RequestException:
            return False
