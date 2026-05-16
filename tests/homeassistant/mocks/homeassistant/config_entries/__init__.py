"""Mock Home Assistant config_entries module."""

from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ConfigEntry:
    """Mock ConfigEntry class."""
    entry_id: str = "test_entry_id"
    domain: str = "tesla_ups"
    data: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    title: str = "Tesla UPS"
    version: int = 1
    source: str = "user"
    state: str = "loaded"
    unique_id: str = None
    
    def __post_init__(self):
        if self.unique_id is None:
            self.unique_id = self.entry_id
    
    def async_on_unload(self, func):
        """Mock async_on_unload."""
        return func


class ConfigFlowMeta(type):
    """Metaclass for ConfigFlow to support domain= keyword argument."""
    
    def __new__(mcs, name, bases, namespace, **kwargs):
        # Pop domain keyword if present
        kwargs.pop('domain', None)
        return super().__new__(mcs, name, bases, namespace)
    
    def __init__(cls, name, bases, namespace, **kwargs):
        # Pop domain keyword if present
        kwargs.pop('domain', None)
        super().__init__(name, bases, namespace)


class ConfigFlow(metaclass=ConfigFlowMeta):
    """Mock ConfigFlow base class."""
    VERSION = 1
    
    def __init__(self):
        self.hass = None
        self.handler = None
        self.context = {}
        self.unique_id = None
        
    async def async_step_user(self, user_input=None):
        """Mock user step."""
        raise NotImplementedError
        
    def async_show_form(self, step_id, data_schema=None, errors=None, description_placeholders=None):
        """Mock show form."""
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders or {}
        }
        
    def async_create_entry(self, title, data):
        """Mock create entry."""
        return {
            "type": "create_entry",
            "title": title,
            "data": data
        }
        
    def async_abort(self, reason):
        """Mock abort."""
        return {
            "type": "abort",
            "reason": reason
        }
        
    async def async_set_unique_id(self, unique_id):
        """Mock set unique id."""
        self.unique_id = unique_id
        return unique_id
        
    def _abort_if_unique_id_configured(self, updates=None):
        """Mock abort if configured."""
        pass


class OptionsFlow:
    """Mock OptionsFlow base class."""
    
    def __init__(self, config_entry):
        self.config_entry = config_entry
        
    async def async_step_init(self, user_input=None):
        """Mock init step."""
        raise NotImplementedError
        
    def async_show_form(self, step_id, data_schema=None, errors=None):
        """Mock show form."""
        return {
            "type": "form",
            "step_id": step_id,
            "errors": errors or {}
        }
        
    def async_create_entry(self, title, data):
        """Mock create entry."""
        return {
            "type": "create_entry",
            "title": title,
            "data": data
        }
