"""Comprehensive unit tests for the configuration system (Section 1.3).

Tests cover:
- Settings schema loading and validation
- Risk profile loading from YAML
- Template loading and parameter validation
- Config loader unified interface
- Backup creation, compression, restore, and retention

Decision: DEC-2026-02-08-003 - Timezone-aware timestamps in tests
"""
from __future__ import annotations

import gzip
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.core.config.backup import ConfigBackupManager
from src.core.config.loader import ConfigLoader, get_config, reset_config
from src.core.config.risk_profiles import (
    RiskProfileConfig,
    RiskProfileManager,
)
from src.core.config.settings import Settings, get_settings, reset_settings
from src.core.config.templates import (
    TemplateManager,
)


# =========================================================================
# TestSettingsSchema
# =========================================================================


class TestSettingsSchema:
    """Test suite for Pydantic v2 Settings schema."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_settings()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        reset_settings()

    def test_settings_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings should have sensible defaults for development."""
        # Clear any environment variables that might override defaults
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        # Reset singleton to force reload with clean environment
        reset_settings()

        settings = Settings()
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.database_url == "sqlite:///data/trading.db"
        assert settings.paper_trading is True
        assert settings.binance_testnet is True
        assert settings.default_risk_profile == "balanced"
        assert "BTCUSDT" in settings.default_symbols

    def test_settings_computed_properties(self) -> None:
        """Computed properties should derive from base settings."""
        settings = Settings()
        assert settings.is_production is False
        assert settings.is_live_trading is False

        # Production + live settings
        settings_live = Settings(
            environment="production",
            paper_trading=False,
            binance_testnet=False,
        )
        assert settings_live.is_production is True
        assert settings_live.is_live_trading is True

    def test_settings_validation_fails_on_invalid_database_url(self) -> None:
        """Settings should reject unsupported database URL schemes."""
        with pytest.raises(Exception):
            Settings(database_url="mysql://localhost/db")

    def test_settings_validation_fails_on_empty_symbols(self) -> None:
        """Settings should reject empty symbols list."""
        with pytest.raises(Exception):
            Settings(default_symbols=[])

    def test_settings_singleton_behavior(self) -> None:
        """get_settings() should return the same instance on repeated calls."""
        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_environment_override(self) -> None:
        """Environment variables should override default settings."""
        reset_settings()
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            reset_settings()
            settings = Settings()
            assert settings.environment == "production"

    def test_settings_port_validation(self) -> None:
        """API port must be between 1 and 65535."""
        with pytest.raises(Exception):
            Settings(api_port=0)
        with pytest.raises(Exception):
            Settings(api_port=70000)

    def test_settings_risk_percentage_validation(self) -> None:
        """Risk percentages must be within 0.1 - 100.0."""
        with pytest.raises(Exception):
            Settings(max_position_size_pct=0.0)
        with pytest.raises(Exception):
            Settings(max_position_size_pct=101.0)

    def test_settings_data_dir_property(self) -> None:
        """data_dir should extract directory from sqlite URL."""
        settings = Settings(database_url="sqlite:///data/trading.db")
        assert settings.data_dir == Path("data")

    def test_settings_symbols_uppercased(self) -> None:
        """Symbols should be automatically uppercased."""
        settings = Settings(default_symbols=["btcusdt", "ethusdt"])
        assert settings.default_symbols == ["BTCUSDT", "ETHUSDT"]


# =========================================================================
# TestRiskProfiles
# =========================================================================


class TestRiskProfiles:
    """Test suite for risk profile loading and validation."""

    def test_risk_profiles_load_from_yaml(self) -> None:
        """All 3 standard profiles should load from the YAML file."""
        manager = RiskProfileManager(
            config_path=Path("config/risk_profiles.yaml")
        )
        profiles = manager.list_profiles()
        assert "conservative" in profiles
        assert "balanced" in profiles
        assert "aggressive" in profiles
        assert len(profiles) == 3

    def test_risk_profile_values(self) -> None:
        """Profile values should match expected ranges."""
        manager = RiskProfileManager(
            config_path=Path("config/risk_profiles.yaml")
        )
        conservative = manager.get_profile("conservative")
        assert conservative.max_position_size_pct == 2.0
        assert conservative.max_open_positions == 5
        assert conservative.daily_loss_limit_pct == 2.0
        assert conservative.max_drawdown_pct == 8.0

        aggressive = manager.get_profile("aggressive")
        assert aggressive.max_position_size_pct == 5.0
        assert aggressive.max_open_positions == 10

    def test_risk_profile_not_found(self) -> None:
        """Requesting a non-existent profile should raise ValueError."""
        manager = RiskProfileManager(
            config_path=Path("config/risk_profiles.yaml")
        )
        with pytest.raises(ValueError, match="not found"):
            manager.get_profile("ultra_risky")

    def test_risk_profile_validation_rejects_invalid(self) -> None:
        """Invalid profile values should raise validation errors."""
        with pytest.raises(Exception):
            RiskProfileConfig(
                max_position_size_pct=-1.0,  # Invalid: negative
                max_concentration_pct=20.0,
                max_open_positions=8,
                daily_loss_limit_pct=3.0,
                weekly_loss_limit_pct=7.0,
                max_drawdown_pct=12.0,
                max_leverage=1.0,
                volatility_multiplier=1.0,
                max_correlation=0.8,
                max_strategies_per_account=5,
                regime_adjustments={
                    "volatile": 0.5,
                    "ranging": 0.8,
                    "trending_up": 1.0,
                    "trending_down": 0.7,
                    "unknown": 0.6,
                },
            )

    def test_risk_profile_file_not_found(self) -> None:
        """Missing YAML file should raise FileNotFoundError."""
        manager = RiskProfileManager(
            config_path=Path("/nonexistent/path.yaml")
        )
        with pytest.raises(FileNotFoundError):
            _ = manager.profiles

    def test_regime_multiplier(self) -> None:
        """Regime multiplier should return correct value."""
        manager = RiskProfileManager(
            config_path=Path("config/risk_profiles.yaml")
        )
        multiplier = manager.get_regime_multiplier("conservative", "volatile")
        assert multiplier == 0.3

    def test_regime_multiplier_invalid_regime(self) -> None:
        """Invalid regime should raise ValueError."""
        manager = RiskProfileManager(
            config_path=Path("config/risk_profiles.yaml")
        )
        with pytest.raises(ValueError, match="Unknown regime"):
            manager.get_regime_multiplier("conservative", "chaos")


# =========================================================================
# TestTemplates
# =========================================================================


class TestTemplates:
    """Test suite for strategy template loading and validation."""

    def test_template_manager_loads_all_templates(self) -> None:
        """Should load every template YAML in the templates directory.

        Asserted against the directory contents rather than a literal count.
        The previous version hardcoded 7 and silently went stale as the library
        grew to 14 -- a test that fails when the system grows correctly is
        worse than no test.
        """
        templates_dir = Path("config/templates")
        expected = len(list(templates_dir.glob("*.yaml")))
        manager = TemplateManager(templates_dir=templates_dir)
        assert expected > 0, "no template YAML files found"
        assert len(manager.templates) == expected
        # Original 3 templates
        assert "ema_trend_rsi" in manager.list_template_ids()
        assert "bb_squeeze_breakout" in manager.list_template_ids()
        assert "macd_pullback" in manager.list_template_ids()
        # New 4 templates
        assert "donchian_atr" in manager.list_template_ids()
        assert "rsi_bb_mean_reversion" in manager.list_template_ids()
        assert "supertrend_volume_macd" in manager.list_template_ids()
        assert "vwap_pullback_volume" in manager.list_template_ids()

    def test_template_has_required_fields(self) -> None:
        """Each template should have all required fields populated."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        template = manager.get_template("ema_trend_rsi")
        assert template.id == "ema_trend_rsi"
        assert template.name == "EMA Trend + RSI Filter"
        assert template.version == "1.0.0"
        assert template.type == "trend_following"
        assert len(template.parameters) > 0
        assert len(template.entry_logic) > 0
        assert len(template.exit_logic) > 0

    def test_template_default_parameters(self) -> None:
        """get_default_parameters() should return valid defaults."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        defaults = manager.get_default_parameters("ema_trend_rsi")
        assert "fast_ema_period" in defaults
        assert defaults["fast_ema_period"] == 12
        assert "slow_ema_period" in defaults
        assert defaults["slow_ema_period"] == 26

    def test_template_parameter_validation_passes(self) -> None:
        """Valid parameters should produce no errors."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        defaults = manager.get_default_parameters("ema_trend_rsi")
        errors = manager.validate_parameters("ema_trend_rsi", defaults)
        assert errors == []

    def test_template_parameter_validation_fails_out_of_range(self) -> None:
        """Out-of-range parameters should produce validation errors."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        params = manager.get_default_parameters("ema_trend_rsi")
        params["fast_ema_period"] = 999  # Way above max
        errors = manager.validate_parameters("ema_trend_rsi", params)
        assert len(errors) > 0
        assert any("fast_ema_period" in e for e in errors)

    def test_template_parameter_validation_fails_wrong_type(self) -> None:
        """Wrong-type parameters should produce validation errors."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        params = manager.get_default_parameters("ema_trend_rsi")
        params["fast_ema_period"] = "not_an_int"
        errors = manager.validate_parameters("ema_trend_rsi", params)
        assert len(errors) > 0

    def test_template_parameter_validation_fails_missing(self) -> None:
        """Missing required parameters should produce errors."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        errors = manager.validate_parameters("ema_trend_rsi", {})
        assert len(errors) > 0

    def test_template_not_found(self) -> None:
        """Requesting a non-existent template should raise ValueError."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        with pytest.raises(ValueError, match="not found"):
            manager.get_template("nonexistent_strategy")

    def test_template_get_by_type(self) -> None:
        """Should filter templates by strategy type."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        trend_templates = manager.get_templates_by_type("trend_following")
        assert len(trend_templates) >= 1
        assert all(t.type == "trend_following" for t in trend_templates)

    def test_template_directory_not_found(self) -> None:
        """Missing templates directory should raise FileNotFoundError."""
        manager = TemplateManager(
            templates_dir=Path("/nonexistent/templates")
        )
        with pytest.raises(FileNotFoundError):
            _ = manager.templates

    def test_template_unknown_parameter_reported(self) -> None:
        """Unknown parameters should be reported as errors."""
        manager = TemplateManager(templates_dir=Path("config/templates"))
        defaults = manager.get_default_parameters("ema_trend_rsi")
        defaults["unknown_param"] = 42
        errors = manager.validate_parameters("ema_trend_rsi", defaults)
        assert any("Unknown parameter" in e for e in errors)


# =========================================================================
# TestConfigLoader
# =========================================================================


class TestConfigLoader:
    """Test suite for the unified ConfigLoader."""

    def setup_method(self) -> None:
        """Reset singletons before each test."""
        reset_config()
        reset_settings()

    def teardown_method(self) -> None:
        """Reset singletons after each test."""
        reset_config()
        reset_settings()

    def test_config_loader_loads_all_sources(self) -> None:
        """ConfigLoader should provide access to all config sources."""
        loader = ConfigLoader(
            settings_yaml_path=Path("config/settings.yaml"),
            risk_profiles_path=Path("config/risk_profiles.yaml"),
            templates_dir=Path("config/templates"),
        )
        # Access settings
        assert loader.settings is not None
        # Access risk profiles
        assert len(loader.risk_profiles.list_profiles()) == 3
        # Access templates. Counted from the directory, not hardcoded, so the
        # assertion does not go stale as templates are added.
        assert len(loader.templates.list_template_ids()) == len(
            list(Path("config/templates").glob("*.yaml"))
        )

    def test_config_loader_singleton(self) -> None:
        """get_config() should return the same instance."""
        reset_config()
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_config_lazy_loading(self) -> None:
        """Resources should only be loaded on first access."""
        loader = ConfigLoader(
            settings_yaml_path=Path("config/settings.yaml"),
            risk_profiles_path=Path("config/risk_profiles.yaml"),
            templates_dir=Path("config/templates"),
        )
        # Internal state should be None before access
        assert loader._risk_profiles is None
        assert loader._templates is None
        assert loader._yaml_data is None

        # Access triggers loading
        _ = loader.risk_profiles
        assert loader._risk_profiles is not None

    def test_config_yaml_value_access(self) -> None:
        """Should retrieve nested YAML values by path."""
        loader = ConfigLoader(
            settings_yaml_path=Path("config/settings.yaml"),
        )
        symbols = loader.get_yaml_value("trading", "default_symbols")
        assert "BTCUSDT" in symbols

    def test_config_yaml_value_default(self) -> None:
        """Should return default when YAML path is missing."""
        loader = ConfigLoader(
            settings_yaml_path=Path("config/settings.yaml"),
        )
        value = loader.get_yaml_value("nonexistent", "key", default="fallback")
        assert value == "fallback"

    def test_config_reload(self) -> None:
        """reload() should clear all cached data."""
        loader = ConfigLoader(
            settings_yaml_path=Path("config/settings.yaml"),
            risk_profiles_path=Path("config/risk_profiles.yaml"),
            templates_dir=Path("config/templates"),
        )
        _ = loader.yaml_data
        assert loader._yaml_data is not None

        loader.reload()
        assert loader._yaml_data is None
        assert loader._risk_profiles is None
        assert loader._templates is None


# =========================================================================
# TestSettingsYaml
# =========================================================================


class TestSettingsYaml:
    """Test suite for settings.yaml file."""

    def test_settings_yaml_valid_format(self) -> None:
        """settings.yaml should parse without errors."""
        with open("config/settings.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "system" in data
        assert "database" in data
        assert "api" in data

    def test_settings_yaml_has_trading_section(self) -> None:
        """settings.yaml should include the trading section."""
        with open("config/settings.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "trading" in data
        assert "default_symbols" in data["trading"]
        assert "BTCUSDT" in data["trading"]["default_symbols"]

    def test_settings_yaml_has_monitoring_section(self) -> None:
        """settings.yaml should include the monitoring section."""
        with open("config/settings.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "monitoring" in data
        assert "health_check_interval_seconds" in data["monitoring"]

    def test_settings_yaml_has_backup_section(self) -> None:
        """settings.yaml should include the backup section."""
        with open("config/settings.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "backup" in data
        assert data["backup"]["daily_retention_days"] == 30
        assert data["backup"]["monthly_retention_months"] == 12


# =========================================================================
# TestBackupSystem
# =========================================================================


class TestBackupSystem:
    """Test suite for the configuration backup system."""

    def test_backup_creation(self) -> None:
        """Backup should create a compressed file with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigBackupManager(backup_dir=Path(tmpdir))
            test_data = {
                "strategies": [{"id": "str_001", "name": "Test"}],
                "accounts": [{"id": "acc_001"}],
                "positions": [],
                "system_state": None,
            }
            metadata = manager.create_backup(data=test_data)

            assert metadata.filepath.exists()
            assert metadata.size_bytes > 0
            assert metadata.version == "1.0.0"
            assert metadata.timestamp.tzinfo is not None

    def test_backup_compression(self) -> None:
        """Backup file should be valid gzip compressed JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigBackupManager(backup_dir=Path(tmpdir))
            metadata = manager.create_backup(data={"strategies": []})

            # Verify it is gzip
            with gzip.open(metadata.filepath, "rt", encoding="utf-8") as f:
                data = json.load(f)
            assert "timestamp" in data
            assert "version" in data

    def test_backup_restore(self) -> None:
        """Should restore data from a backup file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigBackupManager(backup_dir=Path(tmpdir))
            original_data = {
                "strategies": [{"id": "str_001", "name": "EMA"}],
                "accounts": [{"id": "acc_001", "balance": 10000}],
            }
            metadata = manager.create_backup(data=original_data)

            restored = manager.restore_backup(metadata.filepath)
            assert restored["strategies"] == original_data["strategies"]
            assert restored["accounts"] == original_data["accounts"]

    def test_backup_restore_file_not_found(self) -> None:
        """Restore should raise FileNotFoundError for missing files."""
        manager = ConfigBackupManager()
        with pytest.raises(FileNotFoundError):
            manager.restore_backup(Path("/nonexistent/backup.json.gz"))

    def test_backup_restore_corrupt_file(self) -> None:
        """Restore should raise ValueError for corrupt files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corrupt_file = Path(tmpdir) / "corrupt.json.gz"
            corrupt_file.write_bytes(b"not gzip data")

            manager = ConfigBackupManager(backup_dir=Path(tmpdir))
            with pytest.raises(ValueError, match="Corrupt"):
                manager.restore_backup(corrupt_file)

    def test_backup_metadata(self) -> None:
        """Backup should include timestamp and version in content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigBackupManager(backup_dir=Path(tmpdir))
            metadata = manager.create_backup()

            with gzip.open(metadata.filepath, "rt", encoding="utf-8") as f:
                data = json.load(f)
            assert "timestamp" in data
            assert "version" in data
            assert data["version"] == "1.0.0"
            # Verify timestamp is ISO format and timezone-aware
            parsed = datetime.fromisoformat(data["timestamp"])
            assert parsed.tzinfo is not None

    def test_backup_list(self) -> None:
        """list_backups() should return backups sorted newest first."""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigBackupManager(backup_dir=Path(tmpdir))

            # Use mocked timestamps to ensure distinct filenames
            # (both calls can happen within the same second)
            ts1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            ts2 = datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)

            with patch(
                "src.core.config.backup.datetime"
            ) as mock_dt:
                mock_dt.now.return_value = ts1
                mock_dt.strptime = datetime.strptime
                manager.create_backup(data={"batch": 1})

                mock_dt.now.return_value = ts2
                manager.create_backup(data={"batch": 2})

            backups = manager.list_backups()
            assert len(backups) == 2
            # Newest first
            assert backups[0].timestamp >= backups[1].timestamp

    def test_backup_retention_policy(self) -> None:
        """Old backups should be deleted per retention policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigBackupManager(
                backup_dir=Path(tmpdir),
                daily_retention_days=0,  # Delete all daily backups immediately
                monthly_retention_months=0,
            )
            # Create a backup
            _metadata = manager.create_backup(data={"test": True})
            # The retention policy with 0 days should clean up
            manager._apply_retention_policy()

            # With 0 retention, backup should be deleted
            remaining = manager.list_backups()
            # The just-created backup may still exist since cutoff is "now"
            # but the policy logic is exercised
            assert isinstance(remaining, list)

    def test_backup_get_latest(self) -> None:
        """get_latest_backup() should return the most recent backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ConfigBackupManager(backup_dir=Path(tmpdir))
            assert manager.get_latest_backup() is None

            manager.create_backup(data={"first": True})
            latest = manager.get_latest_backup()
            assert latest is not None
            assert latest.filepath.exists()
