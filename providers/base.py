"""Abstract base for battery provider implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BatteryStatus:
    """Normalised battery state returned by every provider."""

    soe: float
    grid_connected: bool


class BatteryProvider(ABC):
    """Common interface for battery system integrations."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of this provider, shown in the dashboard."""

    @abstractmethod
    def fetch_status(self) -> BatteryStatus:
        """Return the current battery and grid state."""

    def health_check(self) -> bool:
        """Optional connectivity check called at startup. Return False to log a warning."""
        return True
