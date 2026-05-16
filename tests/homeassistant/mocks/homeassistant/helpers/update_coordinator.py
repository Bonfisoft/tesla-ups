"""Mock Home Assistant update_coordinator module."""

import logging
from datetime import timedelta
from typing import Any, Generic, TypeVar
from unittest.mock import MagicMock
import asyncio

T = TypeVar("T")


class DataUpdateCoordinator(Generic[T]):
    """Mock DataUpdateCoordinator."""
    
    def __init__(
        self,
        hass,
        logger,
        name: str = None,
        update_interval: timedelta = None,
        update_method=None,
    ):
        self.hass = hass
        self.logger = logger or logging.getLogger(__name__)
        self.name = name
        self.update_interval = update_interval
        self.update_method = update_method
        self.data = None
        self.last_update_success = True
        self.last_exception = None
        
    async def async_config_entry_first_refresh(self):
        """Mock first refresh."""
        if self.update_method:
            self.data = await self.update_method()
        return self.data
        
    async def async_request_refresh(self):
        """Mock request refresh."""
        if self.update_method:
            self.data = await self.update_method()
        return self.data
        
    def async_set_updated_data(self, data):
        """Mock set updated data."""
        self.data = data
        self.last_update_success = True
        
    def async_add_listener(self, update_callback):
        """Mock add listener."""
        return MagicMock()


class CoordinatorEntity(Generic[T]):
    """Mock CoordinatorEntity."""
    
    def __init__(self, coordinator: DataUpdateCoordinator[T]):
        self.coordinator = coordinator
        
    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success
        
    async def async_added_to_hass(self):
        """Run when entity about to be added to hass."""
        pass
        
    async def async_update(self):
        """Update the entity."""
        pass
