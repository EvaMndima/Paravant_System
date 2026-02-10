"""Application settings schema using Pydantic v2 BaseSettings.

This module provides the main application settings loaded from environment
variables and .env files. All sensitive data (API keys, tokens) must be
stored in .env and never committed to version control.

Decision: DEC-2026-02-08-001 - Virtual environment (venv, not conda)
Decision: DEC-2026-02-08-003 - Timezone-aware timestamps throughout
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings loaded from .env and environment variables.

    All fields support environment variable override using uppercase names.
    For example, ``database_url`` can be set via the ``DATABASE_URL``
    environment variable.

    Attributes:
        environment: Deployment environment (development/staging/production).
        debug: Enable debug mode with verbose output.
        log_level: Logging verbosity level.
        database_url: SQLAlchemy database connection string.
        binance_api_key: Binance exchange API key (sensitive).
        binance_secret_key: Binance exchange secret key (sensitive).
        binance_testnet: Use Binance testnet instead of production.
        telegram_bot_token: Telegram bot token for alerts (sensitive).
        telegram_chat_id: Telegram chat ID for alert delivery.
        telegram_alerts_enabled: Enable or disable Telegram alerting.
        default_risk_profile: Default risk profile for new accounts.
        max_position_size_pct: Global maximum position size as percentage.
        max_daily_loss_pct: Global maximum daily loss as percentage.
        max_drawdown_pct: Global maximum drawdown as percentage.
        default_symbols: Default trading symbols for new strategies.
        default_timeframe: Default candlestick timeframe.
        paper_trading: Enable paper trading mode (no real orders).
        health_check_interval_seconds: Interval between health checks.
        backup_enabled: Enable automatic configuration backups.
        backup_path: Directory path for storing backups.
        api_host: API server bind host.
        api_port: API server bind port.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Environment ----------------------------------------------------------
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging verbosity level",
    )

    # -- Database -------------------------------------------------------------
    database_url: str = Field(
        default="sqlite:///data/trading.db",
        description="SQLAlchemy database connection string",
    )

    # -- Binance API (sensitive - stored in .env) -----------------------------
    binance_api_key: str | None = Field(
        default=None,
        description="Binance exchange API key",
    )
    binance_secret_key: str | None = Field(
        default=None,
        description="Binance exchange secret key",
    )
    binance_testnet: bool = Field(
        default=True,
        description="Use Binance testnet for development",
    )

    # -- Telegram Alerts (sensitive - stored in .env) -------------------------
    telegram_bot_token: str | None = Field(
        default=None,
        description="Telegram bot token for alerts",
    )
    telegram_chat_id: str | None = Field(
        default=None,
        description="Telegram chat ID for alert delivery",
    )
    telegram_alerts_enabled: bool = Field(
        default=False,
        description="Enable Telegram alerting",
    )

    # -- Risk Defaults --------------------------------------------------------
    default_risk_profile: Literal["conservative", "balanced", "aggressive"] = Field(
        default="balanced",
        description="Default risk profile for new accounts",
    )
    max_position_size_pct: float = Field(
        default=3.0,
        ge=0.1,
        le=100.0,
        description="Global maximum position size (% of capital)",
    )
    max_daily_loss_pct: float = Field(
        default=3.0,
        ge=0.1,
        le=100.0,
        description="Global maximum daily loss (% of capital)",
    )
    max_drawdown_pct: float = Field(
        default=12.0,
        ge=0.1,
        le=100.0,
        description="Global maximum drawdown (% of capital)",
    )

    # -- Trading --------------------------------------------------------------
    default_symbols: list[str] = Field(
        default=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        description="Default trading symbols",
    )
    default_timeframe: str = Field(
        default="1h",
        description="Default candlestick timeframe",
    )
    paper_trading: bool = Field(
        default=True,
        description="Enable paper trading mode (no real orders)",
    )

    # -- Monitoring -----------------------------------------------------------
    health_check_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Health check interval in seconds",
    )

    # -- Backup ---------------------------------------------------------------
    backup_enabled: bool = Field(
        default=True,
        description="Enable automatic configuration backups",
    )
    backup_path: str = Field(
        default="backups",
        description="Directory path for storing backups",
    )

    # -- API ------------------------------------------------------------------
    api_host: str = Field(
        default="0.0.0.0",
        description="API server bind host",
    )
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="API server bind port",
    )

    # -- Validators -----------------------------------------------------------

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Validate database URL is a supported format.

        Args:
            value: Database connection string to validate.

        Returns:
            Validated database URL.

        Raises:
            ValueError: If database URL scheme is not supported.
        """
        if not value.startswith(("sqlite:", "postgresql:", "postgresql+asyncpg:")):
            raise ValueError(
                f"Unsupported database URL scheme: {value.split(':')[0]}. "
                "Only sqlite and postgresql are supported."
            )
        return value

    @field_validator("default_symbols")
    @classmethod
    def validate_symbols(cls, value: list[str]) -> list[str]:
        """Validate trading symbols are non-empty and uppercase.

        Args:
            value: List of trading symbol strings.

        Returns:
            Validated and uppercased symbol list.

        Raises:
            ValueError: If symbols list is empty.
        """
        if not value:
            raise ValueError("default_symbols must not be empty")
        return [s.upper() for s in value]

    @field_validator("backup_path")
    @classmethod
    def validate_backup_path(cls, value: str) -> str:
        """Validate backup path is a valid directory path string.

        Args:
            value: Backup directory path.

        Returns:
            Validated backup path string.

        Raises:
            ValueError: If backup path is empty.
        """
        if not value.strip():
            raise ValueError("backup_path must not be empty")
        return value

    # -- Computed Properties --------------------------------------------------

    @property
    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if environment is 'production'.
        """
        return self.environment == "production"

    @property
    def is_live_trading(self) -> bool:
        """Check if live trading is enabled (real money at risk).

        Live trading requires both paper_trading=False and
        binance_testnet=False.

        Returns:
            True if live trading is active.
        """
        return not self.paper_trading and not self.binance_testnet

    @property
    def data_dir(self) -> Path:
        """Get the data directory path derived from database URL.

        Returns:
            Path to the data directory.
        """
        if self.database_url.startswith("sqlite:///"):
            db_path = Path(self.database_url.replace("sqlite:///", ""))
            return db_path.parent
        return Path("data")


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_settings_instance: Settings | None = None


def get_settings(**kwargs: str | bool | int | float | None) -> Settings:
    """Get the application settings singleton.

    On first call, creates and caches a Settings instance. Subsequent calls
    return the cached instance. Pass keyword arguments to override defaults
    (useful for testing).

    Args:
        **kwargs: Optional overrides passed to Settings constructor on
            first creation.

    Returns:
        The cached Settings instance.
    """
    global _settings_instance  # noqa: PLW0603
    if _settings_instance is None:
        _settings_instance = Settings(**kwargs)  # type: ignore[arg-type]
    return _settings_instance


def reset_settings() -> None:
    """Reset the settings singleton (for testing only).

    Clears the cached settings instance so the next call to
    ``get_settings()`` creates a fresh instance.
    """
    global _settings_instance  # noqa: PLW0603
    _settings_instance = None
