"""Mock Home Assistant core module."""

from unittest.mock import MagicMock
from typing import Any, Callable, Coroutine
import asyncio


class HomeAssistant:
    """Mock HomeAssistant class."""
    
    def __init__(self):
        self.data = {}
        self.config_entries = MagicMock()
        self.bus = MagicMock()
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in current thread, create one
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
    def async_create_background_task(self, coro, name):
        """Create a background task."""
        task = asyncio.create_task(coro)
        task.set_name(name)
        return task
    
    def async_add_executor_job(self, target, *args):
        """Add an executor job."""
        return target(*args)


class callback:
    """Mock callback decorator."""
    
    def __init__(self, func):
        self.func = func
        
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class ConfigEntryState:
    """Mock ConfigEntryState."""
    LOADED = "loaded"
    NOT_LOADED = "not_loaded"
    FAILED_UNLOAD = "failed_unload"
