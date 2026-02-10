"""Unified configuration loader with lazy loading.

Provides a single entry point for accessing all configuration sources:
settings (from .env), risk profiles (from YAML), templates (from YAML
directory), and application YAML settings.

Decision: DEC-2026-02-10-001 - Configuration hierarchy (portfolio -> account -> strategy)
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any  # HIGH-003: Any justified - YAML values can be any JSON type

import yaml

from .risk_profiles import RiskProfileManager
from .settings import Settings, get_settings
from .templates import TemplateManager


class ConfigLoader:
    """Unified configuration loader with lazy-loaded subsystems.

    Provides properties for each configuration subsystem that are loaded
    on first access. This avoids loading all configuration up front,
    which is useful when only a subset is needed (e.g., in tests).

    Attributes:
        settings_yaml_path: Path to the main settings YAML file.
        risk_profiles_path: Path to the risk profiles YAML file.
        templates_dir: Path to the templates directory.
    """

    def __init__(
        self,
        settings_yaml_path: Path | None = None,
        risk_profiles_path: Path | None = None,
        templates_dir: Path | None = None,
    ) -> None:
        """Initialize the config loader with optional custom paths.

        Args:
            settings_yaml_path: Path to the settings YAML file.
                Defaults to ``config/settings.yaml``.
            risk_profiles_path: Path to the risk profiles YAML file.
                Defaults to ``config/risk_profiles.yaml``.
            templates_dir: Path to the templates directory.
                Defaults to ``config/templates``.
        """
        self.settings_yaml_path = settings_yaml_path or Path("config/settings.yaml")
        self.risk_profiles_path = risk_profiles_path or Path("config/risk_profiles.yaml")
        self.templates_dir = templates_dir or Path("config/templates")

        # Lazy-loaded subsystems
        self._settings: Settings | None = None
        self._risk_profiles: RiskProfileManager | None = None
        self._templates: TemplateManager | None = None
        self._yaml_data: dict[str, Any] | None = None

    @property
    def settings(self) -> Settings:
        """Get application settings (lazy loaded from .env).

        Returns:
            The Settings instance.
        """
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    @property
    def risk_profiles(self) -> RiskProfileManager:
        """Get risk profile manager (lazy loaded from YAML).

        Returns:
            The RiskProfileManager instance.
        """
        if self._risk_profiles is None:
            self._risk_profiles = RiskProfileManager(self.risk_profiles_path)
        return self._risk_profiles

    @property
    def templates(self) -> TemplateManager:
        """Get template manager (lazy loaded from YAML directory).

        Returns:
            The TemplateManager instance.
        """
        if self._templates is None:
            self._templates = TemplateManager(self.templates_dir)
        return self._templates

    @property
    def yaml_data(self) -> dict[str, Any]:
        """Get raw YAML configuration data (lazy loaded).

        Returns:
            Dictionary of parsed YAML content.

        Raises:
            FileNotFoundError: If the settings YAML file does not exist.
        """
        if self._yaml_data is None:
            if not self.settings_yaml_path.exists():
                raise FileNotFoundError(
                    f"Settings YAML file not found: {self.settings_yaml_path}"
                )
            # MEDIUM-004: Handle YAML parsing errors explicitly
            try:
                with open(self.settings_yaml_path, encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise ValueError(
                    f"Invalid YAML in {self.settings_yaml_path}: {exc}"
                ) from exc
            self._yaml_data = loaded if loaded is not None else {}
        return self._yaml_data

    def get_yaml_value(self, *keys: str, default: Any = None) -> Any:
        """Get a nested YAML value by key path.

        Traverses the YAML data dictionary using the provided keys.
        Returns the default value if any key in the path is missing.

        Args:
            *keys: Sequence of dictionary keys forming the path.
            default: Value to return if path is not found.

        Returns:
            The value at the specified path, or the default.

        Examples:
            >>> config.get_yaml_value("trading", "default_symbols")
            ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            >>> config.get_yaml_value("missing", "path", default=[])
            []
        """
        data: Any = self.yaml_data
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                return default
            data = data[key]
        return data

    def reload(self) -> None:
        """Force reload of all configuration sources.

        Clears all cached data so that the next access triggers a
        fresh load from disk. Useful after configuration files have
        been modified.
        """
        self._settings = None
        self._risk_profiles = None
        self._templates = None
        self._yaml_data = None


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

# HIGH-004: Thread-safe singleton pattern with lock to prevent race conditions
# MEDIUM-003: Global state documentation
#
# _config_instance: Cached ConfigLoader singleton (None until first get_config() call)
#                   Subsequent calls return the same instance for consistency.
#
# _config_lock: Threading lock for thread-safe singleton initialization.
#               Uses double-checked locking pattern: fast path checks without lock,
#               slow path acquires lock only during first initialization.
#               Lock minimizes contention - only held during first creation.
#
# Thread Safety: Multiple concurrent get_config() calls are safe.
#                First caller creates instance, others wait on lock and reuse.
#
_config_instance: ConfigLoader | None = None
_config_lock = threading.Lock()


def get_config(**kwargs: Any) -> ConfigLoader:  # HIGH-003: Any justified - kwargs forwarded to ConfigLoader
    """Get the configuration loader singleton (thread-safe).

    On first call, creates and caches a ConfigLoader instance.
    Subsequent calls return the cached instance.

    HIGH-004 fix: Uses double-checked locking pattern to prevent
    race conditions when multiple threads call this concurrently.

    Args:
        **kwargs: Optional keyword arguments passed to ConfigLoader
            on first creation.

    Returns:
        The cached ConfigLoader instance.
    """
    global _config_instance  # noqa: PLW0603

    # Fast path: instance already created (no lock needed)
    if _config_instance is not None:
        return _config_instance

    # Slow path: need to create instance (acquire lock)
    with _config_lock:
        # Double-check: another thread may have created it while we waited
        if _config_instance is None:
            _config_instance = ConfigLoader(**kwargs)

    return _config_instance


def reset_config() -> None:
    """Reset the configuration singleton (for testing only).

    Clears the cached ConfigLoader instance so the next call to
    ``get_config()`` creates a fresh instance.
    """
    global _config_instance  # noqa: PLW0603
    _config_instance = None
