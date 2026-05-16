"""Mock Home Assistant entity_platform module."""

from typing import Callable, List
from unittest.mock import MagicMock


AddEntitiesCallback = Callable[[List], None]
