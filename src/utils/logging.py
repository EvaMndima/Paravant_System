"""Structured logging setup for the PARAVANT Trading System.

This module configures structlog for production-grade JSON logging in
production and human-readable console logging for development.

Features:
- JSON output for production (machine-parseable)
- Console output for development (human-readable)
- Sensitive data masking (API keys, passwords, tokens)
- Application context injection (app name, version)
- Context variable support via LogContext manager
- Callsite information (filename, function, line number)

Decision: DEC-2026-02-08-008 - Structured logging (JSON format)
Decision: DEC-2026-02-10-003 - Sensitive data masking in logs
"""
import logging
import sys
from typing import Any

import structlog


# ---------------------------------------------------------------------------
# Sensitive data patterns for masking
# ---------------------------------------------------------------------------

# Keys whose values should be masked in log output (show last 4 chars only)
# CRITICAL SECURITY: These values are credentials/PII and must never be logged in full
_SENSITIVE_KEYS: frozenset[str] = frozenset({
    # API credentials
    "api_key",
    "secret_key",
    "binance_api_key",
    "binance_secret_key",
    "private_key",
    "access_token",
    "refresh_token",

    # Authentication tokens
    "token",
    "bot_token",
    "telegram_bot_token",
    "authorization",
    "bearer",

    # Database credentials (HIGH-008 fix)
    "password",
    "passwd",
    "db_password",
    "database_password",
    "postgres_password",
    "mysql_password",
    "connection_string",

    # Generic sensitive terms
    "secret",
    "credential",
    "auth",
})


def mask_sensitive_data(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Mask sensitive data in log entries before rendering.

    Replaces sensitive field values with masked versions showing only
    the last 4 characters for debugging purposes. Values 4 chars or
    shorter are fully masked to prevent exposure.

    CRITICAL SECURITY: This prevents accidental credential leakage
    in log files, monitoring systems, and log aggregation services.

    Examples:
        - "sk_live_1234567890abcdef" -> "**************cdef"
        - "abc" -> "****" (fully masked - too short)
        - None -> None (unchanged)

    Args:
        logger: The wrapped logger object (unused, required by structlog).
        method_name: The log method name (unused, required by structlog).
        event_dict: The event dictionary to process.

    Returns:
        The event dictionary with sensitive values masked.
    """
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if key_lower in _SENSITIVE_KEYS:
            value = event_dict[key]
            # Only mask non-None string values
            if value is not None and isinstance(value, str):
                # CRITICAL-005 fix: Fully mask values <= 4 chars to prevent exposure
                # For "abcde" (5 chars), show "*bcde" would expose 4/5 chars - unacceptable
                if len(value) <= 4:
                    event_dict[key] = "****"
                else:
                    # Show last 4 chars for debugging (can identify which key is in use)
                    event_dict[key] = "*" * (len(value) - 4) + value[-4:]
    return event_dict


def add_app_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application context to log entries.

    Adds standard fields like app name and version to every log entry
    for filtering and identification in log aggregation systems.

    Args:
        logger: The wrapped logger object (unused, required by structlog).
        method_name: The log method name (unused, required by structlog).
        event_dict: The event dictionary to process.

    Returns:
        The event dictionary with app context fields added.
    """
    event_dict["app"] = "paravant-trading"
    event_dict["version"] = "1.0.0"
    return event_dict


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Sets up structlog with processors for timestamps, log levels,
    sensitive data masking, and application context. Configures
    the output renderer based on the environment (JSON for production,
    console for development).

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, use JSON formatting (production).
            If False, use console formatting (development).
        log_file: Optional path to a log file. Currently reserved for
            future use; logging is always to stdout.
    """
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set third-party loggers to WARNING to reduce noise
    for logger_name in [
        "urllib3",
        "httpx",
        "asyncio",
        "sqlalchemy.engine",
        "watchfiles",
        "uvicorn.access",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Shared processors for all log entries
    shared_processors: list[Any] = [
        # Add context variables from LogContext
        structlog.contextvars.merge_contextvars,
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add ISO 8601 UTC timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add application context (app name, version)
        add_app_context,
        # Mask sensitive data (API keys, passwords, tokens)
        mask_sensitive_data,
        # Add exception info if present
        structlog.processors.StackInfoRenderer(),
        # Add callsite info (filename, function, line number)
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # Choose renderer based on environment
    renderer: Any
    if json_format:
        # Production: JSON output for machine parsing
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Pretty console output for humans
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # Configure structlog
    processors = shared_processors.copy()
    if json_format:
        # Add format_exc_info for JSON output to include stack traces
        processors.append(structlog.processors.format_exc_info)
        processors.append(renderer)
    else:
        # ConsoleRenderer handles exception formatting itself
        processors.append(renderer)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    MEDIUM-007: Explicit return type for IDE autocomplete and type safety.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        Configured structlog BoundLogger instance with full type support.
    """
    # structlog.get_logger() returns Any, but we know it's BoundLogger after configure()
    return structlog.get_logger(name)  # type: ignore[no-any-return]


class LogContext:
    """Context manager for adding structured context to log entries.

    All log entries within the context will automatically include the
    provided key-value pairs. This is useful for adding correlation
    IDs or request-scoped data to all log messages.

    Example::

        with LogContext(strategy_id="str_001", account_id="acc_001"):
            logger.info("signal_generated", signal="buy")
            # Output includes strategy_id and account_id automatically

    Attributes:
        context: Dictionary of context key-value pairs.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the log context.

        Args:
            **kwargs: Key-value pairs to bind as context variables.
        """
        self.context = kwargs

    def __enter__(self) -> "LogContext":
        """Enter the context and bind context variables.

        HIGH-009 fix: Does NOT clear existing context to support nested
        LogContext usage. structlog's merge_contextvars processor merges
        contexts correctly.
        """
        # Don't call clear_contextvars() - would destroy outer context in nested usage
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and unbind context variables."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())
