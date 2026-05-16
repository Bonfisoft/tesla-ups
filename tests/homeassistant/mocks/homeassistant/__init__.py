"""Mock Home Assistant package for testing."""

from .core import HomeAssistant
from .const import Platform

__all__ = ["HomeAssistant", "Platform"]
