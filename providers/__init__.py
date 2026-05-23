"""Provider package: factory and public exports."""

import importlib
import logging
import os
from typing import Any

from providers.base import BatteryProvider, BatteryStatus

logger = logging.getLogger(__name__)

_PROVIDER_CLASS_MAP = {
    "powerwall": ("providers.powerwall", "PowerwallProvider"),
}


class ConfigError(Exception):
    """Raised when the provider configuration is missing or invalid."""


def _get_env(key: str, default: str | None = None) -> str | None:
    """Get environment variable, returning None if empty."""
    value = os.getenv(key, default)
    return value if value else None


def _load_single_provider_config(
    prefix: str, default_type: str = "powerwall"
) -> dict[str, Any] | None:
    """Load a single provider configuration with the given env var prefix.

    Args:
        prefix: Environment variable prefix (e.g., "PROVIDER_1_", "PROVIDER_2_")
        default_type: Default provider type if not specified

    Returns:
        Provider config dict or None if PROXY_URL not set for this provider
    """
    proxy_url = _get_env(f"{prefix}PROXY_URL")

    if not proxy_url:
        return None

    provider_type = _get_env(f"{prefix}TYPE", default_type)
    timeout_str = _get_env(f"{prefix}TIMEOUT", "10")
    name = _get_env(f"{prefix}NAME")

    try:
        timeout = int(timeout_str)
    except ValueError:
        timeout = 10

    config: dict[str, Any] = {
        "provider": provider_type,
        "config": {
            "base_url": proxy_url,
            "timeout": timeout,
        },
    }

    if name:
        config["name"] = name

    return config


def load_provider_configs() -> list[dict[str, Any]]:
    """Load all provider configurations from environment variables.

    Supports numbered providers (PROVIDER_1_*, PROVIDER_2_*, etc.) and
    legacy single provider (PROXY_URL without number).

    Returns:
        List of provider configuration dictionaries
    """
    configs: list[dict[str, Any]] = []

    # Check for numbered providers (PROVIDER_1_PROXY_URL, etc.)
    provider_num = 1
    while True:
        prefix = f"PROVIDER_{provider_num}_"
        cfg = _load_single_provider_config(prefix)

        if cfg is None:
            # No more numbered providers found
            break

        cfg["id"] = f"provider_{provider_num}"
        configs.append(cfg)
        provider_num += 1

    # Check for legacy single provider (backward compatibility)
    if not configs:
        legacy_cfg = _load_single_provider_config("", "powerwall")
        if legacy_cfg:
            legacy_cfg["id"] = "provider_1"
            configs.append(legacy_cfg)

    if not configs:
        raise ConfigError(
            "No provider configuration found. "
            "Set PROVIDER_1_PROXY_URL or PROXY_URL environment variable."
        )

    return configs


def _instantiate_provider(cfg: dict[str, Any]) -> BatteryProvider:
    """Instantiate a single provider from its configuration."""
    provider_key = cfg.get("provider", "").strip()
    provider_id = cfg.get("id", "unknown")

    if not provider_key:
        raise ConfigError(f"Provider type not set for {provider_id}")

    if provider_key not in _PROVIDER_CLASS_MAP:
        known = ", ".join(_PROVIDER_CLASS_MAP)
        raise ConfigError(
            f"Unknown provider '{provider_key}' for {provider_id}. "
            f"Known providers: {known}"
        )

    module_path, class_name = _PROVIDER_CLASS_MAP[provider_key]
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    provider_config = cfg.get("config") or {}
    provider: BatteryProvider = cls(**provider_config)

    # Store the provider ID and custom name for reference
    provider._bridge_id = provider_id
    provider._bridge_name = cfg.get("name")

    if not provider.health_check():
        logger.warning(
            "Provider '%s' (%s) health check failed at startup; continuing anyway.",
            provider.provider_name,
            provider_id,
        )

    return provider


def load_providers() -> list[BatteryProvider]:
    """Load and instantiate all configured BatteryProviders from environment variables.

    Supports multiple providers via numbered environment variables:
    - PROVIDER_1_TYPE, PROVIDER_1_PROXY_URL, PROVIDER_1_TIMEOUT, PROVIDER_1_NAME
    - PROVIDER_2_TYPE, PROVIDER_2_PROXY_URL, PROVIDER_2_TIMEOUT, PROVIDER_2_NAME
    - etc.

    Or legacy single provider:
    - PROVIDER_TYPE, PROXY_URL, PROVIDER_TIMEOUT

    Required environment variables per provider:
    - PROXY_URL: URL to the Powerwall proxy

    Optional per provider:
    - TYPE: Provider type (default: powerwall)
    - TIMEOUT: Request timeout in seconds (default: 10)
    - NAME: Custom display name for this provider

    Returns:
        List of instantiated BatteryProvider instances
    """
    configs = load_provider_configs()
    providers: list[BatteryProvider] = []

    for cfg in configs:
        provider = _instantiate_provider(cfg)
        providers.append(provider)
        logger.info(
            "Loaded provider %s: %s (%s)",
            cfg["id"],
            provider.provider_name,
            cfg.get("config", {}).get("proxy_url", "unknown"),
        )

    logger.info("Total providers loaded: %d", len(providers))
    return providers


def load_provider() -> BatteryProvider:
    """Load a single provider (backward compatibility).

    Deprecated: Use load_providers() for multi-provider support.
    """
    providers = load_providers()
    if len(providers) > 1:
        logger.warning(
            "Multiple providers configured but only returning first one. "
            "Use load_providers() for multi-provider support."
        )
    return providers[0]


__all__ = [
    "BatteryProvider",
    "BatteryStatus",
    "load_provider",
    "load_providers",
    "ConfigError",
]
