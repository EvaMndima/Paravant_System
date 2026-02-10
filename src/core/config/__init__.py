"""Configuration management for the PARAVANT Trading System.

This package provides unified access to all configuration sources:

- **Settings**: Environment variables and .env file (Pydantic v2)
- **Risk Profiles**: YAML-defined risk management profiles
- **Strategy Templates**: YAML-defined strategy parameter templates
- **Config Loader**: Unified lazy-loading interface

Usage::

    from src.core.config import get_config, get_settings

    # Access settings directly
    settings = get_settings()
    print(settings.database_url)

    # Access all config via unified loader
    config = get_config()
    profile = config.risk_profiles.get_profile("conservative")
    template = config.templates.get_template("ema_trend_rsi")
    symbols = config.get_yaml_value("trading", "default_symbols")
"""
from .loader import ConfigLoader, get_config, reset_config
from .risk_profiles import RegimeAdjustments, RiskProfileConfig, RiskProfileManager
from .settings import Settings, get_settings, reset_settings
from .templates import (
    ExpectedPerformance,
    ParameterSpec,
    StrategyTemplate,
    TemplateManager,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "reset_settings",
    # Risk Profiles
    "RiskProfileConfig",
    "RiskProfileManager",
    "RegimeAdjustments",
    # Templates
    "ParameterSpec",
    "StrategyTemplate",
    "TemplateManager",
    "ExpectedPerformance",
    # Unified Loader
    "ConfigLoader",
    "get_config",
    "reset_config",
]
