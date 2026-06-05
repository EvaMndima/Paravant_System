#!/usr/bin/env python
"""Strategy card CLI -- pretty-print a strategy biography (spec Section 14).

Renders a strategy's canonical biography YAML
(``research/biographies/{active,retired}/<id>.yaml``) to the terminal so the
operator can review a strategy without opening YAML files or generating
markdown. READ-ONLY: never writes to any biography or other file.

Usage:
    python -m scripts.show_strategy <strategy_id> [options]

Options:
    --section <name>   Show only one section:
                         hypothesis | parameters | optimization | backtest |
                         paper | live | decay | post_mortem | decisions | validation
    --history          Show full history rather than current-state-only.
    --verbose          Include all fields, including null/empty.
    --json             Output the raw biography as JSON.
    --no-color         Disable ANSI color (also auto-disabled when not a TTY).

Design (spec Section 14.4):
    - Read-only; stdlib + PyYAML only.
    - Fast: reads one YAML file, no DB queries.
    - Graceful: an unknown id lists available strategies and exits cleanly.
    - Tolerant: renders from the raw dict so a partial biography (e.g. one with
      only retrospective-DSR sections populated) still displays without error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BIOGRAPHIES_DIR = REPO_ROOT / "research" / "biographies"


class Palette:
    """ANSI color codes, with a no-op mode for pipes / ``--no-color``."""

    def __init__(self, enabled: bool) -> None:
        """Initialize the palette.

        Args:
            enabled: Whether ANSI codes are emitted. When False, every helper
                returns the text unchanged.
        """
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def green(self, text: str) -> str:
        """Return ``text`` in green (used for Tier A / passing floors)."""
        return self._wrap("32", text)

    def yellow(self, text: str) -> str:
        """Return ``text`` in yellow (used for Tier B / Tier C)."""
        return self._wrap("33", text)

    def red(self, text: str) -> str:
        """Return ``text`` in red (used for Tier D / failing floors)."""
        return self._wrap("31", text)

    def bold(self, text: str) -> str:
        """Return ``text`` in bold."""
        return self._wrap("1", text)

    def dim(self, text: str) -> str:
        """Return ``text`` dimmed."""
        return self._wrap("2", text)

    def tier(self, tier_value: str) -> str:
        """Colorize a tier label by severity.

        Args:
            tier_value: A tier string (e.g. ``TIER_A_FULL_READY``).

        Returns:
            The tier label wrapped in the appropriate color.
        """
        upper = tier_value.upper()
        if upper.startswith("TIER_A"):
            return self.green(tier_value)
        if upper.startswith("TIER_B") or upper.startswith("TIER_C"):
            return self.yellow(tier_value)
        return self.red(tier_value)


def available_strategy_ids() -> list[str]:
    """List available biography ids from active/ and retired/ directories.

    Returns:
        Sorted unique strategy ids (file stems) found in either directory.
    """
    ids: set[str] = set()
    for sub in ("active", "retired"):
        directory = BIOGRAPHIES_DIR / sub
        if directory.exists():
            for path in directory.glob("*.yaml"):
                ids.add(path.stem)
    return sorted(ids)


def find_biography_path(strategy_id: str) -> Path | None:
    """Find the biography file for a strategy id.

    Args:
        strategy_id: The strategy id (file stem).

    Returns:
        The path if found in active/ or retired/, else None.
    """
    for sub in ("active", "retired"):
        path = BIOGRAPHIES_DIR / sub / f"{strategy_id}.yaml"
        if path.exists():
            return path
    return None


def load_biography(path: Path) -> dict[str, Any]:
    """Load a biography YAML into a dict.

    Args:
        path: Path to the biography YAML.

    Returns:
        The parsed mapping (empty dict if the file is empty).
    """
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _rule(char: str = "=", width: int = 72) -> str:
    """Return a horizontal rule of the given character and width."""
    return char * width


def _latest_validation(bio: dict[str, Any]) -> dict[str, Any] | None:
    """Return the most recent statistical-validation entry, or None."""
    history = bio.get("statistical_validation_history") or []
    return history[-1] if history else None


def render_summary(bio: dict[str, Any], pal: Palette) -> str:
    """Render the default current-state summary (spec Section 14.2).

    Args:
        bio: The biography mapping.
        pal: The color palette.

    Returns:
        The summary text (kept compact -- the latest validation is the headline).
    """
    strategy_id = bio.get("strategy_id", "?")
    status = bio.get("status", "?")
    classification = str(bio.get("current_classification") or "UNCLASSIFIED")

    lines = [
        _rule(),
        f"  Strategy: {pal.bold(str(strategy_id))}",
        f"  Status: {status}",
        f"  Current Classification: {pal.tier(classification)}",
        _rule(),
        "",
    ]

    lines += _render_hypothesis_block(bio, compact=True)
    lines += _render_parameters_block(bio, compact=True)
    lines += _render_validation_block(bio, pal)
    lines += _render_live_block(bio, compact=True)
    lines += _render_lifecycle_summary(bio)
    lines += _render_recent_decisions(bio, pal)

    lines += [
        _rule(),
        f"  For full history: python -m scripts.show_strategy {strategy_id} --history",
        _rule(),
    ]
    return "\n".join(lines)


def _render_hypothesis_block(bio: dict[str, Any], *, compact: bool) -> list[str]:
    """Render the hypothesis block (latest version)."""
    history = bio.get("hypothesis_history") or []
    if not history:
        return []
    latest = history[-1]
    lines = [
        "HYPOTHESIS",
        f"  Source: {latest.get('source', '-')}",
        f"  Regime Target: {latest.get('regime_target', '-')}",
        f"  Pre-Registered: PF={latest.get('expected_pf', '-')}, "
        f"Sharpe={latest.get('expected_sharpe', '-')}, "
        f"N/yr={latest.get('expected_n_per_year', '-')}",
        "",
    ]
    return lines


def _render_parameters_block(bio: dict[str, Any], *, compact: bool) -> list[str]:
    """Render the current-parameters block (latest version)."""
    history = bio.get("parameter_history") or []
    symbols = bio.get("symbols") or []
    if not history and not symbols:
        return []
    lines = ["CURRENT PARAMETERS"]
    if history:
        latest = history[-1]
        lines.append(f"  Version: {latest.get('version', '-')}")
        params = latest.get("params") or {}
        for key, value in params.items():
            lines.append(f"  {key}: {value}")
    if symbols:
        lines.append(f"  symbols: {symbols}")
    lines.append("")
    return lines


def _render_validation_block(bio: dict[str, Any], pal: Palette) -> list[str]:
    """Render the latest statistical-validation block (the headline)."""
    entry = _latest_validation(bio)
    if not entry:
        return ["LATEST STATISTICAL VALIDATION", "  (none recorded yet)", ""]
    gating_p = entry.get("conservative_dsr_p_value", entry.get("dsr_p_value"))
    base_p = entry.get("base_dsr_p_value")
    floor = entry.get("hard_floor_status") or {}
    dsr_floor = "PASSED" if floor.get("dsr_passed") else "FAILED"
    dd_floor = "PASSED" if floor.get("max_dd_passed") else "FAILED"
    floor_render = pal.green(dsr_floor) if floor.get("dsr_passed") else pal.red(dsr_floor)
    dd_render = pal.green(dd_floor) if floor.get("max_dd_passed") else pal.red(dd_floor)
    return [
        f"LATEST STATISTICAL VALIDATION ({entry.get('run_date', '-')})",
        f"  Cost Model: {entry.get('cost_model_version', '-')}",
        f"  PF (adjusted): {_fmt(entry.get('pf_adjusted'))}  (raw: {_fmt(entry.get('pf_raw'))})",
        f"  Sharpe (adjusted): {_fmt(entry.get('sharpe_adjusted'))}  (raw: {_fmt(entry.get('sharpe_raw'))})",
        f"  N: {entry.get('n_trades_analyzed', '-')}  "
        f"(quarantined: {entry.get('n_trades_quarantined', 0)})",
        f"  Effective K: {entry.get('effective_k', '-')}  "
        f"(gating K: {entry.get('gating_k_used', '-')})",
        f"  DSR p (gating): {_fmt(gating_p)}  [floor: {floor_render}]",
        f"  DSR p (base): {_fmt(base_p)}",
        f"  MaxDD (adjusted): {_fmt(entry.get('max_dd_pct_pooled_adjusted'))}%  [{dd_render}]",
        f"  Base tier: {pal.tier(str(entry.get('base_tier', '-')))}  ->  "
        f"Conservative: {pal.tier(str(entry.get('conservative_tier', '-')))}  "
        f"(fragile: {entry.get('verdict_is_fragile')})",
        "",
    ]


def _render_live_block(bio: dict[str, Any], *, compact: bool) -> list[str]:
    """Render the live-deployment block (latest deployment)."""
    history = bio.get("live_deployment_history") or []
    if not history:
        return []
    latest = history[-1]
    return [
        "LIVE STATUS",
        f"  Deployed: {latest.get('deployed_date', '-')}",
        f"  Capital slice: {latest.get('capital_allocation_pct', '-')}%",
        f"  Trades to date: {latest.get('trades_to_date', '-')}",
        f"  PF to date: {_fmt(latest.get('pf_to_date'))}",
        f"  Status: {latest.get('status', '-')}",
        "",
    ]


def _render_lifecycle_summary(bio: dict[str, Any]) -> list[str]:
    """Render the lifecycle counts summary."""
    return [
        "LIFECYCLE SUMMARY",
        f"  Versions: {len(bio.get('parameter_history') or [])}",
        f"  Optimization attempts: {len(bio.get('optimization_history') or [])}",
        f"  Backtests: {len(bio.get('backtest_history') or [])}",
        f"  Paper sessions: {len(bio.get('paper_trading_history') or [])}",
        f"  Validation runs: {len(bio.get('statistical_validation_history') or [])}",
        f"  Decay events: {len(bio.get('decay_events') or [])}",
        "",
    ]


def _render_recent_decisions(bio: dict[str, Any], pal: Palette, limit: int = 3) -> list[str]:
    """Render the most recent decision-log entries."""
    decisions = bio.get("decision_log") or []
    if not decisions:
        return []
    lines = ["RECENT DECISIONS"]
    for item in decisions[-limit:]:
        lines.append(f"  {pal.dim(str(item))}")
    lines.append("")
    return lines


_SECTION_KEYS: dict[str, str] = {
    "hypothesis": "hypothesis_history",
    "parameters": "parameter_history",
    "optimization": "optimization_history",
    "backtest": "backtest_history",
    "paper": "paper_trading_history",
    "live": "live_deployment_history",
    "decay": "decay_events",
    "post_mortem": "post_mortem",
    "decisions": "decision_log",
    "validation": "statistical_validation_history",
}


def render_section(bio: dict[str, Any], section: str, pal: Palette) -> str:
    """Render a single biography section (spec Section 14.3).

    Args:
        bio: The biography mapping.
        section: One of the keys in ``_SECTION_KEYS``.
        pal: The color palette.

    Returns:
        The rendered section text.
    """
    key = _SECTION_KEYS[section]
    value = bio.get(key)
    header = [
        _rule(),
        f"  Strategy: {pal.bold(str(bio.get('strategy_id', '?')))} - {section} section",
        _rule(),
        "",
    ]
    if not value:
        return "\n".join(header + ["  (empty)", _rule()])
    body = yaml.safe_dump(value, sort_keys=False, default_flow_style=False, allow_unicode=False)
    return "\n".join(header + [body, _rule()])


def _fmt(value: Any) -> str:
    """Format a numeric value to 3 significant decimals, or '-' if None."""
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    return str(value)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument vector.

    Returns:
        The parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Show a strategy biography card.")
    parser.add_argument("strategy_id", nargs="?", help="Strategy id (e.g. MACD_PB).")
    parser.add_argument("--section", choices=sorted(_SECTION_KEYS), help="Show one section.")
    parser.add_argument("--history", action="store_true", help="Show full history.")
    parser.add_argument("--verbose", action="store_true", help="Include all fields.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the strategy-card CLI.

    Args:
        argv: Optional argument vector.

    Returns:
        Process exit code (0 success; 2 on unknown / missing strategy).
    """
    args = parse_args(argv)
    color_enabled = (not args.no_color) and sys.stdout.isatty()
    pal = Palette(color_enabled)

    available = available_strategy_ids()
    if not args.strategy_id:
        print("Available strategies: " + (", ".join(available) if available else "(none)"))
        return 0

    path = find_biography_path(args.strategy_id)
    if path is None:
        print(f"Strategy {args.strategy_id!r} not found.", file=sys.stderr)
        print("Available: " + (", ".join(available) if available else "(none)"), file=sys.stderr)
        return 2

    bio = load_biography(path)

    if args.json:
        print(json.dumps(bio, indent=2, default=str))
        return 0

    if args.section:
        print(render_section(bio, args.section, pal))
        return 0

    if args.history:
        print(yaml.safe_dump(bio, sort_keys=False, default_flow_style=False, allow_unicode=False))
        return 0

    print(render_summary(bio, pal))
    if args.verbose:
        # --verbose: include all fields, including null/empty (spec Section 14.1).
        print("")
        print(_rule("-"))
        print("  FULL BIOGRAPHY (verbose)")
        print(_rule("-"))
        print(yaml.safe_dump(bio, sort_keys=False, default_flow_style=False, allow_unicode=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
