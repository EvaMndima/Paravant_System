"""Unit tests for config utilities.

Tests configuration helper functions and validation.
"""
import pytest
from pathlib import Path

from src.utils.config import (
    load_yaml_config,
    get_config_path,
    get_env_or_raise,
    get_env_or_default,
    get_env_bool,
    get_env_int,
    get_env_float,
    validate_database_url,
    get_project_root,
    get_data_dir,
    get_logs_dir,
)


class TestYamlLoading:
    """Test YAML configuration loading."""

    def test_load_yaml_config_success(self, tmp_path):
        """Test loading valid YAML configuration."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("database:\n  host: localhost\n  port: 5432")
        
        config = load_yaml_config(config_file)
        assert config["database"]["host"] == "localhost"
        assert config["database"]["port"] == 5432

    def test_load_yaml_config_file_not_found(self):
        """Test loading non-existent YAML file raises error."""
        with pytest.raises(FileNotFoundError):
            load_yaml_config(Path("/nonexistent/config.yaml"))

    def test_get_config_path(self):
        """Test getting configuration file path."""
        path = get_config_path("settings.yaml")
        assert path.name == "settings.yaml"
        assert "config" in str(path)


class TestEnvironmentVariables:
    """Test environment variable helpers."""

    def test_get_env_or_raise_success(self, monkeypatch):
        """Test getting existing environment variable."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        value = get_env_or_raise("TEST_VAR")
        assert value == "test_value"

    def test_get_env_or_raise_missing_raises(self):
        """Test missing environment variable raises error."""
        with pytest.raises(ValueError, match="Required environment variable"):
            get_env_or_raise("NONEXISTENT_VAR")

    def test_get_env_or_default(self, monkeypatch):
        """Test getting environment variable with default."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert get_env_or_default("TEST_VAR", "default") == "test_value"
        assert get_env_or_default("NONEXISTENT", "default") == "default"

    def test_get_env_bool_true_values(self, monkeypatch):
        """Test bool environment variable parsing - true values."""
        monkeypatch.setenv("BOOL_VAR", "true")
        assert get_env_bool("BOOL_VAR") is True
        
        monkeypatch.setenv("BOOL_VAR", "True")
        assert get_env_bool("BOOL_VAR") is True
        
        monkeypatch.setenv("BOOL_VAR", "1")
        assert get_env_bool("BOOL_VAR") is True
        
        monkeypatch.setenv("BOOL_VAR", "yes")
        assert get_env_bool("BOOL_VAR") is True

    def test_get_env_bool_false_values(self, monkeypatch):
        """Test bool environment variable parsing - false values."""
        monkeypatch.setenv("BOOL_VAR", "false")
        assert get_env_bool("BOOL_VAR") is False
        
        monkeypatch.setenv("BOOL_VAR", "0")
        assert get_env_bool("BOOL_VAR") is False
        
        assert get_env_bool("NONEXISTENT", default=False) is False

    def test_get_env_int(self, monkeypatch):
        """Test integer environment variable parsing."""
        monkeypatch.setenv("INT_VAR", "42")
        assert get_env_int("INT_VAR", default=0) == 42
        
        # Invalid int returns default
        monkeypatch.setenv("INT_VAR", "invalid")
        assert get_env_int("INT_VAR", default=10) == 10
        
        # Missing returns default
        assert get_env_int("NONEXISTENT", default=99) == 99

    def test_get_env_float(self, monkeypatch):
        """Test float environment variable parsing."""
        monkeypatch.setenv("FLOAT_VAR", "3.14")
        assert get_env_float("FLOAT_VAR", default=0.0) == 3.14
        
        # Invalid float returns default
        monkeypatch.setenv("FLOAT_VAR", "invalid")
        assert get_env_float("FLOAT_VAR", default=1.0) == 1.0
        
        # Missing returns default
        assert get_env_float("NONEXISTENT", default=99.9) == 99.9


class TestDatabaseValidation:
    """Test database URL validation."""

    def test_validate_database_url_valid_sqlite(self):
        """Test validation of valid SQLite URLs."""
        assert validate_database_url("sqlite:///data/trading.db") is True
        assert validate_database_url("sqlite:///path/to/db.db") is True

    def test_validate_database_url_valid_postgresql(self):
        """Test validation of valid PostgreSQL URLs."""
        assert validate_database_url("postgresql://user:pass@localhost/db") is True
        assert validate_database_url("postgresql://localhost/db") is True

    def test_validate_database_url_valid_mysql(self):
        """Test validation of valid MySQL URLs."""
        assert validate_database_url("mysql://user:pass@localhost/db") is True

    def test_validate_database_url_invalid(self):
        """Test validation rejects invalid URLs."""
        assert validate_database_url("invalid://url") is False
        assert validate_database_url("not-a-url") is False
        assert validate_database_url("") is False


class TestPathHelpers:
    """Test path helper functions."""

    def test_get_project_root(self):
        """Test getting project root directory."""
        root = get_project_root()
        assert root.exists()
        assert root.is_dir()

    def test_get_data_dir(self):
        """Test getting data directory."""
        data_dir = get_data_dir()
        assert data_dir.exists()
        assert data_dir.is_dir()
        assert data_dir.name == "data"

    def test_get_logs_dir(self):
        """Test getting logs directory."""
        logs_dir = get_logs_dir()
        assert logs_dir.exists()
        assert logs_dir.is_dir()
        assert logs_dir.name == "logs"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_load_yaml_empty_file(self, tmp_path):
        """Test loading empty YAML file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")
        
        config = load_yaml_config(config_file)
        assert config == {}

    def test_get_env_or_raise_custom_message(self):
        """Test custom error message for missing env var."""
        with pytest.raises(ValueError, match="Custom error"):
            get_env_or_raise("NONEXISTENT", error_message="Custom error")
