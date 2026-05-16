"""Mock Home Assistant exceptions module."""


class HomeAssistantError(Exception):
    """Base Home Assistant exception."""
    pass


class ConfigEntryNotReady(HomeAssistantError):
    """Exception raised when a config entry is not ready."""
    pass


class ConfigEntryAuthFailed(HomeAssistantError):
    """Exception raised when authentication fails."""
    pass
