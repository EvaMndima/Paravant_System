#!/usr/bin/env python
"""Live-paper validation report.

Reads paper_trading_sessions from the configured database (Neon in prod,
SQLite locally) and prints per-strategy and per-session statistics needed
to decide whether a strategy is ready for live promotion.

This is read-only. It NEVER writes to the database. Safe to run on a
cron, on demand, or as part of a deploy gate.

Usage:
    # Console report (default)
    python -m scripts.validation_report

    # JSON output for downstream tools
    python -m scripts.validation_report --json

    # Only strategies with N >= N
    python -m scripts.validation_report --min-trades 10

    # Telegram-friendly compact summary
    python -m scripts.validation_report --compact

    # Run as a Railway cron (e.g. once a day) — sends summary to Telegram
    python -m scripts.validation_report --telegram

Promotion gate (from DEC-2026-05-27-004):
    READY_FOR_LIVE  N >= 30 AND PF >= 1.35 AND Sharpe >= 1.0 AND MaxDD <= 5%
    OBSERVING       N >= 10 AND PF >= 1.0
    DEGRADED        N >= 10 AND PF <  0.8
    RESEARCH        Otherwise (insufficient sample)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from src.data.database import get_db, init_db
from src.data.models.paper_session import PaperTradingSession
from src.utils.logging import get_logger, setup_logging

setup_logging(level="WARNING")
logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# Promotion gate thresholds — single source of truth.
# Decision: DEC-2026-05-27-004.
# -----------------------------------------------------------------------------
PROMOTION_GATE: dict[str, float | int] = {
    "ready_min_trades": 30,
    "ready_min_pf": 1.35,
    "ready_min_sharpe": 1.0,
    "ready_max_dd_pct": 5.0,
    "observing_min_trades": 10,
    "observing_min_pf": 1.0,
    "degraded_min_trades": 10,
    "degraded_max_pf": 0.8,
}


@dataclass(frozen=True)
class SessionStats:
    """Computed live-paper statistics for one session."""

    session_id: str
    template_id: str
    symbol: str
    initial_capital: float
    cash: float
    total_trades: int
    wins: int
    losses: int
    win_rate_pct: float
    realized_pnl: float
    profit_factor: float
    sharpe_per_trade: float
    avg_win: float
    avg_loss: float
    max_drawdown_pct: float
    days_active: float
    classification: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON output."""
        return asdict(self)


def _safe_div(numerator: float, denominator: float) -> float:
    """Return numerator/denominator or 0.0 if denominator is zero."""
    return numerator / denominator if denominator else 0.0


def _profit_factor(wins_sum: float, losses_sum: float) -> float:
    """Profit factor = gross wins / abs(gross losses).

    Returns 0 if no wins. Returns +inf if wins but zero losses (handled
    by replacing with a large sentinel for display).
    """
    abs_losses = abs(losses_sum)
    if abs_losses == 0:
        return float("inf") if wins_sum > 0 else 0.0
    return wins_sum / abs_losses


def _sharpe_per_trade(returns: list[float]) -> float:
    """Return Sharpe ratio computed on per-trade percentage returns.

    This is a per-trade Sharpe (not annualized) — comparable across
    strategies with different trade frequencies, and what most quant
    desks use for paper validation.
    """
    if len(returns) < 2:
        return 0.0
    mu = statistics.mean(returns)
    sigma = statistics.stdev(returns)
    return _safe_div(mu, sigma)


def _max_drawdown_pct(realized_pnls: list[float], starting_capital: float) -> float:
    """Compute max drawdown as a % of starting capital from a sequence of PnLs."""
    if not realized_pnls:
        return 0.0
    cumulative = starting_capital
    peak = starting_capital
    max_dd = 0.0
    for pnl in realized_pnls:
        cumulative += pnl
        peak = max(peak, cumulative)
        dd = peak - cumulative
        dd_pct = _safe_div(dd, peak) * 100.0
        max_dd = max(max_dd, dd_pct)
    return max_dd


def _classify(
    n: int, pf: float, sharpe: float, max_dd_pct: float
) -> str:
    """Apply the promotion-gate rules to classify a session."""
    g = PROMOTION_GATE
    if (
        n >= g["ready_min_trades"]
        and pf >= g["ready_min_pf"]
        and sharpe >= g["ready_min_sharpe"]
        and max_dd_pct <= g["ready_max_dd_pct"]
    ):
        return "READY_FOR_LIVE"
    if (
        n >= g["degraded_min_trades"]
        and pf < g["degraded_max_pf"]
    ):
        return "DEGRADED"
    if (
        n >= g["observing_min_trades"]
        and pf >= g["observing_min_pf"]
    ):
        return "OBSERVING"
    return "RESEARCH"


def compute_session_stats(session: PaperTradingSession) -> SessionStats:
    """Compute all live-paper statistics for one DB row."""
    trades = session.trade_log or []
    pnls = [float(t.get("realized_pnl", 0.0)) for t in trades]
    returns_pct = [float(t.get("return_pct", 0.0)) for t in trades]
    wins_list = [p for p in pnls if p > 0]
    losses_list = [p for p in pnls if p <= 0]
    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    days_active = (datetime.now(timezone.utc) - started).total_seconds() / 86400.0

    n = len(pnls)
    realized_pnl = sum(pnls)
    pf = _profit_factor(sum(wins_list), sum(losses_list))
    sharpe = _sharpe_per_trade(returns_pct)
    max_dd = _max_drawdown_pct(pnls, session.initial_capital)
    wr = _safe_div(len(wins_list), n) * 100.0
    avg_w = statistics.mean(wins_list) if wins_list else 0.0
    avg_l = statistics.mean(losses_list) if losses_list else 0.0
    classification = _classify(n, pf, sharpe, max_dd)

    return SessionStats(
        session_id=session.session_id,
        template_id=session.template_id,
        symbol=session.symbol,
        initial_capital=session.initial_capital,
        cash=session.cash,
        total_trades=n,
        wins=len(wins_list),
        losses=len(losses_list),
        win_rate_pct=wr,
        realized_pnl=realized_pnl,
        profit_factor=pf,
        sharpe_per_trade=sharpe,
        avg_win=avg_w,
        avg_loss=avg_l,
        max_drawdown_pct=max_dd,
        days_active=days_active,
        classification=classification,
    )


def aggregate_by_template(
    sessions: list[SessionStats],
) -> list[dict[str, Any]]:
    """Compute per-template (strategy) aggregate stats."""
    by_template: dict[str, list[SessionStats]] = {}
    for s in sessions:
        by_template.setdefault(s.template_id, []).append(s)

    rows: list[dict[str, Any]] = []
    for tmpl, items in by_template.items():
        total_trades = sum(s.total_trades for s in items)
        total_wins = sum(s.wins for s in items)
        total_pnl = sum(s.realized_pnl for s in items)
        weighted_pf_num = sum(s.profit_factor * s.total_trades for s in items
                              if math.isfinite(s.profit_factor) and s.total_trades > 0)
        weighted_pf_den = sum(s.total_trades for s in items
                              if math.isfinite(s.profit_factor) and s.total_trades > 0)
        weighted_pf = _safe_div(weighted_pf_num, weighted_pf_den)
        wr = _safe_div(total_wins, total_trades) * 100.0
        rows.append({
            "template_id": tmpl,
            "sessions": len(items),
            "total_trades": total_trades,
            "win_rate_pct": wr,
            "realized_pnl": total_pnl,
            "weighted_avg_pf": weighted_pf,
            "ready_sessions": sum(1 for s in items if s.classification == "READY_FOR_LIVE"),
            "observing_sessions": sum(1 for s in items if s.classification == "OBSERVING"),
            "degraded_sessions": sum(1 for s in items if s.classification == "DEGRADED"),
            "research_sessions": sum(1 for s in items if s.classification == "RESEARCH"),
        })
    rows.sort(key=lambda r: r["realized_pnl"])
    return rows


def load_sessions(min_trades: int = 0) -> list[SessionStats]:
    """Load all paper sessions from DB and compute stats.

    Uses the synchronous SQLAlchemy session pattern that the rest of
    the codebase uses (`get_db()` from src.data.database).
    """
    # Show which DB we're actually pointing at so silent fallback to an
    # empty local SQLite is immediately visible. Mask credentials.
    db_url = os.environ.get("DATABASE_URL") or "sqlite:///data/trading.db (local default)"
    if "@" in db_url:
        # postgres-style URL — show only the host part, not the credentials
        masked = db_url.split("@", 1)[1].split("?", 1)[0]
        print(f"[validation_report] Connecting to: <credentials hidden>@{masked}")
    else:
        print(f"[validation_report] Connecting to: {db_url}")

    init_db()
    # CRITICAL: compute stats INSIDE the session context. PaperTradingSession
    # has JSON columns (trade_log) that SQLAlchemy lazy-loads — accessing
    # them after the session closes raises DetachedInstanceError. By
    # computing stats inside the `with` block, the resulting SessionStats
    # dataclasses are plain Python objects and survive session close fine.
    with get_db() as db:
        rows = list(
            db.execute(
                select(PaperTradingSession).order_by(PaperTradingSession.session_id)
            ).scalars()
        )
        if not rows:
            print(
                "[validation_report] WARNING: 0 paper_trading_sessions rows found.\n"
                "[validation_report] If you expected production data, set DATABASE_URL "
                "to the Neon URL before running:\n"
                "[validation_report]   $env:DATABASE_URL = '<neon_url>'   (PowerShell)\n"
                "[validation_report]   export DATABASE_URL='<neon_url>'   (bash/zsh)"
            )
        all_stats = [compute_session_stats(r) for r in rows]

    if min_trades > 0:
        all_stats = [s for s in all_stats if s.total_trades >= min_trades]
    return all_stats


def _fmt_pf(pf: float) -> str:
    """Format profit factor (handle infinity gracefully)."""
    if math.isinf(pf):
        return "inf"
    return f"{pf:.2f}"


def print_console_report(sessions: list[SessionStats]) -> None:
    """Print the full report to stdout."""
    if not sessions:
        print("No paper sessions found (or none match filter).")
        return

    print("=" * 110)
    print(f"PARAVANT LIVE-PAPER VALIDATION REPORT — {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print("=" * 110)
    print(
        f"Promotion gate: "
        f"READY = N>={PROMOTION_GATE['ready_min_trades']} "
        f"AND PF>={PROMOTION_GATE['ready_min_pf']} "
        f"AND Sharpe>={PROMOTION_GATE['ready_min_sharpe']} "
        f"AND MaxDD<={PROMOTION_GATE['ready_max_dd_pct']}%"
    )
    print()

    # Per-session detail
    print("PER-SESSION:")
    print(
        f"{'session_id':<40} {'N':>4} {'WR%':>6} {'PF':>6} "
        f"{'Sharpe':>7} {'DD%':>6} {'PnL$':>9} {'Days':>5} {'Class':>14}"
    )
    print("-" * 110)
    for s in sorted(sessions, key=lambda s: (s.template_id, s.realized_pnl)):
        print(
            f"{s.session_id:<40} "
            f"{s.total_trades:>4d} "
            f"{s.win_rate_pct:>5.1f}% "
            f"{_fmt_pf(s.profit_factor):>6s} "
            f"{s.sharpe_per_trade:>7.3f} "
            f"{s.max_drawdown_pct:>5.1f}% "
            f"{s.realized_pnl:>+8.2f} "
            f"{s.days_active:>5.1f} "
            f"{s.classification:>14s}"
        )

    print()
    print("PER-TEMPLATE:")
    agg = aggregate_by_template(sessions)
    print(
        f"{'template_id':<32} {'Sess':>5} {'Trades':>7} {'WR%':>6} "
        f"{'WgtPF':>7} {'PnL$':>10} {'READY':>6} {'OBS':>5} {'DEGR':>5} {'RSCH':>5}"
    )
    print("-" * 110)
    for row in agg:
        print(
            f"{row['template_id']:<32} "
            f"{row['sessions']:>5d} "
            f"{row['total_trades']:>7d} "
            f"{row['win_rate_pct']:>5.1f}% "
            f"{row['weighted_avg_pf']:>7.2f} "
            f"{row['realized_pnl']:>+9.2f} "
            f"{row['ready_sessions']:>6d} "
            f"{row['observing_sessions']:>5d} "
            f"{row['degraded_sessions']:>5d} "
            f"{row['research_sessions']:>5d}"
        )

    # Summary
    n_ready = sum(1 for s in sessions if s.classification == "READY_FOR_LIVE")
    n_obs = sum(1 for s in sessions if s.classification == "OBSERVING")
    n_degr = sum(1 for s in sessions if s.classification == "DEGRADED")
    n_research = sum(1 for s in sessions if s.classification == "RESEARCH")
    total_pnl = sum(s.realized_pnl for s in sessions)
    total_trades = sum(s.total_trades for s in sessions)
    print()
    print(
        f"TOTALS: {len(sessions)} sessions, {total_trades} trades, "
        f"PnL ${total_pnl:+.2f}"
    )
    print(
        f"READY_FOR_LIVE={n_ready}  OBSERVING={n_obs}  "
        f"DEGRADED={n_degr}  RESEARCH={n_research}"
    )
    if n_ready == 0:
        print()
        print("[!] No sessions currently qualify for live promotion.")


def compact_text(sessions: list[SessionStats]) -> str:
    """One-paragraph summary suitable for Telegram."""
    if not sessions:
        return "Validation report: no paper sessions found."
    n_ready = sum(1 for s in sessions if s.classification == "READY_FOR_LIVE")
    n_degr = sum(1 for s in sessions if s.classification == "DEGRADED")
    total_pnl = sum(s.realized_pnl for s in sessions)
    total_trades = sum(s.total_trades for s in sessions)
    ready_list = [s.session_id for s in sessions if s.classification == "READY_FOR_LIVE"]
    degr_list = [s.session_id for s in sessions if s.classification == "DEGRADED"]
    parts = [
        f"Sessions: {len(sessions)} | Trades: {total_trades} | PnL: ${total_pnl:+.2f}",
        f"READY_FOR_LIVE: {n_ready}" + (f" ({', '.join(ready_list)})" if ready_list else ""),
        f"DEGRADED: {n_degr}" + (f" ({', '.join(degr_list)})" if degr_list else ""),
    ]
    return "\n".join(parts)


async def send_telegram_summary(text: str) -> None:
    """Send the compact summary as a Telegram alert (best-effort)."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("[telegram] BOT_TOKEN or CHAT_ID not set; skipping send.")
        return
    from src.core.alerting.channels.telegram import TelegramChannel
    from src.core.alerting.manager import Alert, AlertLevel
    tg = TelegramChannel(bot_token=bot_token, chat_id=chat_id)
    try:
        await tg.send(Alert(
            level=AlertLevel.INFO,
            title="Validation Report",
            message=text,
        ))
    finally:
        await tg.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Live-paper validation report")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of console table")
    parser.add_argument("--compact", action="store_true",
                        help="Output one-paragraph summary (Telegram-friendly)")
    parser.add_argument("--telegram", action="store_true",
                        help="Send compact summary to Telegram and exit")
    parser.add_argument("--min-trades", type=int, default=0,
                        help="Filter to sessions with at least N trades")
    args = parser.parse_args()

    sessions = load_sessions(min_trades=args.min_trades)

    if args.json:
        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "promotion_gate": PROMOTION_GATE,
            "sessions": [s.to_dict() for s in sessions],
            "per_template": aggregate_by_template(sessions),
        }
        print(json.dumps(out, indent=2, default=str))
        return

    if args.compact or args.telegram:
        summary = compact_text(sessions)
        print(summary)
        if args.telegram:
            asyncio.run(send_telegram_summary(summary))
        return

    print_console_report(sessions)


if __name__ == "__main__":
    main()
