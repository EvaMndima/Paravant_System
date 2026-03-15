"""Shared utilities for backtest comparison run scripts.

Used by run_strategy_comparison.py, run_regime_search.py, and run_final.py.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def make_strategy(variant: dict[str, Any]) -> SimpleNamespace:
    """Create a lightweight in-memory strategy object for direct engine use.

    BacktestEngine reads only: id, name, template_id, parameters.
    SimpleNamespace avoids requiring a database session while staying
    fully compatible with the engine's duck-typed interface.

    Args:
        variant: Dict with keys: id, name, template_id, parameters.

    Returns:
        SimpleNamespace acting as a Strategy duck-type.
    """
    return SimpleNamespace(
        id=variant["id"],
        name=variant["name"],
        template_id=variant["template_id"],
        parameters=variant["parameters"],
    )


def verdict(passed: bool, errors: list[str], *, width: int = 0) -> str:
    """Format a pass/fail verdict string with the first failure reason.

    Args:
        passed: Whether validation passed.
        errors: List of validation error messages.
        width: Optional padding width for the FAIL prefix (default 0 = no pad).

    Returns:
        "PASS" or "FAIL (<abbreviated first error>)".
    """
    if passed:
        return "PASS"
    first = errors[0] if errors else "unknown"
    first = (
        first
        .replace("Insufficient trades:", "trades:")
        .replace("Sharpe ratio too low:", "sharpe:")
        .replace("Max drawdown too high:", "drawdown:")
        .replace("Profit factor too low:", "PF:")
        .replace("Expectancy too low:", "expectancy:")
    )
    pad = " " * width
    return f"FAIL{pad}({first})"
