"""Configuration utilities for the PARAVANT Trading System.

This module provides helper functions for loading and validating configuration
from environment variables and YAML files.
"""
import os
from pathlib import Path
from typing import Any
import yaml  # type: ignore


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Dictionary containing the configuration

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        yaml.YAMLError: If the YAML is malformed
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        try:
            config = yaml.safe_load(f)
            return config or {}
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML config {config_path}: {e}")


def get_config_path(filename: str) -> Path:
    """
    Get the full path to a configuration file.

    Args:
        filename: Name of the configuration file (e.g., 'settings.yaml')

    Returns:
        Path object pointing to the configuration file
    """
    # Assume config files are in project_root/config/
    project_root = Path(__file__).parent.parent.parent
    config_dir = project_root / "config"
    return config_dir / filename


def get_env_or_raise(var_name: str, error_message: str | None = None) -> str:
    """
    Get an environment variable or raise an error if it doesn't exist.

    Args:
        var_name: Name of the environment variable
        error_message: Optional custom error message

    Returns:
        Value of the environment variable

    Raises:
        ValueError: If the environment variable is not set
    """
    value = os.getenv(var_name)
    if value is None:
        message = error_message or f"Required environment variable not set: {var_name}"
        raise ValueError(message)
    return value


def get_env_or_default(var_name: str, default: str) -> str:
    """
    Get an environment variable or return a default value.

    Args:
        var_name: Name of the environment variable
        default: Default value to return if variable is not set

    Returns:
        Value of the environment variable or default
    """
    return os.getenv(var_name, default)


def get_env_bool(var_name: str, default: bool = False) -> bool:
    """
    Get a boolean environment variable.

    Accepts: 'true', 'True', '1', 'yes', 'Yes' as True
    Everything else is False

    Args:
        var_name: Name of the environment variable
        default: Default boolean value if not set

    Returns:
        Boolean value
    """
    value = os.getenv(var_name)
    if value is None:
        return default

    return value.lower() in ('true', '1', 'yes')


def get_env_int(var_name: str, default: int) -> int:
    """
    Get an integer environment variable with type safety.

    Args:
        var_name: Name of the environment variable
        default: Default integer value if not set or invalid

    Returns:
        Integer value
    """
    value = os.getenv(var_name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def get_env_float(var_name: str, default: float) -> float:
    """
    Get a float environment variable with type safety.

    Args:
        var_name: Name of the environment variable
        default: Default float value if not set or invalid

    Returns:
        Float value
    """
    value = os.getenv(var_name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def validate_database_url(database_url: str) -> bool:
    """
    Validate a database URL format.

    Args:
        database_url: Database connection string

    Returns:
        True if valid, False otherwise
    """
    # Basic validation - checks for common database URL patterns
    valid_prefixes = ('sqlite:///', 'postgresql://', 'mysql://', 'mariadb://')
    return any(database_url.startswith(prefix) for prefix in valid_prefixes)


def get_project_root() -> Path:
    """
    Get the project root directory.

    Returns:
        Path object pointing to the project root
    """
    # Assumes utils is in src/utils/
    return Path(__file__).parent.parent.parent


def get_data_dir() -> Path:
    """
    Get the data directory path.

    Returns:
        Path object pointing to the data directory
    """
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """
    Get the logs directory path.

    Returns:
        Path object pointing to the logs directory
    """
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir
