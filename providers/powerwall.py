"""Tesla Powerwall battery provider via the pypowerwall proxy API."""

import requests

from providers.base import BatteryProvider, BatteryStatus

_GRID_CONNECTED_VALUE = "SystemGridConnected"


class PowerwallProvider(BatteryProvider):
    """Fetches battery state from a pypowerwall proxy HTTP endpoint.

    Uses the pypowerwall system_status endpoint:
      - ``<base_url>/api/system_status`` → contains both battery energy and grid state
    """

    def __init__(self, base_url: str, timeout: int = 5) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "Tesla Powerwall"

    def fetch_status(self) -> BatteryStatus:
        """Fetch SOE and grid status from the proxy and return a BatteryStatus."""
        resp = requests.get(
            f"{self._base_url}/api/system_status", timeout=self._timeout
        )
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError as exc:
            raise ValueError(f"Invalid JSON from system_status endpoint: {resp.text[:200]}") from exc
        if data is None:
            raise ValueError("Empty response from system_status endpoint")

        # Calculate SOE from energy values
        energy_remaining = data.get("nominal_energy_remaining", 0)
        full_pack_energy = data.get("nominal_full_pack_energy", 1)
        if full_pack_energy > 0:
            soe = round((energy_remaining / full_pack_energy) * 100, 1)
        else:
            soe = 0.0

        # Get grid status
        grid_connected = data.get("system_island_state", "") == _GRID_CONNECTED_VALUE

        return BatteryStatus(soe=soe, grid_connected=grid_connected)

    def health_check(self) -> bool:
        """Return True if the system_status endpoint responds successfully."""
        try:
            response = requests.get(
                f"{self._base_url}/api/system_status", timeout=self._timeout
            )
            return response.ok
        except requests.RequestException:
            return False
