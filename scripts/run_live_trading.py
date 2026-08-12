"""Live trading runner — real Binance orders, single session.

Runs ONE strategy-symbol pair with REAL capital via Binance Spot API.
Designed as the graduation step after paper trading validation.

Default configuration:
    Strategy: bear_trend_follower (BTF) — best performer in 60-day backtest
    Symbol:   BTCUSDT
    Capital:  Configurable via LIVE_CAPITAL_USDT env var (default $20)

Position sizing:
    Uses 25% of current account equity per trade ($5 on a $20 account), keeping
    max loss per trade around $0.50-$1.00 with ATR-based stops.
    Clears Binance minimum notional ($5 for BTCUSDT Spot).

Safety:
    - Kill switch checked before every order submission
    - Daily loss limit (10%) and max drawdown (20%) enforced as hard blocks
    - Stop-loss and take-profit enforced independently via intrabar high/low
      check every poll cycle — does not rely solely on signal generator CLOSE
    - Reads BINANCE_TESTNET env var: set "true" to test on testnet first
    - Sends Telegram alerts on every entry, exit, and risk block
    - All orders are market orders (guaranteed fills, no stuck limit orders)
    - Actual Binance fill prices recorded — PnL tracks real execution costs
    - Position state saved to SQLite + JSON backup every poll cycle
      so restarts do not cause ghost positions

Prerequisites:
    1. Binance API key with "Enable Spot & Margin Trading" permission
    2. Set env vars: BINANCE_API_KEY, BINANCE_SECRET_KEY, BINANCE_TESTNET=false
    3. Optionally: LIVE_CAPITAL_USDT (default 20), LIVE_SYMBOL (default BTCUSDT)
    4. Railway persistent volume mounted at /app/data

Usage:
    python -m scripts.run_live_trading
    LIVE_CAPITAL_USDT=50 LIVE_SYMBOL=ETHUSDT python -m scripts.run_live_trading

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import signal as signal_mod
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.brokers.binance.client import BinanceClient
from src.brokers.binance.execution import BinanceExecutionAdapter
from src.brokers.binance.rate_limiter import RateLimiter
from src.core.alerting.channels.telegram import TelegramChannel
from src.core.alerting.manager import Alert, AlertLevel
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.risk.types import OrderRequest
from src.core.strategy.regime.detector import RegimeDetector, RegimeState
from src.core.strategy.regime.historical_classifier import SubRegime
from src.core.strategy.regime.sub_regime_detector import SubRegimeDetector
from src.data.database import init_db
from src.data.market_data import OHLCV, MarketDataFetcher
from src.data.models.paper_session import PaperTradingSession
from src.data.store import DataStore
from src.utils.logging import get_logger

# Reuse the canonical promotion-gate logic from the validation report so the
# live auto-promotion gate (DEC-2026-06-01-001) and the report (DEC-2026-05-27-004)
# can never disagree. Import-safe: validation_report calls setup_logging() only
# inside its main(), not at module scope.
from scripts.validation_report import (
    _classify,
    _is_corrupt_force_close,
    _max_drawdown_pct,
    _profit_factor,
    _sharpe_per_trade,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration (all overridable via environment variables)
# ---------------------------------------------------------------------------

LIVE_CAPITAL: float = float(os.getenv("LIVE_CAPITAL_USDT", "20.0"))
LIVE_SYMBOL: str = os.getenv("LIVE_SYMBOL", "BTCUSDT")
LIVE_TEMPLATE: str = os.getenv("LIVE_TEMPLATE", "bear_trend_follower")

# Fraction of current equity to deploy per trade — 25% keeps max loss
# ~$0.50-$1.00 with ATR-based stops on a $20 account. Remaining 75% is buffer.
POSITION_SIZE_FRACTION: float = 0.25

# Binance minimum notional value — BTCUSDT spot minimum is $5
BINANCE_MIN_NOTIONAL: float = 5.0

# Commission rate — Binance standard 0.1% per side (0.2% round-trip)
COMMISSION_RATE: float = 0.001

# Risk guard limits — hard stops before order submission
MAX_DAILY_LOSS_PCT: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.10"))   # 10% of initial capital
MAX_DRAWDOWN_PCT: float = float(os.getenv("MAX_DRAWDOWN_PCT", "0.20"))       # 20% drawdown from initial capital

# ---------------------------------------------------------------------------
# Portfolio capital model (PARA-12 / DEC-2026-05-31-003).
#
# Previously every live tier was allocated the FULL LIVE_CAPITAL, so N
# concurrent strategies double-counted the account N times and per-strategy
# returns were not additive (the PARA-12 finding). The portfolio model gives
# each strategy a SLICE of total capital and bounds how many run at once and
# how much capital may be committed in aggregate.
#
# Each strategy is allocated PER_STRATEGY_ALLOCATION_PCT of LIVE_CAPITAL.
# At most MAX_STRATEGIES_LIVE_CONCURRENT run simultaneously, and total
# committed capital across active tiers may never exceed
# CAPITAL_RESERVE_FRACTION of LIVE_CAPITAL (leaving a cash buffer for fees,
# slippage, and emergency exits — the reserve principle from
# docs/research/PORTFOLIO_LAYER_DESIGN.md section 4.3).
# ---------------------------------------------------------------------------
MAX_STRATEGIES_LIVE_CONCURRENT: int = int(
    os.environ.get("MAX_STRATEGIES_LIVE_CONCURRENT", "4")
)
PER_STRATEGY_ALLOCATION_PCT: float = float(
    os.environ.get("PER_STRATEGY_ALLOCATION_PCT", "0.20")
)
CAPITAL_RESERVE_FRACTION: float = float(
    os.environ.get("CAPITAL_RESERVE_FRACTION", "0.85")
)
# Capital slice allocated to each live strategy (derived, not the full account).
PER_STRATEGY_CAPITAL: float = LIVE_CAPITAL * PER_STRATEGY_ALLOCATION_PCT

# Polling interval in seconds (matches paper trading engine)
POLLING_INTERVAL: int = 60

# Hourly summary interval in seconds
HOURLY_INTERVAL: int = 3600

# State file path (must be on a Railway persistent volume)
STATE_FILE: Path = Path(os.getenv("LIVE_STATE_FILE", "/app/data/live_state.json"))

# Strategy parameters (matching paper trading config)
BTF_PARAMS: dict[str, Any] = {
    "htf_ema_period": 200,
    "kc_ema_period": 20,
    "kc_atr_period": 14,
    "kc_multiplier": 1.5,
    "adx_period": 14,
    "adx_min_threshold": 20.0,
    "rsi_period": 14,
    "rsi_oversold": 25.0,
    "supertrend_period": 10,
    "supertrend_multiplier": 3.0,
    "atr_period": 14,
    "atr_stop_multiplier": 2.5,
}

CMF_PARAMS: dict[str, Any] = {
    "daily_st_period": 10,
    "daily_st_multiplier": 3.0,
    "htf_ema_period": 21,
    "htf_adx_period": 14,
    "htf_adx_min": 15.0,
    "htf_slope_lookback": 5,
    "st_period_1h": 10,
    "st_multiplier_1h": 3.0,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "atr_period": 14,
}

RSI_BB_PARAMS: dict[str, Any] = {
    "rsi_period": 14,
    "rsi_oversold": 25.0,
    "rsi_overbought": 75.0,
    "rsi_exit_long": 50.0,
    "rsi_exit_short": 50.0,
    "bb_period": 20,
    "bb_std_dev": 2.0,
    "adx_threshold": 25.0,
    "stop_loss_pct": 2.5,
    "ema_regime_period": 200,
}

BTP_PARAMS: dict[str, Any] = {
    "htf_ema_period": 150,
    "trend_ema_period": 50,
    "rsi_period": 14,
    "rsi_pullback_low": 30.0,
    "rsi_pullback_high": 60.0,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "risk_reward_ratio": 2.5,
}

MACD_PB_PARAMS: dict[str, Any] = {
    # Multi-regime winner per DEC-2026-05-28-002 — STABLE_EDGE in
    # choppy_bull, choppy_bear, trending_bull.
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "pullback_ema_period": 21,
    "atr_period": 14,
    "atr_stop_multiplier": 2.5,
    "risk_reward_ratio": 2.0,
    "pullback_tolerance_pct": 0.5,
    "regime_ema_period": 200,
}

SRC_PARAMS: dict[str, Any] = {
    "rsi_period": 14,
    "stoch_period": 14,
    "smooth_k": 3,
    "smooth_d": 3,
    "stoch_oversold": 20.0,
    "stoch_max": 70.0,
    "stoch_lookback": 5,
    "ema_period": 50,
    "regime_ema_period": 200,
    "rsi_min": 40.0,
    "rsi_max": 70.0,
    "volume_period": 20,
    "volume_threshold": 1.2,
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "risk_reward_ratio": 3.0,
}

HATP_PARAMS: dict[str, Any] = {
    "ha_wick_lookback": 7,
    "ha_prior_wick_min": 6,
    "wick_tolerance": 0.05,
    "ema_period": 50,
    "regime_ema_period": 200,
    "rsi_period": 14,
    "rsi_min": 50.0,
    "rsi_max": 75.0,
    "volume_period": 20,
    "volume_threshold": 1.4,
    "atr_period": 14,
    "atr_stop_multiplier": 2.0,
    "risk_reward_ratio": 2.0,
}

ICVP_PARAMS: dict[str, Any] = {
    "tenkan_period": 20,
    "kijun_period": 60,
    "senkou_b_period": 120,
    "displacement": 30,
    "atr_period": 14,
    "volume_period": 20,
    "volume_threshold": 1.3,
}

# Minimum lookback bars per strategy (for OHLCV fetch)
MIN_BARS_LOOKUP: dict[str, int] = {
    "bear_trend_follower": 860,
    "cascading_momentum_filter": 400,
    "rsi_bb_mean_reversion": 260,
    "bull_trend_pullback": 300,
    "stoch_rsi_bull_cross": 260,
    "heikin_ashi_trend_pulse": 260,
    "macd_pullback": 260,
    "ichimoku_cloud_trend": 220,
}

STRATEGY_PARAMS_LOOKUP: dict[str, dict[str, Any]] = {
    "bear_trend_follower": BTF_PARAMS,
    "cascading_momentum_filter": CMF_PARAMS,
    "rsi_bb_mean_reversion": RSI_BB_PARAMS,
    "bull_trend_pullback": BTP_PARAMS,
    "stoch_rsi_bull_cross": SRC_PARAMS,
    "heikin_ashi_trend_pulse": HATP_PARAMS,
    "macd_pullback": MACD_PB_PARAMS,
    "ichimoku_cloud_trend": ICVP_PARAMS,
}


# ---------------------------------------------------------------------------
# Position state — persisted to JSON so restarts don't create ghost positions
# ---------------------------------------------------------------------------


@dataclass
class LiveTier:
    """One live-trading strategy-symbol slot.

    Each tier runs independently with its own state, session ID, and fixed
    capital allocation. Tiers activate when total portfolio equity crosses
    their threshold AND the current regime matches their regime_tag.

    Attributes:
        label: Human-readable name shown in Telegram alerts (e.g. "BTF/BTC").
        template: Strategy template ID used by SignalGeneratorFactory.
        symbol: Binance trading pair (e.g. "BTCUSDT").
        capital: Fixed USDT allocation for this tier (independent of others).
        activation_threshold: Total portfolio equity required to activate.
        regime_tag: Legacy coarse regime tag — "bear", "bull", or "all".
            Used for backward-compatibility fallback when regime_tags is empty.
        regime_tags: Fine-grained SubRegime tags (preferred). When non-empty,
            tier activates only when the current confirmed SubRegime is in
            this list. When empty, falls back to legacy regime_tag.
            Decision: DEC-2026-05-28-003.
        params: Strategy-specific parameter dict.
        lookback_bars: OHLCV bars to fetch per poll cycle.
        state: Mutable live position state (loaded from DB on activation).
        active: Whether this tier is currently running.
        generator: SignalGenerator instance (set at runtime).
        session_id: Neon/SQLite session key (e.g. "live_bear_trend_follower_BTCUSDT").
        state_file: JSON backup path (one file per tier on the persistent volume).
    """

    label: str
    template: str
    symbol: str
    capital: float
    activation_threshold: float
    regime_tag: str
    params: dict[str, Any]
    lookback_bars: int
    regime_tags: list[str] = dc_field(default_factory=list)
    state: dict[str, Any] = dc_field(default_factory=dict)
    active: bool = False
    generator: Any = None
    session_id: str = ""
    state_file: Path = dc_field(default=Path("/app/data/live_state_default.json"))


def _build_tiers() -> list[LiveTier]:
    """Build expansion tier list from current LIVE_CAPITAL setting.

    Tiers are listed in activation order.
    Bear tiers run when RegimeState.is_bear is True.
    Bull tiers run when RegimeState.is_bull is True.
    All-regime tiers run regardless of regime.

    Activation thresholds use multiples of the per-strategy capital slice
    (PER_STRATEGY_CAPITAL) so they remain reachable as the active book grows
    (PARA-12 / DEC-2026-05-31-003).
    """
    # PARA-12: `cap` is the PER-STRATEGY capital slice. Both per-tier capital
    # and the activation thresholds scale with it, so a tier's threshold stays
    # reachable from the sum of active slices + PnL (a threshold tied to the
    # full LIVE_CAPITAL could never be reached from $4 slices). At
    # LIVE_CAPITAL=$100 with 20% slices this reproduces the original
    # $0/$40/$60/$80 ladder exactly.
    cap = PER_STRATEGY_CAPITAL
    tiers = [
        # ----------------------------------------------------------------
        # Bear tiers (validated in bear paper trading, ordered by conviction)
        # ----------------------------------------------------------------
        # BTF tiers REMOVED 2026-05-27 — strategy retired after May 2026
        # backtest + live paper showed PF=0.75-0.76 across 115 total trades.
        # See DEC-2026-05-27-007.
        # CMF/SOL and RSI_BB/ETH tiers REMOVED 2026-05-28 — strategies
        # retired (DEC-2026-05-28-002) after spot rolling backtest showed
        # POOR_IN_REGIME for all relevant regimes.
        # ----------------------------------------------------------------
        # Bull-tagged tiers (note: regime_tag uses the coarse legacy field;
        # the SubRegime-aware live router upgrade will use regime_tags from
        # the paper config to route precisely. Until then, these activate
        # whenever cached_regime.is_bull, which approximates correctly).
        # ----------------------------------------------------------------
        LiveTier(
            label="MACD_PB/AVAX",
            template="macd_pullback",
            symbol="AVAXUSDT",
            capital=cap,
            activation_threshold=0.0,
            regime_tag="all",  # legacy fallback
            # DEC-2026-05-28-002: STABLE_EDGE in 3 regimes.
            regime_tags=["choppy_bull", "choppy_bear", "trending_bull"],
            params=MACD_PB_PARAMS,
            lookback_bars=260,
        ),
        LiveTier(
            label="BTP/BTC",
            template="bull_trend_pullback",
            symbol="BTCUSDT",
            capital=cap,
            activation_threshold=cap * 2,
            regime_tag="bull",  # legacy fallback (was wrong — see regime_tags)
            # DEC-2026-05-28-002: STABLE_EDGE in choppy_bear only.
            regime_tags=["choppy_bear"],
            params=BTP_PARAMS,
            lookback_bars=300,
        ),
        LiveTier(
            label="SRC/BTC",
            template="stoch_rsi_bull_cross",
            symbol="BTCUSDT",
            capital=cap,
            activation_threshold=cap * 3,
            regime_tag="bull",
            # DEC-2026-05-28-002: STABLE choppy_bull, PROMISING choppy_bear.
            regime_tags=["choppy_bull", "choppy_bear"],
            params=SRC_PARAMS,
            lookback_bars=260,
        ),
        # HATP/BTC REMOVED 2026-05-28 — strategy retired (DEC-2026-05-28-002).
        # ----------------------------------------------------------------
        # All-regime (ICVP is self-directing via cloud — works in 3 regimes)
        # ----------------------------------------------------------------
        LiveTier(
            label="ICVP/BTC",
            template="ichimoku_cloud_trend",
            symbol="BTCUSDT",
            capital=cap,
            activation_threshold=cap * 4,
            regime_tag="all",
            # DEC-2026-05-28-002: PROMISING in 3 regimes; POOR in trending_bull.
            regime_tags=["choppy_bull", "choppy_bear", "trending_bear"],
            params=ICVP_PARAMS,
            lookback_bars=220,
        ),
    ]
    for tier in tiers:
        tier.session_id = f"live_{tier.template}_{tier.symbol}"
        tier.state_file = Path(
            f"/app/data/live_state_{tier.template}_{tier.symbol}.json"
        )
    return tiers


# Module-level tier list — initialised once, mutated as tiers activate.
EXPANSION_TIERS: list[LiveTier] = _build_tiers()

# -----------------------------------------------------------------------------
# Demotion guardrail thresholds — single source of truth.
# Decision: DEC-2026-05-27-004 (promotion gate).
# A strategy template is DEGRADED if its paper trading sessions in
# aggregate show N >= MIN_TRADES and PF < MAX_PF. Live tiers using a
# degraded template will NOT activate, regardless of equity threshold.
# -----------------------------------------------------------------------------
DEGRADATION_MIN_TRADES: int = 10
DEGRADATION_MAX_PF: float = 0.8

# -----------------------------------------------------------------------------
# Decorrelation cap — max concurrent same-direction positions across tiers.
# Decision: DEC-2026-05-27-006.
# When a basket of tiers shares the same signal (e.g. all BTF symbols
# triggering SHORT at the same hour during a bear regime), correlation
# goes to 1.0 on adverse moves. The 2026-05-23 20:00 stop-out hit 5
# BTF-short sessions simultaneously for ~$395 of realised loss. Capping
# concurrent same-direction positions bounds the worst-case correlated
# bleed at the cost of missing some win clusters.
# -----------------------------------------------------------------------------
MAX_CONCURRENT_SAME_DIRECTION: int = int(
    os.environ.get("MAX_CONCURRENT_SAME_DIRECTION", "4")
)


def _count_open_same_direction(direction: str) -> int:
    """Count tiers currently holding an open position on `direction`."""
    return sum(
        1 for t in EXPANSION_TIERS
        if t.active
        and t.state.get("in_position")
        and t.state.get("side") == direction
    )


def _tier_regime_match(
    tier: LiveTier,
    regime: RegimeState,
    sub_regime: SubRegime,
) -> bool:
    """Whether a tier may run given the current regime + sub_regime.

    Routing precedence (DEC-2026-05-28-003):
      1. If `tier.regime_tags` is non-empty: require sub_regime to be in
         the list. Fail-closed when sub_regime is UNKNOWN — better to
         skip activation than to route to a wrong regime.
      2. Else fall back to legacy coarse `regime_tag` matching.
    """
    if tier.regime_tags:
        if sub_regime == SubRegime.UNKNOWN:
            return False
        return sub_regime.value in tier.regime_tags

    # Legacy coarse fallback.
    return (
        tier.regime_tag == "all"
        or (tier.regime_tag == "bear" and regime.is_bear)
        or (tier.regime_tag == "bull" and regime.is_bull)
    )


def _can_activate_tier(
    tier: LiveTier,
    all_tiers: list[LiveTier],
    *,
    max_concurrent: int,
    reserve_cap_usdt: float,
) -> tuple[bool, str]:
    """Decide whether an eligible tier may activate under portfolio limits.

    Portfolio capital model (PARA-12 / DEC-2026-05-31-003). Assumes the
    caller has already confirmed the tier is eligible by regime, equity
    threshold, and is not degraded; this adds the two portfolio-level rails:

      1. Concurrency cap — at most ``max_concurrent`` tiers active at once,
         so capital and correlated risk stay bounded regardless of how many
         tiers are otherwise eligible.
      2. Capital reserve — the PROJECTED committed capital (currently active
         tiers plus this candidate) must not exceed ``reserve_cap_usdt``.
         The projected (not current-only) check is deliberate: a current-only
         test would permit one activation that overshoots the reserve.

    Committed capital uses ``tier.capital`` (the fixed allocation), not live
    equity — the reserve protects the cash buffer, not mark-to-market value.

    Args:
        tier: The candidate (inactive) tier being considered for activation.
        all_tiers: Full tier list; active members are summed/counted.
        max_concurrent: Maximum number of simultaneously active tiers.
        reserve_cap_usdt: Absolute ceiling on total committed capital
            (typically ``LIVE_CAPITAL * CAPITAL_RESERVE_FRACTION``).

    Returns:
        (allowed, reason). ``reason`` is empty when allowed, else a one-line
        explanation of which rail blocked activation.
    """
    active = [t for t in all_tiers if t.active]
    if len(active) >= max_concurrent:
        return False, (
            f"concurrency cap reached ({len(active)}/{max_concurrent} active)"
        )
    committed = sum(t.capital for t in active)
    projected = committed + tier.capital
    if projected > reserve_cap_usdt:
        return False, (
            f"capital reserve: committed ${committed:.2f} + ${tier.capital:.2f} "
            f"= ${projected:.2f} would exceed reserve cap ${reserve_cap_usdt:.2f}"
        )
    return True, ""


def _paper_strategy_is_degraded(template_id: str) -> tuple[bool, str]:
    """Check if a strategy template has degraded in live paper trading.

    Reads paper_trading_sessions from the configured database, aggregates
    PnL across all sessions sharing the template_id, and applies the
    degradation rule (N >= MIN_TRADES AND PF < MAX_PF).

    Returns:
        (is_degraded, reason_string). reason_string is empty when not
        degraded, or a one-line explanation when degraded.

    Failures (DB unreachable, no rows) return (False, "") — we fail open
    rather than block live activation on a transient DB issue, because
    the live engine already has its own state for the primary tier and
    the alternative (failing closed) would prevent restarts.
    """
    try:
        from src.data.database import get_db

        with get_db() as db:
            rows = list(
                db.query(PaperTradingSession)
                .filter(PaperTradingSession.template_id == template_id)
                .all()
            )
    except Exception as exc:
        logger.warning(
            "degradation_check_failed",
            template_id=template_id,
            error=str(exc),
        )
        return False, ""

    all_pnls: list[float] = []
    for row in rows:
        for trade in (row.trade_log or []):
            all_pnls.append(float(trade.get("realized_pnl", 0.0)))

    n = len(all_pnls)
    if n < DEGRADATION_MIN_TRADES:
        return False, ""

    wins_sum = sum(p for p in all_pnls if p > 0)
    losses_sum = sum(p for p in all_pnls if p <= 0)
    abs_losses = abs(losses_sum)
    if abs_losses == 0:
        # All winners (or no losses) — definitely not degraded.
        return False, ""
    pf = wins_sum / abs_losses

    if pf < DEGRADATION_MAX_PF:
        return True, (
            f"Paper PF={pf:.2f} over {n} trades (< {DEGRADATION_MAX_PF} threshold)"
        )
    return False, ""


def _paper_strategy_classification(template_id: str) -> tuple[str, bool]:
    """Classify a template's pooled live-paper performance for the promotion gate.

    Reuses the canonical promotion-gate logic from ``scripts.validation_report``
    (DEC-2026-05-27-004), so the live auto-promotion gate and the daily report
    can never disagree: pools every PARA-02-quarantined trade across the
    template's paper sessions, computes N / profit factor / per-trade Sharpe /
    max drawdown, and returns one of READY_FOR_LIVE / OBSERVING / DEGRADED /
    RESEARCH.

    Fail-open contract (mirrors ``_paper_strategy_is_degraded``): the second
    tuple element ``db_ok`` is False when the database could not be read. The
    caller treats that as "cannot determine" and does NOT block — so a transient
    DB outage never blocks a restart (which would leave an open position
    unmanaged). A successfully-computed non-READY classification has
    ``db_ok=True`` and the caller blocks: that fail-closed path is the point of
    the gate (DEC-2026-06-01-001).

    Args:
        template_id: Strategy template to classify (pooled across its symbols,
            consistent with the demotion check).

    Returns:
        (classification, db_ok). On DB error: ("RESEARCH", False) — a safe
        placeholder the caller ignores because db_ok is False.
    """
    try:
        from src.data.database import get_db

        with get_db() as db:
            rows = list(
                db.query(PaperTradingSession)
                .filter(PaperTradingSession.template_id == template_id)
                .all()
            )
    except Exception as exc:
        logger.warning(
            "promotion_classification_failed",
            template_id=template_id,
            error=str(exc),
        )
        return "RESEARCH", False

    pnls: list[float] = []
    returns_pct: list[float] = []
    starting_capital = 0.0
    for row in rows:
        starting_capital += float(getattr(row, "initial_capital", 0.0) or 0.0)
        for trade in (row.trade_log or []):
            # PARA-02 quarantine (DEC-2026-05-31-002): exclude corrupted
            # force-close trades so they cannot pollute the classification.
            if _is_corrupt_force_close(trade):
                continue
            pnls.append(float(trade.get("realized_pnl", 0.0)))
            returns_pct.append(float(trade.get("return_pct", 0.0)))

    n = len(pnls)
    wins_sum = sum(p for p in pnls if p > 0)
    losses_sum = sum(p for p in pnls if p <= 0)
    pf = _profit_factor(wins_sum, losses_sum)
    sharpe = _sharpe_per_trade(returns_pct)
    # Pool MaxDD against the summed per-session starting capital. With no rows
    # (or zero capital) n is also 0, so _classify returns RESEARCH regardless.
    max_dd = _max_drawdown_pct(pnls, starting_capital) if starting_capital > 0 else 0.0
    return _classify(n, pf, sharpe, max_dd), True


def _tier1_activation_blocked(template_id: str) -> tuple[bool, str]:
    """Decide whether tier 1 must NOT auto-activate at startup.

    Applies the same auto-promotion gate as expansion tiers
    (DEC-2026-06-01-001) to the operator-chosen primary tier so the
    READY_FOR_LIVE requirement is uniform across every live tier
    (DEC-2026-06-01-002, closing the tier-1 exemption left open by
    DEC-2026-06-01-001).

    Fail-open contract (identical to ``_paper_strategy_is_degraded`` and the
    expansion-tier gate): when the DB cannot be read, ``db_ok`` is False and
    this returns ``(False, "")`` — a transient outage must never block a
    restart, because an inactive tier 1 leaves any open position unmanaged
    (no stop/TP enforcement). Only a successfully-computed non-READY verdict
    blocks; that fail-closed path is the point of the gate.

    Args:
        template_id: Strategy template backing tier 1 (``EXPANSION_TIERS[0]``).

    Returns:
        (blocked, reason). ``blocked`` is True only on a clear non-READY
        classification; ``reason`` is a one-line explanation for the log +
        Telegram alert, empty when not blocked.
    """
    classification, db_ok = _paper_strategy_classification(template_id)
    if db_ok and classification != "READY_FOR_LIVE":
        return True, (
            f"live-paper performance classified {classification}, "
            f"not READY_FOR_LIVE"
        )
    return False, ""


def _make_session_id() -> str:
    """Build unique session key for the primary (tier-1) live config."""
    return f"live_{LIVE_TEMPLATE}_{LIVE_SYMBOL}"


def load_state(
    store: DataStore,
    session_id: str | None = None,
    symbol: str | None = None,
    state_file: Path | None = None,
) -> dict[str, Any]:
    """Load live trading state — tries SQLite first, then JSON backup.

    Args:
        store: DataStore for SQLite/Neon reads.
        session_id: Session key to load. Defaults to primary tier key.
        symbol: Symbol stored in the session. Defaults to LIVE_SYMBOL.
        state_file: JSON backup path. Defaults to STATE_FILE.

    Returns:
        State dict with keys: in_position, side, entry_price, quantity,
        entry_time, realized_pnl, total_trades, trade_history,
        stop_loss, take_profit.
    """
    if session_id is None:
        session_id = _make_session_id()
    if symbol is None:
        symbol = LIVE_SYMBOL
    if state_file is None:
        state_file = STATE_FILE

    empty: dict[str, Any] = {
        "in_position": False,
        "symbol": symbol,
        "realized_pnl": 0.0,
        "total_trades": 0,
        "trade_history": [],
        "stop_loss": None,
        "take_profit": None,
    }

    # 1. Try SQLite (primary)
    try:
        row = store.get_paper_session(session_id)
        if row is not None:
            state: dict[str, Any] = {
                "in_position": False,
                "symbol": row.symbol,
                "realized_pnl": 0.0,
                "total_trades": row.total_trades,
                "trade_history": row.trade_log or [],
                "stop_loss": None,
                "take_profit": None,
            }
            # Restore realized PnL from trade history
            state["realized_pnl"] = sum(
                t.get("realized_pnl", 0.0) for t in state["trade_history"]
            )
            # Restore open position
            if row.position_data and row.position_data.get("in_position"):
                state["in_position"] = True
                state["side"] = row.position_data.get("side", "")
                state["quantity"] = row.position_data.get("quantity", 0.0)
                state["entry_price"] = row.position_data.get("entry_price", 0.0)
                state["entry_time"] = row.position_data.get("entry_time", "")
                state["stop_loss"] = row.position_data.get("stop_loss")
                state["take_profit"] = row.position_data.get("take_profit")
            logger.info(
                "live_state_loaded_from_db",
                session_id=session_id,
                in_position=state["in_position"],
                total_trades=state["total_trades"],
                realized_pnl=state["realized_pnl"],
            )
            print(
                f"State loaded from DATABASE: "
                f"trades={state['total_trades']}, "
                f"realized=${state['realized_pnl']:+.2f}, "
                f"in_position={state['in_position']}"
            )
            return state
    except Exception as exc:
        logger.warning("live_state_db_load_failed", error=str(exc))

    # 2. Fallback to JSON file
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text())
            data.setdefault("stop_loss", None)
            data.setdefault("take_profit", None)
            data.setdefault("trade_history", [])
            logger.info(
                "live_state_loaded_from_json",
                in_position=data.get("in_position", False),
                symbol=data.get("symbol"),
                session_id=session_id,
            )
            print(
                f"[{session_id}] State from JSON: "
                f"trades={data.get('total_trades', 0)}, "
                f"realized=${data.get('realized_pnl', 0):+.2f}"
            )
            return data
        except Exception as exc:
            logger.warning("live_state_json_load_failed", error=str(exc), session_id=session_id)

    # 3. Fresh start
    print(f"[{session_id}] No previous state — starting fresh.")
    return empty


def save_state(
    state: dict[str, Any],
    store: DataStore,
    tier: LiveTier | None = None,
) -> None:
    """Persist live trading state to SQLite (primary) and JSON (backup).

    Args:
        state: Current position state dict.
        store: DataStore instance for SQLite/Neon persistence.
        tier: LiveTier whose state is being saved. Falls back to primary
            LIVE_TEMPLATE/LIVE_SYMBOL globals when None (backward-compatible).
    """
    session_id = tier.session_id if tier else _make_session_id()
    template_id = tier.template if tier else LIVE_TEMPLATE
    symbol = tier.symbol if tier else LIVE_SYMBOL
    capital = tier.capital if tier else LIVE_CAPITAL
    sf = tier.state_file if tier else STATE_FILE

    # 1. Save to SQLite/Neon
    try:
        position_data: dict[str, Any] | None = None
        if state.get("in_position"):
            position_data = {
                "in_position": True,
                "side": state.get("side", ""),
                "quantity": state.get("quantity", 0.0),
                "entry_price": state.get("entry_price", 0.0),
                "entry_time": state.get("entry_time", ""),
                "stop_loss": state.get("stop_loss"),
                "take_profit": state.get("take_profit"),
            }

        row = PaperTradingSession(
            session_id=session_id,
            template_id=template_id,
            symbol=symbol,
            initial_capital=capital,
            cash=capital - (
                state.get("entry_price", 0.0) * state.get("quantity", 0.0)
                if state.get("in_position") else 0.0
            ),
            position_data=position_data,
            trade_log=state.get("trade_history", []),
            equity_curve=[],
            total_trades=state.get("total_trades", 0),
        )
        store.upsert_paper_session(row)
    except Exception as exc:
        logger.warning("live_state_db_save_failed", error=str(exc), session_id=session_id)

    # 2. Backup to JSON
    try:
        sf.parent.mkdir(parents=True, exist_ok=True)
        sf.write_text(json.dumps(state, default=str, indent=2))
    except Exception as exc:
        logger.warning("live_state_json_save_failed", error=str(exc), session_id=session_id)


# ---------------------------------------------------------------------------
# Equity and position sizing
# ---------------------------------------------------------------------------


def _get_current_equity(
    state: dict[str, Any],
    initial_capital: float,
    current_price: float | None = None,
) -> float:
    """Calculate current account equity from live state.

    Accounts for realized PnL. When a position is open and current_price
    is provided, unrealized PnL is also included.

    Args:
        state: Current live trading state dict.
        initial_capital: Starting capital in USDT.
        current_price: Current market price (optional, for unrealized PnL).

    Returns:
        Estimated account equity in USDT.
    """
    equity = initial_capital + state.get("realized_pnl", 0.0)

    if state.get("in_position") and current_price is not None and current_price > 0:
        entry_price = state.get("entry_price", 0.0)
        qty = state.get("quantity", 0.0)
        side = state.get("side", "")
        if side == "LONG":
            unrealized = (current_price - entry_price) * qty
        elif side == "SHORT":
            unrealized = (entry_price - current_price) * qty
        else:
            unrealized = 0.0
        equity += unrealized

    return equity


def calculate_quantity(current_equity: float, price: float) -> float:
    """Calculate order quantity from current equity and current price.

    Uses POSITION_SIZE_FRACTION of current equity — adjusts automatically
    as the account grows or shrinks. Rounds down to 6 decimal places to
    stay within Binance precision requirements.

    Args:
        current_equity: Current account equity in USDT.
        price: Current asset price in USDT.

    Returns:
        Quantity in base asset, or 0.0 if notional would be below minimum.
    """
    usdt_to_spend = current_equity * POSITION_SIZE_FRACTION
    if usdt_to_spend < BINANCE_MIN_NOTIONAL:
        logger.warning(
            "position_below_minimum_notional",
            usdt_to_spend=usdt_to_spend,
            minimum=BINANCE_MIN_NOTIONAL,
            current_equity=current_equity,
        )
        return 0.0
    quantity = usdt_to_spend / price
    # Round down to 6 decimal places — safe floor for BTC/ETH Binance precision
    return math.floor(quantity * 1_000_000) / 1_000_000


# ---------------------------------------------------------------------------
# Risk guards — checked before every order submission
# ---------------------------------------------------------------------------


def _check_risk_guards(
    state: dict[str, Any],
    store: DataStore,
    initial_capital: float,
    current_price: float,
) -> tuple[bool, str]:
    """Enforce risk limits before allowing an order to be submitted.

    Checks (in priority order):
    1. Kill switch — hard halt set externally via the DB or dashboard
    2. Daily loss limit — realized losses exceed MAX_DAILY_LOSS_PCT of initial capital
    3. Max drawdown — current equity has fallen below MAX_DRAWDOWN_PCT of initial capital

    Args:
        state: Current live trading state dict.
        store: DataStore for kill switch DB read.
        initial_capital: Starting capital in USDT.
        current_price: Current market price (for unrealized PnL in equity calc).

    Returns:
        Tuple of (approved, rejection_reason). approved is True if all checks pass.
    """
    # 1. Kill switch — always checked first, consistent with risk controller pipeline
    try:
        system_state = store.get_system_state()
        if system_state.kill_switch_active:
            logger.warning(
                "live_order_blocked_kill_switch",
                kill_switch_active=True,
            )
            return False, "kill_switch_active"
    except Exception as exc:
        # DB failure = fail-safe: block the order
        logger.error(
            "live_risk_guard_db_error",
            error=str(exc),
            exc_info=True,
        )
        return False, f"risk_check_failed_db_error: {exc}"

    # 2. Daily loss limit — guard against a bad trading session
    realized_pnl = state.get("realized_pnl", 0.0)
    daily_loss_limit = -(initial_capital * MAX_DAILY_LOSS_PCT)
    if realized_pnl <= daily_loss_limit:
        logger.warning(
            "live_order_blocked_daily_loss",
            realized_pnl=realized_pnl,
            daily_loss_limit=daily_loss_limit,
            max_daily_loss_pct=MAX_DAILY_LOSS_PCT,
        )
        return False, (
            f"daily_loss_limit_breached: realized_pnl={realized_pnl:.2f} "
            f"<= limit={daily_loss_limit:.2f}"
        )

    # 3. Max drawdown — guard against sustained equity decline
    current_equity = _get_current_equity(state, initial_capital, current_price)
    drawdown = (initial_capital - current_equity) / initial_capital
    if drawdown >= MAX_DRAWDOWN_PCT:
        logger.warning(
            "live_order_blocked_max_drawdown",
            current_equity=current_equity,
            initial_capital=initial_capital,
            drawdown_pct=drawdown,
            max_drawdown_pct=MAX_DRAWDOWN_PCT,
        )
        return False, (
            f"max_drawdown_breached: drawdown={drawdown:.1%} "
            f">= limit={MAX_DRAWDOWN_PCT:.1%}"
        )

    return True, ""


# ---------------------------------------------------------------------------
# Stop-loss and take-profit enforcement
# ---------------------------------------------------------------------------


def _check_stops_and_tp(
    state: dict[str, Any],
    bar: OHLCV,
) -> tuple[bool, str, float]:
    """Check if the current bar triggered stop-loss or take-profit.

    Uses intrabar high/low to detect level breaches — consistent with the
    backtest and paper trading SimulatedTrader.check_stop_take_profit() logic.

    When both stop and TP are hit on the same bar (extreme volatility gap),
    stop-loss takes priority — conservative worst-case assumption.

    For LONG positions:
      - Stop hit when bar.low <= stop_loss
      - TP hit when bar.high >= take_profit

    For SHORT positions:
      - Stop hit when bar.high >= stop_loss
      - TP hit when bar.low <= take_profit

    Args:
        state: Current live trading state dict with stop_loss / take_profit.
        bar: Current OHLCV bar with high and low for intrabar detection.

    Returns:
        Tuple of (should_exit, exit_reason, exit_price).
        should_exit is False if no position is open or no levels are set.
        exit_price is the level that was breached (before market fill slippage).
    """
    if not state.get("in_position"):
        return False, "", 0.0

    side: str = state.get("side", "")
    stop_loss: float | None = state.get("stop_loss")
    take_profit: float | None = state.get("take_profit")

    if stop_loss is None and take_profit is None:
        return False, "", 0.0

    stop_hit = False
    tp_hit = False
    exit_price = 0.0

    if side == "LONG":
        if stop_loss is not None and bar.low <= stop_loss:
            stop_hit = True
            exit_price = stop_loss
        if take_profit is not None and bar.high >= take_profit:
            tp_hit = True
            if not stop_hit:
                exit_price = take_profit
    elif side == "SHORT":
        if stop_loss is not None and bar.high >= stop_loss:
            stop_hit = True
            exit_price = stop_loss
        if take_profit is not None and bar.low <= take_profit:
            tp_hit = True
            if not stop_hit:
                exit_price = take_profit

    if stop_hit:
        logger.info(
            "live_stop_loss_triggered",
            symbol=state.get("symbol"),
            side=side,
            bar_low=bar.low,
            bar_high=bar.high,
            stop_loss=stop_loss,
            exit_price=exit_price,
        )
        return True, "stop_loss", exit_price

    if tp_hit:
        logger.info(
            "live_take_profit_triggered",
            symbol=state.get("symbol"),
            side=side,
            bar_low=bar.low,
            bar_high=bar.high,
            take_profit=take_profit,
            exit_price=exit_price,
        )
        return True, "take_profit", exit_price

    return False, "", 0.0


# ---------------------------------------------------------------------------
# Order helpers
# ---------------------------------------------------------------------------


async def submit_market_order(
    adapter: BinanceExecutionAdapter,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    strategy_id: str,
) -> tuple[bool, float]:
    """Submit a market order and return success flag with actual fill price.

    Args:
        adapter: Binance execution adapter.
        symbol: Trading pair.
        side: "buy" or "sell".
        quantity: Quantity in base asset.
        price: Current price (for OrderRequest price field only).
        strategy_id: Strategy identifier for logging.

    Returns:
        Tuple of (success, filled_price).
        filled_price is the actual Binance execution price, or 0.0 on failure.
    """
    request = OrderRequest(
        account_id="live_account",
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        order_type="market",
        reason=f"live_signal_{side}",
    )
    try:
        result = await adapter.submit_order(request)
        filled_price: float = result.filled_price or price
        logger.info(
            "live_order_submitted",
            symbol=symbol,
            side=side,
            quantity=quantity,
            status=result.status,
            filled_price=filled_price,
            commission=result.commission,
            external_id=result.external_id,
        )
        success = result.status == "filled"
        return success, filled_price if success else 0.0
    except Exception as exc:
        logger.error(
            "live_order_failed",
            symbol=symbol,
            side=side,
            quantity=quantity,
            error=str(exc),
        )
        return False, 0.0


def _record_closed_trade(
    state: dict[str, Any],
    exit_price: float,
    exit_reason: str,
    symbol: str | None = None,
) -> float:
    """Record a closed trade into state and return net PnL after commissions.

    Calculates gross PnL from actual entry and exit fill prices, then deducts
    round-trip commissions. Appends the record to trade_history.

    Args:
        state: Current live trading state dict (mutated in-place).
        exit_price: Actual Binance fill price for the exit order.
        exit_reason: Human-readable exit reason (signal / stop_loss / take_profit).

    Returns:
        Net realized PnL for this trade in USDT (after commissions).
    """
    entry_price: float = state.get("entry_price", 0.0)
    qty: float = state.get("quantity", 0.0)
    current_side: str = state.get("side", "")

    # Gross PnL from actual fill prices
    if current_side == "LONG":
        gross_pnl = (exit_price - entry_price) * qty
    else:
        gross_pnl = (entry_price - exit_price) * qty

    # Round-trip commissions on actual fill prices
    entry_commission = entry_price * qty * COMMISSION_RATE
    exit_commission = exit_price * qty * COMMISSION_RATE
    total_commission = entry_commission + exit_commission

    net_pnl = gross_pnl - total_commission
    return_pct = (net_pnl / (entry_price * qty)) * 100.0 if entry_price * qty > 0 else 0.0

    # Accumulate into running total
    state["realized_pnl"] = state.get("realized_pnl", 0.0) + net_pnl
    state["total_trades"] = state.get("total_trades", 0) + 1

    rec_symbol = symbol if symbol is not None else LIVE_SYMBOL

    if "trade_history" not in state:
        state["trade_history"] = []
    state["trade_history"].append({
        "direction": current_side,
        "symbol": rec_symbol,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": qty,
        "entry_commission": round(entry_commission, 6),
        "exit_commission": round(exit_commission, 6),
        "gross_pnl": round(gross_pnl, 4),
        "realized_pnl": round(net_pnl, 4),
        "return_pct": round(return_pct, 4),
        "exit_reason": exit_reason,
        "entry_time": state.get("entry_time", ""),
        "exit_time": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(
        "live_trade_closed",
        symbol=rec_symbol,
        direction=current_side,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=qty,
        gross_pnl=gross_pnl,
        commission=total_commission,
        net_pnl=net_pnl,
        return_pct=return_pct,
        exit_reason=exit_reason,
    )

    # Clear position fields
    state["in_position"] = False
    state["side"] = ""
    state["quantity"] = 0.0
    state["entry_price"] = 0.0
    state["entry_time"] = ""
    state["stop_loss"] = None
    state["take_profit"] = None

    return net_pnl


# ---------------------------------------------------------------------------
# Per-tier poll processor
# ---------------------------------------------------------------------------


async def _process_tier(
    tier: LiveTier,
    adapter: BinanceExecutionAdapter,
    fetcher: MarketDataFetcher,
    store: DataStore,
    regime_allows_entry: bool,
    send_alert: Callable[..., Coroutine[Any, Any, None]],
    poll_count: int,
) -> None:
    """Run one poll cycle for a single LiveTier.

    Handles stop/TP enforcement, signal generation, and order submission
    for one strategy-symbol pair. Called once per tier per poll cycle
    from the main loop.

    Entry is gated by regime_allows_entry — stops and signal closes
    always execute regardless of regime.

    Args:
        tier: The active LiveTier to process.
        adapter: Binance execution adapter.
        fetcher: OHLCV market data fetcher.
        store: DataStore for risk guard (kill switch) reads.
        regime_allows_entry: True when current regime matches this tier's
            regime_tag. False blocks new positions but not exits.
        send_alert: Async callable for Telegram notifications.
        poll_count: Current poll counter (for periodic logging).
    """
    series = await fetcher.fetch_ohlcv(
        symbol=tier.symbol,
        timeframe="1h",
        limit=min(tier.lookback_bars, 1000),
    )

    if series is None or len(series) < tier.generator.min_bars_required + 2:
        logger.warning(
            "live_insufficient_data",
            tier=tier.label,
            available=len(series) if series else 0,
            required=tier.generator.min_bars_required + 2,
        )
        return

    current_bar: OHLCV = series[-1]
    current_price: float = current_bar.close

    # -------------------------------------------------------------------
    # Step 1: Stop-loss / take-profit (executes regardless of regime)
    # -------------------------------------------------------------------
    should_exit, exit_reason, level_price = _check_stops_and_tp(tier.state, current_bar)

    if should_exit:
        qty = tier.state.get("quantity", 0.0)
        current_side = tier.state.get("side", "")
        exit_order_side = "sell" if current_side == "LONG" else "buy"

        approved, block_reason = _check_risk_guards(
            tier.state, store, tier.capital, current_price
        )
        if not approved and "kill_switch" in block_reason:
            await send_alert(
                title=f"KILL SWITCH — Stop Exit Blocked [{tier.label}]",
                message=(
                    f"Kill switch is active. Cannot close position.\n"
                    f"Position: IN {current_side} @ ${tier.state.get('entry_price', 0):,.2f}"
                ),
                level=AlertLevel.CRITICAL,
            )
        else:
            success, filled_price = await submit_market_order(
                adapter, tier.symbol, exit_order_side, qty, current_price,
                tier.session_id,
            )
            if success and filled_price > 0:
                entry_snap = tier.state.get("entry_price", level_price)
                net_pnl = _record_closed_trade(
                    tier.state, filled_price, exit_reason, tier.symbol
                )
                save_state(tier.state, store, tier)
                await send_alert(
                    title=f"CLOSED [{exit_reason.upper()}]: {tier.label}",
                    message=(
                        f"Direction: {current_side}\n"
                        f"Entry: ${entry_snap:,.2f} -> Fill: ${filled_price:,.2f}\n"
                        f"Level: ${level_price:,.2f}\n"
                        f"Net PnL: ${net_pnl:+.4f}\n"
                        f"---\n"
                        f"Tier Realized: ${tier.state['realized_pnl']:+.2f}\n"
                        f"Trades: {tier.state['total_trades']}"
                    ),
                )
            else:
                await send_alert(
                    title=f"STOP EXIT FAILED: {tier.label}",
                    message=(
                        f"Could not close on {exit_reason}.\n"
                        f"Manual intervention required.\n"
                        f"Side: {current_side} | Qty: {qty:.6f}"
                    ),
                    level=AlertLevel.CRITICAL,
                )

    # -------------------------------------------------------------------
    # Step 2: Signal generation (confirmed bars only, no lookahead)
    # -------------------------------------------------------------------
    signal_series = series.slice(0, len(series) - 1)
    signal = tier.generator.generate(signal_series, tier.params, tier.symbol)

    in_position = tier.state.get("in_position", False)
    current_side = tier.state.get("side", "")

    if signal is not None:
        sig_dir = signal.direction.value

        logger.info(
            "live_signal_generated",
            tier=tier.label,
            symbol=tier.symbol,
            direction=sig_dir,
            strength=signal.strength,
            in_position=in_position,
            regime_allows_entry=regime_allows_entry,
            poll=poll_count,
        )

        # -------------------------------------------------------------------
        # Step 3: Signal-driven CLOSE (executes regardless of regime)
        # -------------------------------------------------------------------
        if in_position and sig_dir == "CLOSE":
            exit_order_side = "sell" if current_side == "LONG" else "buy"
            approved, block_reason = _check_risk_guards(
                tier.state, store, tier.capital, current_price
            )
            if not approved and "kill_switch" in block_reason:
                await send_alert(
                    title=f"KILL SWITCH — Signal Close Blocked [{tier.label}]",
                    message=f"Kill switch active.\nBlock: {block_reason}",
                    level=AlertLevel.CRITICAL,
                )
            else:
                success, filled_price = await submit_market_order(
                    adapter, tier.symbol, exit_order_side,
                    tier.state.get("quantity", 0.0), current_price, tier.session_id,
                )
                if success and filled_price > 0:
                    entry_snap = tier.state.get("entry_price", 0.0)
                    entry_time_snap = tier.state.get("entry_time", "")
                    net_pnl = _record_closed_trade(
                        tier.state, filled_price, "signal_close", tier.symbol
                    )
                    save_state(tier.state, store, tier)

                    hold_str = ""
                    if entry_time_snap:
                        try:
                            e_dt = datetime.fromisoformat(entry_time_snap)
                            hold_h = (datetime.now(timezone.utc) - e_dt).total_seconds() / 3600.0
                            hold_str = f"\nHold: {hold_h:.1f}h"
                        except (ValueError, TypeError):
                            pass

                    await send_alert(
                        title=f"TRADE CLOSED [SIGNAL]: {tier.label}",
                        message=(
                            f"Direction: {current_side}\n"
                            f"Entry: ${entry_snap:,.2f} -> Fill: ${filled_price:,.2f}"
                            f"{hold_str}\n"
                            f"Net PnL: ${net_pnl:+.4f}\n"
                            f"---\n"
                            f"Tier Realized: ${tier.state['realized_pnl']:+.2f}\n"
                            f"Trades: {tier.state['total_trades']}"
                        ),
                    )

        # -------------------------------------------------------------------
        # Step 4: Signal-driven ENTRY (only when flat AND regime allows)
        # -------------------------------------------------------------------
        elif not in_position and sig_dir in ("LONG", "SHORT"):
            if not regime_allows_entry:
                logger.info(
                    "live_entry_blocked_regime",
                    tier=tier.label,
                    direction=sig_dir,
                    symbol=tier.symbol,
                )
            else:
                # Decorrelation cap: count tiers already in this direction.
                # Decision: DEC-2026-05-27-006.
                open_same_dir = _count_open_same_direction(sig_dir)
                if open_same_dir >= MAX_CONCURRENT_SAME_DIRECTION:
                    logger.warning(
                        "live_entry_blocked_decorrelation",
                        tier=tier.label,
                        direction=sig_dir,
                        open_same_direction=open_same_dir,
                        cap=MAX_CONCURRENT_SAME_DIRECTION,
                    )
                    await send_alert(
                        title=f"ENTRY BLOCKED [decorrelation]: {tier.label}",
                        message=(
                            f"Signal: {sig_dir}\n"
                            f"Already open same-direction: "
                            f"{open_same_dir} / cap {MAX_CONCURRENT_SAME_DIRECTION}\n"
                            f"Action: skipping entry to limit correlated risk."
                        ),
                        level=AlertLevel.WARNING,
                    )
                    return
                approved, block_reason = _check_risk_guards(
                    tier.state, store, tier.capital, current_price
                )
                if not approved:
                    logger.warning(
                        "live_entry_blocked_risk_guard",
                        tier=tier.label,
                        direction=sig_dir,
                        reason=block_reason,
                    )
                    await send_alert(
                        title=f"ENTRY BLOCKED: {tier.label}",
                        message=(
                            f"Signal: {sig_dir}\n"
                            f"Blocked by: {block_reason}\n"
                            f"Tier Realized: ${tier.state.get('realized_pnl', 0):+.2f}"
                        ),
                        level=AlertLevel.WARNING,
                    )
                else:
                    order_side = "buy" if sig_dir == "LONG" else "sell"
                    current_equity = _get_current_equity(
                        tier.state, tier.capital, current_price
                    )
                    qty = calculate_quantity(current_equity, current_price)

                    if qty > 0:
                        success, filled_price = await submit_market_order(
                            adapter, tier.symbol, order_side, qty,
                            current_price, tier.session_id,
                        )
                        if success and filled_price > 0:
                            tier.state["in_position"] = True
                            tier.state["side"] = sig_dir
                            tier.state["quantity"] = qty
                            tier.state["entry_price"] = filled_price
                            tier.state["entry_time"] = datetime.now(timezone.utc).isoformat()
                            tier.state["stop_loss"] = signal.stop_loss
                            tier.state["take_profit"] = signal.take_profit
                            save_state(tier.state, store, tier)

                            stop_str = f"${signal.stop_loss:,.2f}" if signal.stop_loss else "None"
                            tp_str = f"${signal.take_profit:,.2f}" if signal.take_profit else "None"

                            await send_alert(
                                title=f"TRADE OPENED: {tier.label}",
                                message=(
                                    f"Direction: {sig_dir}\n"
                                    f"Fill: ${filled_price:,.2f} | Qty: {qty:.6f}\n"
                                    f"Notional: ${qty * filled_price:.2f}\n"
                                    f"Stop: {stop_str} | TP: {tp_str}\n"
                                    f"Strength: {signal.strength:.2f}\n"
                                    f"Equity: ${current_equity:.2f} x {POSITION_SIZE_FRACTION:.0%}"
                                ),
                            )

    # Periodic console log (every 12 polls ~= 12 minutes)
    if poll_count % 12 == 0:
        pos_str = (
            f"IN {tier.state['side']} @ ${tier.state.get('entry_price', 0):,.2f}"
            if tier.state.get("in_position") else "FLAT"
        )
        eq = _get_current_equity(tier.state, tier.capital, current_price)
        print(
            f"  [{tier.label}] {pos_str} | "
            f"Equity: ${eq:.2f} | "
            f"Realized: ${tier.state.get('realized_pnl', 0):+.2f}",
            flush=True,
        )


# ---------------------------------------------------------------------------
# Main live trading loop
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the live trading loop.

    Polls Binance for new 1H candles every POLLING_INTERVAL seconds.
    Each poll cycle:
      1. Refresh regime (hourly) and activate any new expansion tiers
      2. For each active tier: check stop/TP, generate signal, run entries
      3. Save state for all tiers and wait for next interval

    Regime gate: new entries blocked when current regime does not match
    a tier's regime_tag. Stops and signal closes always execute.
    Expansion tiers: activate when total portfolio equity exceeds threshold.
    """
    print("=" * 60)
    print("PARAVANT Live Trading Runner (Multi-Tier)")
    print(f"Tier 1:    {LIVE_TEMPLATE} / {LIVE_SYMBOL}")
    print(
        f"Capital:   ${LIVE_CAPITAL:.2f} total | "
        f"${PER_STRATEGY_CAPITAL:.2f}/strategy ({PER_STRATEGY_ALLOCATION_PCT:.0%}), "
        f"max {MAX_STRATEGIES_LIVE_CONCURRENT} concurrent"
    )
    print(f"Testnet:   {os.getenv('BINANCE_TESTNET', 'true')}")
    print(f"Max Daily Loss: {MAX_DAILY_LOSS_PCT:.0%} | Max Drawdown: {MAX_DRAWDOWN_PCT:.0%}")
    print(f"Expansion tiers: {len(EXPANSION_TIERS)} defined")
    print(f"Started:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

    try:
        import urllib.request
        ext_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
        print(f"Server IP: {ext_ip}  <-- add this to Binance API IP whitelist")
    except Exception:
        print("Server IP: could not determine")
    print("=" * 60)

    # PARA-12 (DEC-2026-05-31-003): each strategy trades its PER_STRATEGY_CAPITAL
    # slice, not the full account, so the minimum-notional check uses the slice.
    # Fail closed — refuse to start a config whose per-strategy trade would be
    # rejected by Binance, rather than activating tiers that silently never
    # place a valid order.
    usdt_per_trade = PER_STRATEGY_CAPITAL * POSITION_SIZE_FRACTION
    if usdt_per_trade < BINANCE_MIN_NOTIONAL:
        min_live_capital = math.ceil(
            BINANCE_MIN_NOTIONAL
            / (PER_STRATEGY_ALLOCATION_PCT * POSITION_SIZE_FRACTION)
        )
        print(
            f"ERROR: Per-strategy capital ${PER_STRATEGY_CAPITAL:.2f} "
            f"(= ${LIVE_CAPITAL:.2f} x {PER_STRATEGY_ALLOCATION_PCT:.0%}) "
            f"x {POSITION_SIZE_FRACTION:.0%} position size = ${usdt_per_trade:.2f}, "
            f"below Binance minimum notional (${BINANCE_MIN_NOTIONAL:.2f}).\n"
            f"For the portfolio capital model, set LIVE_CAPITAL_USDT to at least "
            f"${min_live_capital:.0f} (or raise PER_STRATEGY_ALLOCATION_PCT)."
        )
        sys.exit(1)

    api_key = os.getenv("BINANCE_API_KEY", "")
    secret_key = os.getenv("BINANCE_SECRET_KEY", "")
    testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    if not api_key or not secret_key:
        print("ERROR: BINANCE_API_KEY and BINANCE_SECRET_KEY must be set.")
        sys.exit(1)

    rate_limiter = RateLimiter()
    client = BinanceClient(
        api_key=api_key, secret_key=secret_key, testnet=testnet, rate_limiter=rate_limiter,
    )
    adapter = BinanceExecutionAdapter(client=client, rate_limiter=rate_limiter)
    fetcher = MarketDataFetcher()

    init_db()
    store = DataStore()
    print("Database initialized.")

    telegram: TelegramChannel | None = None
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        telegram = TelegramChannel(bot_token=bot_token, chat_id=chat_id)

    async def send_alert(
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
    ) -> None:
        """Send a Telegram alert if configured."""
        if telegram is None:
            return
        alert = Alert(level=level, title=title, message=message, metadata={})
        try:
            await telegram.send(alert)
        except Exception as exc:
            logger.warning("live_telegram_failed", error=str(exc))

    # Wire up signal generators for all tiers
    factory = SignalGeneratorFactory()
    for tier in EXPANSION_TIERS:
        tier.generator = factory.get_generator(tier.template)

    # Activate tier 1 (threshold=0) — now subject to the SAME auto-promotion
    # gate as expansion tiers (DEC-2026-06-01-002). Tier 1 was exempt under
    # DEC-2026-06-01-001 ("two decisions" follow-up); this closes that gap so
    # READY_FOR_LIVE is required uniformly across every live tier. State is
    # loaded first (read-only) so the alert reports the real position/PnL
    # whether or not the gate lets the tier trade.
    tier1 = EXPANSION_TIERS[0]
    tier1.state = load_state(store, tier1.session_id, tier1.symbol, tier1.state_file)
    tier1_blocked, tier1_block_reason = _tier1_activation_blocked(tier1.template)

    mode_label = "TESTNET" if testnet else "REAL MONEY"
    pos_detail = "FLAT"
    if tier1.state.get("in_position"):
        pos_detail = (
            f"IN {tier1.state.get('side', '?')} @ "
            f"${tier1.state.get('entry_price', 0):,.2f}"
        )

    if tier1_blocked:
        # tier1.active stays False — uniform with expansion-tier gating. The
        # kill switch is independent and remains in effect (DEC-2026-05-27-001).
        # If a prior position is open it is NOT managed while inactive; the
        # alert surfaces this so the operator can intervene manually.
        logger.warning(
            "live_tier1_activation_blocked_not_ready",
            tier=tier1.label,
            template=tier1.template,
            reason=tier1_block_reason,
            in_position=tier1.state.get("in_position", False),
        )
        unmanaged_note = (
            "\n[!] An open position exists and is NOT managed while tier 1 is "
            "inactive — close it manually if needed."
            if tier1.state.get("in_position") else ""
        )
        await send_alert(
            title=f"Tier 1 BLOCKED — Not Started [{mode_label}]",
            message=(
                f"Tier 1: {tier1.label} ({tier1.template})\n"
                f"Blocked: {tier1_block_reason}.\n"
                f"Gate (DEC-2026-05-27-004): N>=30 AND PF>=1.35 AND "
                f"Sharpe>=1.0 AND MaxDD<=5%.\n"
                f"Tier 1 will NOT trade until paper data clears the gate.\n"
                f"Position: {pos_detail}{unmanaged_note}\n"
                f"Realized: ${tier1.state.get('realized_pnl', 0):+.2f}\n"
                f"Trades: {tier1.state.get('total_trades', 0)}"
            ),
            level=AlertLevel.WARNING,
        )
        # Tier 1 stays inactive, so the expansion-activation loop will re-check
        # it every poll (threshold 0.0) — desirable, as it lets tier 1 come
        # online automatically once paper data clears the gate. Pre-set the
        # alert-dedup flags so that re-check does not emit a duplicate blocked
        # alert this session (mirrors the expansion-tier "alert once" contract;
        # both flags set because the verdict may be DEGRADED, which the
        # demotion check would otherwise re-alert).
        tier1.state["_promotion_alerted"] = True
        tier1.state["_degradation_alerted"] = True
    else:
        tier1.active = True
        await send_alert(
            title=f"Live Trading Started [{mode_label}]",
            message=(
                f"Tier 1: {tier1.label}\n"
                f"Capital/strategy: ${PER_STRATEGY_CAPITAL:.2f} "
                f"({PER_STRATEGY_ALLOCATION_PCT:.0%} of ${LIVE_CAPITAL:.2f}, "
                f"max {MAX_STRATEGIES_LIVE_CONCURRENT} concurrent)\n"
                f"Per Trade: {POSITION_SIZE_FRACTION:.0%} of equity\n"
                f"Risk: daily -{MAX_DAILY_LOSS_PCT:.0%} | DD -{MAX_DRAWDOWN_PCT:.0%}\n"
                f"Mode: {mode_label}\n"
                f"Position: {pos_detail}\n"
                f"Realized: ${tier1.state.get('realized_pnl', 0):+.2f}\n"
                f"Trades: {tier1.state.get('total_trades', 0)}\n"
                f"Expansion tiers waiting: "
                f"{sum(1 for t in EXPANSION_TIERS[1:] if not t.active)}"
            ),
        )

    # Regime detection: coarse (BTC daily EMA50/EMA200) + fine SubRegime
    # (adds ADX trend strength + realized-vol classification on top of macro).
    # Decision: DEC-2026-05-28-003 — SubRegime-aware tier routing.
    regime_detector = RegimeDetector(fetcher=fetcher)
    sub_regime_detector = SubRegimeDetector(fetcher=fetcher)
    cached_regime: RegimeState = RegimeState.UNKNOWN
    prev_regime: RegimeState = RegimeState.UNKNOWN
    cached_sub_regime: SubRegime = SubRegime.UNKNOWN
    prev_sub_regime: SubRegime = SubRegime.UNKNOWN

    stop_event = asyncio.Event()

    def handle_signal(sig: int, frame: Any) -> None:
        print(f"\nReceived signal {sig}, shutting down...")
        stop_event.set()

    signal_mod.signal(signal_mod.SIGINT, handle_signal)
    signal_mod.signal(signal_mod.SIGTERM, handle_signal)

    print(f"\nPolling every {POLLING_INTERVAL}s. Press Ctrl+C to stop.\n")

    poll_count = 0
    # Suppress Telegram alerts on isolated transient failures — only escalate
    # after CONSECUTIVE_FAILURES_TO_ALERT in a row, which represents a real
    # ongoing problem (e.g. API key revoked, Binance outage) rather than a
    # single read-timeout that self-heals. Decision: DEC-2026-05-27-003.
    CONSECUTIVE_FAILURES_TO_ALERT = 3
    consecutive_failures = 0

    while not stop_event.is_set():
        poll_count += 1

        try:
            # -----------------------------------------------------------
            # Regime check — on startup and every 60 polls (~1 hour)
            # Uses 2-bar daily confirmation to prevent whipsaw switches.
            # Decision: DEC-2026-05-04-002
            # -----------------------------------------------------------
            if poll_count == 1 or poll_count % 60 == 0:
                new_regime = await regime_detector.get_confirmed_state()
                # SubRegime detection is fail-closed: errors return UNKNOWN
                # which causes regime_tags-tagged tiers to remain inactive.
                try:
                    new_sub_regime = await sub_regime_detector.get_confirmed_state()
                except Exception as exc:
                    logger.error(
                        "live_sub_regime_detection_failed",
                        error=str(exc),
                        exc_info=True,
                    )
                    new_sub_regime = SubRegime.UNKNOWN

                regime_flipped = new_regime != cached_regime
                sub_flipped = new_sub_regime != cached_sub_regime

                if regime_flipped or sub_flipped:
                    prev_regime = cached_regime
                    prev_sub_regime = cached_sub_regime
                    cached_regime = new_regime
                    cached_sub_regime = new_sub_regime
                    logger.info(
                        "live_regime_changed",
                        previous=prev_regime.value,
                        current=cached_regime.value,
                        previous_sub=prev_sub_regime.value,
                        current_sub=cached_sub_regime.value,
                    )
                    await send_alert(
                        title="Regime Change Detected",
                        message=(
                            f"Coarse: {prev_regime.value} -> {cached_regime.value}\n"
                            f"Sub:    {prev_sub_regime.value} -> {cached_sub_regime.value}\n"
                            f"Tier activation now routes on sub_regime when "
                            f"`regime_tags` is set.\n"
                            f"Open positions still managed (stops/TP active)."
                        ),
                        level=AlertLevel.WARNING,
                    )

            # -----------------------------------------------------------
            # Tier activation check — evaluate inactive tiers each poll
            # -----------------------------------------------------------
            active_equity = sum(
                t.capital + t.state.get("realized_pnl", 0.0)
                for t in EXPANSION_TIERS if t.active
            )

            for tier in EXPANSION_TIERS:
                if tier.active:
                    continue
                regime_ok = _tier_regime_match(
                    tier, cached_regime, cached_sub_regime,
                )
                if regime_ok and active_equity >= tier.activation_threshold:
                    # Demotion guardrail: block activation if paper data shows
                    # the strategy is currently degraded. Decision: DEC-2026-05-27-004.
                    is_degraded, reason = _paper_strategy_is_degraded(tier.template)
                    if is_degraded:
                        logger.warning(
                            "live_tier_activation_blocked",
                            tier=tier.label,
                            reason=reason,
                        )
                        # Send a one-time alert per tier per poll cycle.
                        # tier.active stays False so we keep checking but
                        # set a flag to avoid alert spam on every poll.
                        if not tier.state.get("_degradation_alerted"):
                            await send_alert(
                                title=f"Tier Activation Blocked: {tier.label}",
                                message=(
                                    f"{tier.label} ({tier.template}) was "
                                    f"eligible by equity but live paper "
                                    f"performance shows degradation.\n"
                                    f"Reason: {reason}\n"
                                    f"Action: tier will remain inactive "
                                    f"until paper performance improves or "
                                    f"DEGRADATION thresholds are revised."
                                ),
                                level=AlertLevel.WARNING,
                            )
                            tier.state["_degradation_alerted"] = True
                        continue

                    # Auto-promotion gate (DEC-2026-06-01-001): a tier may only
                    # activate if its pooled live-paper performance is classified
                    # READY_FOR_LIVE. Closes the gap where a brand-new (N=0 ->
                    # RESEARCH) or still-maturing (OBSERVING) strategy passed the
                    # demotion check — which only catches PF<0.8 at N>=10 — and
                    # activated with no validation. Fails OPEN when the DB can't
                    # be read (db_ok False), mirroring the demotion check, so a
                    # transient outage never blocks a restart.
                    classification, db_ok = _paper_strategy_classification(tier.template)
                    if db_ok and classification != "READY_FOR_LIVE":
                        logger.info(
                            "live_tier_activation_blocked_not_ready",
                            tier=tier.label,
                            classification=classification,
                        )
                        if not tier.state.get("_promotion_alerted"):
                            await send_alert(
                                title=f"Tier Activation Blocked: {tier.label}",
                                message=(
                                    f"{tier.label} ({tier.template}) is eligible by "
                                    f"equity + regime but live-paper performance is "
                                    f"classified {classification}, not READY_FOR_LIVE.\n"
                                    f"Gate (DEC-2026-05-27-004): N>=30 AND PF>=1.35 "
                                    f"AND Sharpe>=1.0 AND MaxDD<=5%.\n"
                                    f"Tier stays inactive until paper data clears "
                                    f"the gate."
                                ),
                                level=AlertLevel.WARNING,
                            )
                            tier.state["_promotion_alerted"] = True
                        continue

                    # Portfolio capital limits (PARA-12 / DEC-2026-05-31-003):
                    # concurrency cap + capital reserve. An eligible,
                    # non-degraded tier still waits if the portfolio is already
                    # at its strategy count or capital ceiling.
                    can_activate, block_reason = _can_activate_tier(
                        tier,
                        EXPANSION_TIERS,
                        max_concurrent=MAX_STRATEGIES_LIVE_CONCURRENT,
                        reserve_cap_usdt=LIVE_CAPITAL * CAPITAL_RESERVE_FRACTION,
                    )
                    if not can_activate:
                        logger.info(
                            "live_tier_activation_deferred",
                            tier=tier.label,
                            reason=block_reason,
                        )
                        continue

                    tier.active = True
                    tier.state = load_state(
                        store, tier.session_id, tier.symbol, tier.state_file
                    )
                    logger.info(
                        "live_tier_activated",
                        tier=tier.label,
                        threshold=tier.activation_threshold,
                        active_equity=active_equity,
                    )
                    await send_alert(
                        title=f"New Tier Activated: {tier.label}",
                        message=(
                            f"Strategy: {tier.template}\n"
                            f"Symbol: {tier.symbol}\n"
                            f"Capital: ${tier.capital:.2f}\n"
                            f"Regime tag: {tier.regime_tag}\n"
                            f"Triggered by equity: ${active_equity:.2f} "
                            f">= threshold ${tier.activation_threshold:.2f}\n"
                            f"Active tiers now: "
                            f"{sum(1 for t in EXPANSION_TIERS if t.active)}"
                        ),
                    )

            # -----------------------------------------------------------
            # Process each active tier
            # -----------------------------------------------------------
            active_tiers = [t for t in EXPANSION_TIERS if t.active]

            if poll_count % 12 == 0:
                now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
                print(
                    f"[{now_str} UTC] Poll #{poll_count} | "
                    f"Regime: {cached_regime.value} | "
                    f"Active tiers: {len(active_tiers)}",
                    flush=True,
                )

            for tier in active_tiers:
                regime_allows_entry = _tier_regime_match(
                    tier, cached_regime, cached_sub_regime,
                )
                await _process_tier(
                    tier=tier,
                    adapter=adapter,
                    fetcher=fetcher,
                    store=store,
                    regime_allows_entry=regime_allows_entry,
                    send_alert=send_alert,
                    poll_count=poll_count,
                )

            # -----------------------------------------------------------
            # Hourly Telegram summary (every 60 polls)
            # -----------------------------------------------------------
            if poll_count % 60 == 0:
                now_utc = datetime.now(timezone.utc)
                tier_lines = []
                for tier in active_tiers:
                    eq = _get_current_equity(tier.state, tier.capital)
                    pos = (
                        f"IN {tier.state.get('side', '?')} @ "
                        f"${tier.state.get('entry_price', 0):,.2f}"
                        if tier.state.get("in_position") else "FLAT"
                    )
                    tier_lines.append(
                        f"{tier.label}: {pos} | "
                        f"Equity ${eq:.2f} | "
                        f"Realized ${tier.state.get('realized_pnl', 0):+.2f} | "
                        f"Trades {tier.state.get('total_trades', 0)}"
                    )

                total_eq = sum(
                    _get_current_equity(t.state, t.capital)
                    for t in active_tiers
                )
                next_tier = next(
                    (t for t in EXPANSION_TIERS if not t.active), None
                )
                next_str = (
                    f"Next tier: {next_tier.label} at "
                    f"${next_tier.activation_threshold:.0f} "
                    f"(regime: {next_tier.regime_tag})"
                    if next_tier else "All tiers active"
                )

                await send_alert(
                    title=f"Hourly Update — {now_utc.strftime('%Y-%m-%d %H:%M')} UTC",
                    message=(
                        "\n".join(tier_lines) + "\n"
                        f"---\n"
                        f"Total portfolio equity: ${total_eq:.2f}\n"
                        f"Regime: {cached_regime.value}\n"
                        f"{next_str}"
                    ),
                )

            # Poll succeeded — reset the consecutive-failure counter and
            # send a recovery alert if we had previously escalated.
            if consecutive_failures >= CONSECUTIVE_FAILURES_TO_ALERT:
                await send_alert(
                    title="Live Trading Recovered",
                    message=(
                        f"Live trading recovered after "
                        f"{consecutive_failures} consecutive failed polls. "
                        f"Resuming normal operation at poll #{poll_count}."
                    ),
                    level=AlertLevel.INFO,
                )
            consecutive_failures = 0

        except Exception as exc:
            consecutive_failures += 1
            logger.error(
                "live_poll_error",
                error=str(exc),
                poll=poll_count,
                consecutive_failures=consecutive_failures,
                exc_info=True,
            )
            # Only escalate to Telegram once we've crossed the threshold,
            # and then only on the boundary crossing to avoid alert storms.
            if consecutive_failures == CONSECUTIVE_FAILURES_TO_ALERT:
                await send_alert(
                    title="Live Trading Error",
                    message=(
                        f"{consecutive_failures} consecutive polls have "
                        f"failed (latest poll #{poll_count}). Last error: "
                        f"{exc}"
                    ),
                    level=AlertLevel.ERROR,
                )

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLLING_INTERVAL)
            break
        except asyncio.TimeoutError:
            continue

    # Shutdown summary
    active_tiers = [t for t in EXPANSION_TIERS if t.active]
    tier_summaries = []
    for tier in active_tiers:
        pos = (
            f"IN {tier.state.get('side', '?')} @ "
            f"${tier.state.get('entry_price', 0):,.2f}"
            if tier.state.get("in_position") else "FLAT"
        )
        tier_summaries.append(
            f"{tier.label}: {pos} | "
            f"Realized ${tier.state.get('realized_pnl', 0):+.2f} | "
            f"Trades {tier.state.get('total_trades', 0)}"
        )
    summary = (
        "\n".join(tier_summaries) + "\n"
        f"---\n"
        f"Regime at shutdown: {cached_regime.value}"
    )
    print(f"\n{summary}")
    await send_alert(title="Live Trading Stopped", message=summary)

    if telegram:
        await telegram.close()

    print("\nDone.")


if __name__ == "__main__":
    import time as _time

    from src.utils.geo_block import (
        GEO_BLOCK_EXIT_CODE,
        is_geo_block_error,
        print_geo_block_message,
    )

    MAX_CRASH_RESTARTS = 5
    CRASH_COOLDOWN = 60

    for attempt in range(1, MAX_CRASH_RESTARTS + 1):
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            print("\nKeyboard interrupt — exiting.")
            break
        except Exception as fatal:
            # Fail-fast on Binance geo-block: retries cannot fix a
            # regulatory IP rejection. Exit with the dedicated code
            # that tells the supervisor NOT to restart.
            # Decision: DEC-2026-06-01-003.
            if is_geo_block_error(fatal):
                logger.error(
                    "live_geo_block_detected",
                    error=str(fatal),
                    attempt=attempt,
                )
                print_geo_block_message(context="live_trading")
                sys.exit(GEO_BLOCK_EXIT_CODE)

            print(
                f"\nFATAL ERROR (attempt {attempt}/{MAX_CRASH_RESTARTS}): {fatal}",
                flush=True,
            )
            logger.error("live_fatal_crash", error=str(fatal), attempt=attempt)
            if attempt < MAX_CRASH_RESTARTS:
                print(f"Restarting in {CRASH_COOLDOWN}s...", flush=True)
                _time.sleep(CRASH_COOLDOWN)
            else:
                print("Max restarts reached — stopping to prevent Telegram spam.")
                sys.exit(1)
