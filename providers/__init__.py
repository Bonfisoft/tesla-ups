"""Provider package: factory and public exports."""

import importlib
import logging

import yaml

from providers.base import BatteryProvider, BatteryStatus

logger = logging.getLogger(__name__)

_PROVIDER_CLASS_MAP = {
    "powerwall": ("providers.powerwall", "PowerwallProvider"),
}

_DEFAULT_CONFIG_PATH = "providers.yaml"


class ConfigError(Exception):
    """Raised when the provider configuration is missing or invalid."""


def load_provider(path: str = _DEFAULT_CONFIG_PATH) -> BatteryProvider:
    """Load and instantiate the configured BatteryProvider.

    Reads *path* (a YAML file), resolves the provider module and class,
    passes the ``config`` block as keyword arguments to the constructor,
    and calls :py:meth:`BatteryProvider.health_check` before returning.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"Provider config file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc

    provider_key = cfg.get("provider", "").strip()
    if not provider_key:
        raise ConfigError("'provider' key is missing from providers.yaml")

    if provider_key not in _PROVIDER_CLASS_MAP:
        known = ", ".join(_PROVIDER_CLASS_MAP)
        raise ConfigError(
            f"Unknown provider '{provider_key}'. Known providers: {known}"
        )

    module_path, class_name = _PROVIDER_CLASS_MAP[provider_key]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    provider_config = cfg.get("config") or {}
    provider: BatteryProvider = cls(**provider_config)

    if not provider.health_check():
        logger.warning(
            "Provider '%s' health check failed at startup; continuing anyway.",
            provider.provider_name,
        )

    return provider


__all__ = ["BatteryProvider", "BatteryStatus", "load_provider", "ConfigError"]
