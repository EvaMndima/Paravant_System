"""Risk profile configuration management.

Loads and validates risk profiles from YAML configuration. Each profile
defines position sizing, loss limits, leverage, and regime-specific
adjustments for a particular trading style.

Decision: DEC-2026-02-10-001 - Configuration hierarchy (portfolio -> account -> strategy)

The profile names (conservative, balanced, aggressive) must match the
RiskProfile enum values in src/data/models/account.py exactly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class RegimeAdjustments(BaseModel):
    """Regime-specific position size multipliers.

    Each value is a multiplier (0.0 - 1.0) applied to position size
    when the market is in the corresponding regime. A value of 1.0
    means full position size; 0.3 means 30% of normal size.

    Attributes:
        volatile: Multiplier for volatile market regime.
        ranging: Multiplier for ranging (sideways) market regime.
        trending_up: Multiplier for bullish trending regime.
        trending_down: Multiplier for bearish trending regime.
        unknown: Multiplier when regime is not classified.
    """

    volatile: float = Field(..., ge=0.0, le=1.0)
    ranging: float = Field(..., ge=0.0, le=1.0)
    trending_up: float = Field(..., ge=0.0, le=1.0)
    trending_down: float = Field(..., ge=0.0, le=1.0)
    unknown: float = Field(..., ge=0.0, le=1.0)


class RiskProfileConfig(BaseModel):
    """Risk profile configuration model.

    Defines all risk management parameters for a given trading style.
    Values are validated against acceptable ranges to prevent
    misconfiguration.

    Attributes:
        description: Human-readable profile description.
        max_position_size_pct: Maximum position size as % of capital.
        max_concentration_pct: Maximum exposure to a single symbol.
        max_open_positions: Maximum number of concurrent positions.
        daily_loss_limit_pct: Daily loss limit as % of capital.
        weekly_loss_limit_pct: Weekly loss limit as % of capital.
        max_drawdown_pct: Maximum drawdown before kill switch.
        max_leverage: Maximum allowed leverage (1.0 = spot only).
        volatility_multiplier: Position size adjustment for volatility.
        max_correlation: Maximum allowed correlation between positions.
        max_strategies_per_account: Maximum strategies per account.
        regime_adjustments: Regime-specific size multipliers.
    """

    description: str = Field(
        default="",
        description="Human-readable profile description",
    )

    # Position sizing
    max_position_size_pct: float = Field(
        ..., ge=0.1, le=100.0,
        description="Maximum position size (% of capital)",
    )
    max_concentration_pct: float = Field(
        ..., ge=1.0, le=100.0,
        description="Maximum concentration in single symbol (%)",
    )
    max_open_positions: int = Field(
        ..., ge=1, le=100,
        description="Maximum concurrent open positions",
    )

    # Loss limits
    daily_loss_limit_pct: float = Field(
        ..., ge=0.1, le=100.0,
        description="Daily loss limit (% of capital)",
    )
    weekly_loss_limit_pct: float = Field(
        ..., ge=0.1, le=100.0,
        description="Weekly loss limit (% of capital)",
    )
    max_drawdown_pct: float = Field(
        ..., ge=0.1, le=100.0,
        description="Maximum drawdown before kill switch (%)",
    )

    # Leverage
    max_leverage: float = Field(
        ..., ge=1.0, le=10.0,
        description="Maximum allowed leverage",
    )

    # Volatility and correlation
    volatility_multiplier: float = Field(
        ..., ge=0.0, le=5.0,
        description="Volatility-based position size multiplier",
    )
    max_correlation: float = Field(
        ..., ge=0.0, le=1.0,
        description="Maximum correlation between positions",
    )

    # Strategy limits
    max_strategies_per_account: int = Field(
        ..., ge=1, le=50,
        description="Maximum strategies per account",
    )

    # Regime adjustments
    regime_adjustments: RegimeAdjustments = Field(
        ...,
        description="Regime-specific position size multipliers",
    )

    @field_validator("weekly_loss_limit_pct")
    @classmethod
    def weekly_loss_exceeds_daily(
        cls, value: float, info: Any
    ) -> float:
        """Validate weekly loss limit is not less than daily limit.

        Args:
            value: Weekly loss limit percentage.
            info: Pydantic validation info containing other field values.

        Returns:
            Validated weekly loss limit.

        Raises:
            ValueError: If weekly limit is less than daily limit.
        """
        daily = info.data.get("daily_loss_limit_pct")
        if daily is not None and value < daily:
            raise ValueError(
                f"weekly_loss_limit_pct ({value}) must be >= "
                f"daily_loss_limit_pct ({daily})"
            )
        return value


class RiskProfileManager:
    """Manager for loading and accessing risk profiles from YAML.

    Loads risk profiles from a YAML file and provides methods to
    retrieve individual profiles by name. Profile names must match
    the RiskProfile enum values from the Account model.

    Attributes:
        config_path: Path to the risk profiles YAML file.
        profiles: Dictionary mapping profile names to configurations.
    """

    def __init__(
        self,
        config_path: Path | None = None,
    ) -> None:
        """Initialize the risk profile manager.

        Args:
            config_path: Path to the risk profiles YAML file.
                Defaults to ``config/risk_profiles.yaml``.
        """
        self.config_path = config_path or Path("config/risk_profiles.yaml")
        self._profiles: dict[str, RiskProfileConfig] = {}
        self._loaded = False

    @property
    def profiles(self) -> dict[str, RiskProfileConfig]:
        """Get all loaded profiles, loading on first access.

        Returns:
            Dictionary mapping profile names to their configurations.
        """
        if not self._loaded:
            self._load_profiles()
        return self._profiles

    def _load_profiles(self) -> None:
        """Load and validate profiles from YAML file.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If YAML content is malformed or invalid.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Risk profiles file not found: {self.config_path}"
            )

        with open(self.config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "profiles" not in data:
            raise ValueError(
                f"Invalid risk profiles file: missing 'profiles' key in "
                f"{self.config_path}"
            )

        for name, config in data["profiles"].items():
            self._profiles[str(name)] = RiskProfileConfig(**config)

        self._loaded = True

    def get_profile(self, name: str) -> RiskProfileConfig:
        """Get a risk profile by name.

        Args:
            name: Profile name (conservative, balanced, aggressive).

        Returns:
            The risk profile configuration.

        Raises:
            ValueError: If the profile name is not found.
        """
        if name not in self.profiles:
            available = ", ".join(sorted(self.profiles.keys()))
            raise ValueError(
                f"Risk profile '{name}' not found. "
                f"Available profiles: {available}"
            )
        return self.profiles[name]

    def list_profiles(self) -> list[str]:
        """List all available profile names.

        Returns:
            Sorted list of profile name strings.
        """
        return sorted(self.profiles.keys())

    def get_regime_multiplier(
        self, profile_name: str, regime: str
    ) -> float:
        """Get the position size multiplier for a specific regime.

        Args:
            profile_name: Name of the risk profile.
            regime: Current market regime string.

        Returns:
            Position size multiplier (0.0 - 1.0).

        Raises:
            ValueError: If profile or regime is not found.
        """
        profile = self.get_profile(profile_name)
        adjustments = profile.regime_adjustments.model_dump()
        if regime not in adjustments:
            raise ValueError(
                f"Unknown regime '{regime}'. "
                f"Valid regimes: {list(adjustments.keys())}"
            )
        return float(adjustments[regime])
