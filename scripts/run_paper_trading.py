"""Paper trading runner for PARAVANT — regime-aware strategy portfolio.

Regime management is automated via RegimeDetector (BTC daily EMA(50)/EMA(200))
and RegimeRouter. Bull strategies run when EMA(50) > EMA(200); bear strategies
run when EMA(50) < EMA(200). ICVP (ichimoku_cloud_trend) runs in all regimes
as it is self-directing via cloud position.

Regime change requires 2 consecutive daily closes on the new macro side to
confirm, preventing whipsaw switches on single-candle fakeouts.

Active strategy universe:
    Bull regime:
        MACD_PB  — DOGE/AVAX         (SUPERVISED-validated, 2 passes)
        BTP      — BTC/ETH/BNB       (quality-validated, observing Gate 2)
    Bear regime:
        BTF      — all 8 symbols     (validated bear, 100% WR in Q1 2026)
        CMF      — SOL/XRP/AVAX/ETH  (validated bear, highest conviction)
        RSI_BB   — ETH/BNB/DOGE      (mean-reversion, underperforms strong bull)
    All regimes:
        ICVP     — all 8 symbols     (regime-agnostic via cloud direction)

Usage:
    PYTHONPATH=. .venv/Scripts/python scripts/run_paper_trading.py
    PYTHONPATH=. .venv/Scripts/python scripts/run_paper_trading.py --lite

Environment:
    BINANCE_API_KEY      - Required
    BINANCE_SECRET_KEY   - Required
    BINANCE_TESTNET      - false for mainnet data (default: true)
    TELEGRAM_BOT_TOKEN   - Optional (for trade alerts)
    TELEGRAM_CHAT_ID     - Optional (for trade alerts)

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-05-04-001 - Dual-EMA composite regime detection
Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule
"""
from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from src.core.alerting.channels.telegram import TelegramChannel
from src.core.alerting.manager import Alert, AlertLevel
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.paper.types import PaperTradingMode
from src.core.strategy.regime import (
    RegimeDetector,
    RegimeRouter,
    SubRegimeDetector,
)
from src.data.database import init_db
from src.data.market_data import MarketDataFetcher
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Strategy Configuration — Bull Regime
#
# These run when BTC EMA(50) > EMA(200) daily (2 consecutive closes confirmed).
# Decision: DEC-2026-05-04-001 / DEC-2026-05-04-002
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Regime tagging convention (DEC-2026-05-27-008):
#
# Each strategy declares `regime_tags` — the fine-grained SubRegimes it
# claims to work in. Valid values come from
# src.core.strategy.regime.historical_classifier.SubRegime:
#   trending_bull, choppy_bull, trending_bear, choppy_bear,
#   ranging, high_vol, transitional, unknown
#
# These tags are LOAD-BEARING: they're consumed by the rolling-window
# backtest validation and (eventually) by the regime router to decide
# which strategies activate.
#
# The tags below are PRELIMINARY professional estimates. They MUST be
# verified by running `scripts/backtest_rolling.py --strategy <name>`
# and confirming the strategy actually shows STABLE_EDGE_IN_REGIME in
# the regimes it claims. Tags inconsistent with empirical performance
# should be corrected.
# ---------------------------------------------------------------------------

BULL_STRATEGY_CONFIG: dict[str, dict[str, Any]] = {
    "macd_pullback": {
        # SUPERVISED-validated: 2 passes (DOGE Sharpe=3.8/PF=1.60, AVAX Sharpe=2.1/PF=1.45)
        # stop=2.5x ATR (sweep-validated, widened from 2.0), tol=0.5% pullback zone
        # regime_ema_period=200: blocks SHORT signals when price > EMA(200) — prevents
        # spurious bearish entries during bull-market MACD dips which would open a SHORT
        # position in the wrong direction and run against the prevailing trend.
        "label": "MACD_PB",
        "regime": "bull",
        # Empirically validated (DEC-2026-05-28-002): STABLE_EDGE in three
        # regimes on spot — choppy_bull (PF 1.58), choppy_bear (PF 2.33),
        # trending_bull (PF 1.65). 118 trades total. Multi-regime real edge.
        "regime_tags": ["choppy_bull", "choppy_bear", "trending_bull"],
        "symbols": ["DOGEUSDT", "AVAXUSDT"],
        "params": {
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "pullback_ema_period": 21,
            "atr_period": 14,
            "atr_stop_multiplier": 2.5,
            "risk_reward_ratio": 2.0,
            "pullback_tolerance_pct": 0.5,
            "regime_ema_period": 200,
        },
    },
    "bull_trend_pullback": {
        # Quality-validated (90d): BTC PF=1.79/Sharpe=1.60, ETH PF=2.21/Sharpe=2.27,
        # BNB PF=1.72/Sharpe=1.73. DD <2.5% on all three. Observing Gate 2 (40 trades).
        # htf_ema=150 and rsi_high=60 are sweep-optimal from 272-run parameter scan.
        # DOGE added 2026-05-07: 45d bull PF=5.10, Sharpe=7.15, WR=66.7% — Gate1=10.
        "label": "BTP",
        "regime": "bull",
        # Empirically validated (DEC-2026-05-28-002): STABLE_EDGE in
        # choppy_bear only (PF 1.63, PF min 1.30, CV 0.16 across 69 trades).
        # POOR in trending_bear/trending_bull/choppy_bull. The "bull
        # trend pullback" name is misleading — the actual edge is in
        # choppy_bear, not trending_bull. Re-tagged accordingly.
        "regime_tags": ["choppy_bear"],
        "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT"],
        "params": {
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
        },
    },
    # ----------------------------------------------------------------------
    # RETIRED 2026-05-28: volatility_regime_breakout (VRB)
    # ----------------------------------------------------------------------
    # BTC-only, single-window per regime in rolling backtest. Per-regime
    # PFs: choppy_bull 0.36, choppy_bear 1.43 (1 window only), trending_bear
    # 0.83 (POOR), trending_bull 2.40 (1 window only). No regime has both
    # sufficient windows AND stable edge. Generator code preserved at
    # src/core/strategy/generators/volatility_regime_breakout.py.
    # Decision: DEC-2026-05-28-002.
    # ----------------------------------------------------------------------
    "volume_balance_breakout": {
        # Promoted 2026-05-08. 90d backtest confirmed edge on BTC/ETH/SOL:
        # BTC PF=1.39/Sharpe=0.59/10 trades, ETH PF=1.94/Sharpe=1.83/9 trades,
        # SOL PF=2.02/Sharpe=1.66/10 trades. Results stable across 2 independent
        # test rounds. Low-frequency (6-11 trades/90d per symbol). Gate1=10 trades.
        # Institutional accumulation (up-volume ratio ≥60%) + range breakout +
        # volume confirmation. Fails on altcoins (XRP/AVAX/DOT) — large-caps only.
        "label": "VBB",
        "regime": "bull",
        # Empirically validated (DEC-2026-05-28-002): STABLE_EDGE in
        # choppy_bear only (PF 1.61, PF min 1.44, CV 0.14 across 32 trades).
        # POOR in choppy_bull (PF 0.64), trending_bull (PF 0.91), trending_bear
        # (PF 0.39). The "bull-tagged" framing in the legacy config was wrong;
        # VBB is a choppy_bear strategy.
        "regime_tags": ["choppy_bear"],
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "params": {
            "balance_period": 15,
            "balance_threshold": 0.60,
            "breakout_lookback": 10,
            "ema_period": 200,
            "rsi_period": 14,
            "rsi_min": 40.0,
            "rsi_max": 70.0,
            "volume_period": 20,
            "volume_threshold": 1.5,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "risk_reward_ratio": 3.0,
        },
    },
    "stoch_rsi_bull_cross": {
        # Promoted 2026-05-08. 3-round 90d backtest — exceptional large-cap edge:
        # BTC PF=8.71/Sharpe=3.185 (R3), 6.77 (R1) — best signal in portfolio
        # ETH PF=2.21/Sharpe=1.285 — identical across all 3 independent rounds
        # SOL PF=2.80/Sharpe=1.687 (R3), 2.72/2.82 prior rounds
        # All 3 with DD <3%, WR 50-60% on large-caps. Gate1=10 trades.
        # StochRSI K/D cross from oversold (<20) in confirmed bull trend (EMA-50/200).
        # Fails on altcoins (XRP/AVAX/DOT) — large-caps only, same as VBB pattern.
        "label": "SRC",
        "regime": "bull",
        # Empirically validated (DEC-2026-05-28-002): STABLE_EDGE in
        # choppy_bull (PF 1.56, CV 0.27) and PROMISING in choppy_bear
        # (PF 1.70). POOR in trending_bull/bear. Pullback signal works
        # in chop, fails in trends.
        "regime_tags": ["choppy_bull", "choppy_bear"],
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "params": {
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
        },
    },
    # ----------------------------------------------------------------------
    # RETIRED 2026-05-28: heikin_ashi_trend_pulse (HATP), vpt_momentum (VPT)
    # ----------------------------------------------------------------------
    # HATP: POOR in all 4 regimes (best PF 0.96 in choppy_bear, 231 trades).
    #       Promoted on Q1 3-round backtests showing PF 1.40-1.70; live-spec
    #       rolling backtest could not reproduce. Same overfit pattern as BTF.
    # VPT:  PF 1.00 overall (break-even). Loses after live slippage. Trending_bear
    #       (only 2-window regime) PF 0.80 POOR. BTC-only limits diagnosis.
    # Generator code preserved for both at src/core/strategy/generators/.
    # Decision: DEC-2026-05-28-002.
    # ----------------------------------------------------------------------
    "realized_vol_compression_breakout": {
        # Promoted 2026-05-08 (batch 3). 2-round 90d backtest — HV compression breakout.
        # AVAX: R2 PF=4.32, R3 PF=4.62 — signal STRENGTHENED across rounds (not decay).
        # 75% WR, Sharpe=2.295, 4T in R3. Ultra-low frequency. Gate1=5 trades.
        # BTC PF=0.23 (8T) — clearly wrong instrument. ETH Sharpe=0.432 (not ready).
        # Realized vol compression = statistical vol (std of log returns), not BB width.
        # hv_short < 0.65 × hv_medium for 3+ consecutive bars = real regime compression.
        "label": "RVCB",
        "regime": "bull",
        # OBSERVE-ONLY 2026-05-28 (DEC-2026-05-28-002): 19 trades total in
        # rolling backtest is insufficient sample for promotion. Trending_bear
        # PROMISING (PF 1.56, 2 windows). Other regimes single-window with
        # large PF values (5.58, 1.84) on 2-4 trades — pure noise. Keep
        # paper-running to accumulate trades; do not activate live tier.
        "observe_only": True,
        "regime_tags": ["trending_bear"],
        "symbols": ["AVAXUSDT"],
        "params": {
            "hv_short_period": 20,
            "hv_medium_period": 60,
            "hv_compression_ratio": 0.65,
            "hv_min_compression_bars": 3,
            "breakout_lookback": 20,
            "regime_ema_period": 200,
            "rsi_period": 14,
            "rsi_min": 50.0,
            "rsi_max": 78.0,
            "volume_period": 20,
            "volume_threshold": 1.3,
            "atr_period": 14,
            "atr_stop_multiplier": 2.0,
            "risk_reward_ratio": 2.5,
        },
    },
}

# ---------------------------------------------------------------------------
# Strategy Configuration — Bear Regime
#
# These run when BTC EMA(50) < EMA(200) daily (2 consecutive closes confirmed).
# Decision: DEC-2026-05-04-001 / DEC-2026-05-04-002
#
# IMPORTANT: Do NOT run BTF in bull — caused -$2,323 paper loss in April 2026
# when left active during a bull market.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# BEAR_STRATEGY_CONFIG is INTENTIONALLY EMPTY as of 2026-05-28.
#
# All previously-bear-tagged strategies have been retired after the spot-vs-
# futures rolling backtest comparison (DEC-2026-05-28-002) showed:
#   - BTF retired 2026-05-27 (DEC-2026-05-27-007): no edge in any regime.
#   - CMF: POOR in all 3 bear/chop regimes. "Trending_bull edge" is wrong
#          direction and unreliable.
#   - RSI_BB: PF 0.06–0.41 across all regimes. Worst PF in portfolio.
#
# The strategies that actually have STABLE_EDGE in choppy_bear (the current
# regime) are tagged "bull" in the legacy coarse regime field but tagged
# choppy_bear in the new regime_tags field — BTP, VBB, MACD_PB, SRC. They
# will route correctly once the SubRegime-aware live router (DEC-2026-05-28-001
# step 4 precursor) is built. Until then, paper trading runs nothing in
# bear regime by design — better to be quiet than to lose money.
# ---------------------------------------------------------------------------
BEAR_STRATEGY_CONFIG: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# All-regime strategies (run regardless of bull/bear)
# ---------------------------------------------------------------------------

ALL_REGIME_CONFIG: dict[str, dict[str, Any]] = {
    "ichimoku_cloud_trend": {
        # Regime-agnostic: Ichimoku cloud determines direction internally.
        # LONG above cloud, SHORT below — self-adjusts to bull and bear regimes.
        "label": "ICVP",
        "regime": "all",
        # Empirically validated (DEC-2026-05-28-002): PROMISING_IN_REGIME
        # in choppy_bull (PF 2.08), choppy_bear (PF 1.28), trending_bear
        # (PF 1.40, 14 windows — strongest evidence). POOR in trending_bull.
        # Multi-regime real edge; the most regime-resilient strategy in
        # the portfolio after MACD_PB.
        "regime_tags": ["choppy_bull", "choppy_bear", "trending_bear"],
        "symbols": [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
            "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT",
        ],
        "params": {
            "tenkan_period": 20,
            "kijun_period": 60,
            "senkou_b_period": 120,
            "displacement": 30,
            "atr_period": 14,
            "volume_period": 20,
            "volume_threshold": 1.3,
        },
    },
}

# ---------------------------------------------------------------------------
# Full configuration — merged view used by RegimeRouter
# ---------------------------------------------------------------------------

FULL_STRATEGY_CONFIG: dict[str, dict[str, Any]] = {
    **BULL_STRATEGY_CONFIG,
    **BEAR_STRATEGY_CONFIG,
    **ALL_REGIME_CONFIG,
}

# Backward-compatibility aliases preserved for reference
STRATEGY_CONFIG = BULL_STRATEGY_CONFIG  # active at time of last manual switch
SUSPENDED_STRATEGY_CONFIG = BEAR_STRATEGY_CONFIG  # suspended shelf at that time

# Lite mode: one session per strategy for local testing
LITE_SYMBOLS: dict[str, list[str]] = {
    "macd_pullback": ["DOGEUSDT"],
    "bull_trend_pullback": ["BTCUSDT"],
    "ichimoku_cloud_trend": ["BTCUSDT"],
    "bear_trend_follower": ["BTCUSDT"],
    "cascading_momentum_filter": ["SOLUSDT"],
    "rsi_bb_mean_reversion": ["ETHUSDT"],
    "heikin_ashi_trend_pulse": ["BTCUSDT"],
    "vpt_momentum": ["BTCUSDT"],
    "realized_vol_compression_breakout": ["AVAXUSDT"],
}

# Status report interval (seconds)
STATUS_INTERVAL = 900  # 15 minutes (aligned with polling interval)
# Telegram trade check interval (seconds)
TRADE_CHECK_INTERVAL = 900  # 15 minutes (aligned with polling interval)


# ---------------------------------------------------------------------------
# Engine Builder
# ---------------------------------------------------------------------------


def build_engines(
    factory: SignalGeneratorFactory,
    series_provider: Any,
    config: BacktestConfig,
    store: DataStore,
    strategy_config: dict[str, dict[str, Any]],
    lite: bool = False,
) -> list[PaperTradingEngine]:
    """Create PaperTradingEngine instances for all strategy-symbol pairs.

    Args:
        factory: Signal generator factory.
        series_provider: Async callable for OHLCV data.
        config: Backtest/paper trading configuration.
        store: DataStore for session persistence.
        strategy_config: Subset of FULL_STRATEGY_CONFIG for the current regime.
        lite: If True, use reduced symbol set for testing.

    Returns:
        List of PaperTradingEngine instances ready to start.
    """
    engines: list[PaperTradingEngine] = []

    for template_id, cfg in strategy_config.items():
        label = cfg["label"]
        symbols = LITE_SYMBOLS.get(template_id, []) if lite else cfg["symbols"]
        params = cfg["params"]

        for symbol in symbols:
            strategy = SimpleNamespace(
                id=f"paper_{label}_{symbol}",
                name=f"{label} {symbol}",
                symbols=[symbol],
                parameters=params,
                template_id=template_id,
            )

            engine = PaperTradingEngine(
                strategy=strategy,
                signal_generator_factory=factory,
                series_provider=series_provider,
                mode=PaperTradingMode.LIVE,
                config=config,
                store=store,
            )
            engines.append(engine)

            logger.info(
                "engine_created",
                session_id=strategy.id,
                template=template_id,
                symbol=symbol,
            )

    return engines


# ---------------------------------------------------------------------------
# Monitoring Tasks
#
# All three tasks accept a Callable[[], list[PaperTradingEngine]] rather than
# a static list so they automatically observe the correct engines after a
# regime flip. They wait before first action (STATUS_INTERVAL / TRADE_CHECK_INTERVAL
# / 3600s), so the router will always have engines by the time they check.
# ---------------------------------------------------------------------------


async def status_reporter(
    get_engines: Callable[[], list[PaperTradingEngine]],
    stop_event: asyncio.Event,
) -> None:
    """Periodically log status of all running engines.

    Args:
        get_engines: Callable returning the current list of active engines.
        stop_event: Signal to stop reporting.
    """
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=STATUS_INTERVAL
            )
            break
        except asyncio.TimeoutError:
            pass

        engines = get_engines()
        running = [e for e in engines if e.is_running]
        if not running:
            continue

        total_realized = 0.0
        total_unrealized = 0.0
        total_completed = 0
        total_open = 0
        lines: list[str] = []
        for engine in engines:
            status = engine.get_status()
            total_realized += status.realized_pnl
            total_unrealized += status.unrealized_pnl
            total_completed += status.num_trades
            if status.has_open_position:
                total_open += 1
                lines.append(
                    f"  {status.strategy_id}: "
                    f"IN {(status.open_position_direction or '?').upper()} "
                    f"unrealized ${status.unrealized_pnl:+.0f}"
                )

        print(
            f"\n[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] "
            f"Sessions: {len(running)}/{len(engines)} | "
            f"Open: {total_open} | "
            f"Closed: {total_completed} | "
            f"Unrealized: ${total_unrealized:+,.0f} | "
            f"Realized: ${total_realized:+,.0f}",
            flush=True,
        )
        for line in lines:
            print(line, flush=True)


async def trade_monitor(
    get_engines: Callable[[], list[PaperTradingEngine]],
    telegram: TelegramChannel | None,
    stop_event: asyncio.Event,
) -> None:
    """Monitor engines for position entries AND trade exits, send Telegram alerts.

    Tracks per-engine state lazily — tracking dicts are synced each iteration
    so new engines added after a regime flip are picked up automatically.

    Args:
        get_engines: Callable returning the current list of active engines.
        telegram: Telegram channel for alerts (or None to skip).
        stop_event: Signal to stop monitoring.
    """
    if telegram is None:
        return

    # Lazy tracking: populated and synced on each iteration
    last_counts: dict[str, int] = {}
    had_position: dict[str, bool] = {}

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=TRADE_CHECK_INTERVAL
            )
            break
        except asyncio.TimeoutError:
            pass

        engines = get_engines()

        # Sync tracking state: register any new engines (after regime flip)
        for engine in engines:
            sid = engine.strategy_id
            if sid not in last_counts:
                last_counts[sid] = 0
                had_position[sid] = False

        for engine in engines:
            if not engine.is_running:
                continue

            status = engine.get_status()
            sid = engine.strategy_id
            prev_had_pos = had_position.get(sid, False)
            prev_count = last_counts.get(sid, 0)

            # --- ENTRY ALERT: was flat, now has a position ---
            if status.has_open_position and not prev_had_pos:
                direction = status.open_position_direction or "?"
                entry_price = status.open_position_entry_price
                price_str = f"${entry_price:,.2f}" if entry_price else "?"

                msg = (
                    f"Direction: {direction}\n"
                    f"Entry Price: {price_str}\n"
                    f"Equity: ${status.current_equity:,.2f}"
                )

                alert = Alert(
                    level=AlertLevel.INFO,
                    title=f"OPENED: {sid}",
                    message=msg,
                    metadata={
                        "strategy": sid,
                        "direction": direction,
                        "entry_price": price_str,
                    },
                )
                try:
                    await telegram.send(alert)
                except Exception as exc:
                    logger.error(
                        "telegram_entry_alert_failed",
                        error=str(exc),
                        strategy_id=sid,
                    )

            # --- EXIT ALERT: trade count went up (round-trip completed) ---
            if status.num_trades > prev_count:
                trades = engine.get_trade_log()
                new_trades = trades[prev_count:]

                for trade in new_trades:
                    direction = trade.get("direction", "?")
                    symbol = trade.get("symbol", "?")
                    pnl = trade.get("realized_pnl", 0.0)
                    ret_pct = trade.get("return_pct", 0.0)

                    msg = (
                        f"Direction: {direction}\n"
                        f"Entry: ${trade.get('entry_price', 0):,.2f} -> "
                        f"Exit: ${trade.get('exit_price', 0):,.2f}\n"
                        f"PnL: ${pnl:+.2f} ({ret_pct:+.2f}%)\n"
                        f"Equity: ${status.current_equity:,.2f}"
                    )

                    alert = Alert(
                        level=AlertLevel.INFO,
                        title=f"CLOSED: {sid}",
                        message=msg,
                        metadata={
                            "strategy": sid,
                            "symbol": symbol,
                            "pnl": f"${pnl:+.2f}",
                        },
                    )
                    try:
                        await telegram.send(alert)
                    except Exception as exc:
                        logger.error(
                            "telegram_exit_alert_failed",
                            error=str(exc),
                            strategy_id=sid,
                        )

            # Update tracked state
            had_position[sid] = status.has_open_position
            last_counts[sid] = status.num_trades


async def hourly_summary(
    get_engines: Callable[[], list[PaperTradingEngine]],
    telegram: TelegramChannel | None,
    stop_event: asyncio.Event,
) -> None:
    """Send hourly portfolio summary via Telegram.

    Args:
        get_engines: Callable returning the current list of active engines.
        telegram: Telegram channel for alerts (or None to skip).
        stop_event: Signal to stop.
    """
    if telegram is None:
        return

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=3600
            )
            break
        except asyncio.TimeoutError:
            pass

        engines = get_engines()
        total_completed = 0
        total_open = 0
        total_realized = 0.0
        total_unrealized = 0.0
        active_lines: list[str] = []

        for engine in engines:
            status = engine.get_status()
            total_completed += status.num_trades
            total_realized += status.realized_pnl
            if status.has_open_position:
                total_open += 1
                total_unrealized += status.unrealized_pnl
                direction = status.open_position_direction or "?"
                # Show open-position state AND any historical closed
                # trades from this session, so the summary doesn't hide
                # closed-trade PnL just because a new position is open.
                history_str = (
                    f" | {status.num_trades}T closed "
                    f"${status.realized_pnl:+.0f}"
                    if status.num_trades > 0 else ""
                )
                active_lines.append(
                    f"  {status.strategy_id}: "
                    f"IN {direction.upper()} "
                    f"unrealized ${status.unrealized_pnl:+.0f}"
                    f"{history_str}"
                )
            elif status.num_trades > 0:
                active_lines.append(
                    f"  {status.strategy_id}: "
                    f"{status.num_trades}T closed "
                    f"realized ${status.realized_pnl:+.0f}"
                )

        running = sum(1 for e in engines if e.is_running)
        msg = (
            f"Sessions: {running}/{len(engines)}\n"
            f"Open Positions: {total_open}\n"
            f"Completed Trades: {total_completed}\n"
            f"Unrealized PnL: ${total_unrealized:+,.0f}\n"
            f"Realized PnL: ${total_realized:+,.0f}\n"
        )
        if active_lines:
            msg += "\nActive:\n" + "\n".join(active_lines)
        else:
            msg += "\nNo open positions or completed trades yet."

        alert = Alert(
            level=AlertLevel.INFO,
            title="Paper Trading Hourly Summary",
            message=msg,
            metadata={"sessions": running, "trades": total_completed},
        )
        try:
            await telegram.send(alert)
        except Exception as exc:
            logger.error("hourly_summary_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------


async def main(lite: bool = False) -> None:
    """Main paper trading runner — regime-aware.

    Creates a RegimeDetector + RegimeRouter which detect the current BTC regime
    and start the appropriate strategy engines automatically. Monitoring tasks
    call router.get_active_engines() dynamically so they observe the correct
    sessions after any regime flip.

    Args:
        lite: If True, use reduced symbol set (one symbol per strategy).
    """
    print("=" * 60)
    print("PARAVANT Paper Trading Runner")
    print(f"Mode: {'LITE' if lite else 'FULL'}  |  Regime: AUTO-DETECTED")
    print(f"Universe: {len(FULL_STRATEGY_CONFIG)} strategies across all regimes")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    # Initialize database (idempotent)
    init_db()

    # Initialize components
    fetcher = MarketDataFetcher()
    factory = SignalGeneratorFactory()
    store = DataStore()

    config = BacktestConfig(
        initial_capital=10_000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    async def series_provider(symbol: str, lookback_bars: int) -> Any:
        """Fetch recent OHLCV bars for paper trading."""
        try:
            return await fetcher.fetch_ohlcv(
                symbol=symbol,
                timeframe="1h",
                limit=min(lookback_bars, 1000),
            )
        except Exception as exc:
            logger.error(
                "series_fetch_failed",
                symbol=symbol,
                lookback_bars=lookback_bars,
                error=str(exc),
            )
            return None

    def engine_factory(template_ids: list[str]) -> list[PaperTradingEngine]:
        """Build engines for the given template IDs from FULL_STRATEGY_CONFIG."""
        subset = {
            tid: cfg
            for tid, cfg in FULL_STRATEGY_CONFIG.items()
            if tid in template_ids
        }
        return build_engines(factory, series_provider, config, store, subset, lite=lite)

    # Telegram setup (optional)
    telegram: TelegramChannel | None = None
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        telegram = TelegramChannel(bot_token=bot_token, chat_id=chat_id)
        print("Telegram alerts: ENABLED")
    else:
        print("Telegram alerts: DISABLED (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)")

    # Graceful shutdown event
    stop_event = asyncio.Event()

    def handle_signal(sig: int, frame: Any) -> None:
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        print(f"\nReceived signal {sig}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Create regime router — auto-detects coarse regime + fine SubRegime
    # and manages engine lifecycle. Strategies with `regime_tags` route via
    # SubRegime; strategies with only legacy `regime` route via coarse state.
    # Decision: DEC-2026-05-28-003.
    detector = RegimeDetector(fetcher=fetcher)
    sub_detector = SubRegimeDetector(fetcher=fetcher)
    router = RegimeRouter(
        detector=detector,
        engine_factory=engine_factory,
        full_config=FULL_STRATEGY_CONFIG,
        stop_event=stop_event,
        check_interval=86400,  # re-check daily
        telegram=telegram,
        store=store,
        sub_detector=sub_detector,
    )

    print("\nDetecting initial regime and starting engines...")
    print("(Regime check uses BTC daily EMA(50)/EMA(200) with 2-bar confirmation)")
    print("-" * 60)

    # Startup alert
    if telegram:
        startup_alert = Alert(
            level=AlertLevel.INFO,
            title="Paper Trading Started",
            message=(
                f"Mode: {'LITE' if lite else 'FULL'}\n"
                f"Regime: AUTO-DETECTED (BTC EMA(50)/EMA(200))\n"
                f"Universe: {len(FULL_STRATEGY_CONFIG)} strategy templates\n"
                f"Capital: $10,000 per session"
            ),
        )
        try:
            await telegram.send(startup_alert)
        except Exception:
            pass

    # Launch regime router (manages engine lifecycle) and monitoring tasks
    router_task = asyncio.create_task(router.run())

    monitor_tasks = [
        asyncio.create_task(
            status_reporter(router.get_active_engines, stop_event)
        ),
        asyncio.create_task(
            trade_monitor(router.get_active_engines, telegram, stop_event)
        ),
        asyncio.create_task(
            hourly_summary(router.get_active_engines, telegram, stop_event)
        ),
    ]

    # Wait for shutdown signal
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        pass

    # Cancel monitoring tasks
    for task in monitor_tasks:
        task.cancel()

    # Await router task (it stops engines on stop_event)
    try:
        await asyncio.wait_for(router_task, timeout=60)
    except (asyncio.TimeoutError, Exception):
        router_task.cancel()

    # Print final summary
    final_engines = router.get_active_engines()
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print(f"Regime at shutdown: {router.get_current_regime().value}")
    print("=" * 60)

    total_trades = 0
    total_pnl = 0.0
    for engine in final_engines:
        status = engine.get_status()
        total_trades += status.num_trades
        total_pnl += status.current_pnl
        if status.num_trades > 0:
            print(
                f"  {status.strategy_id}: "
                f"${status.current_equity:,.0f} "
                f"({status.current_pnl_pct:+.2f}%) "
                f"{status.num_trades} trades"
            )

    print(f"\nTotal Trades: {total_trades}")
    print(f"Total PnL: ${total_pnl:+,.2f}")
    elapsed = final_engines[0].get_status().days_elapsed if final_engines else 0
    print(f"Elapsed: {elapsed:.1f} days")

    # Send shutdown alert
    if telegram:
        shutdown_alert = Alert(
            level=AlertLevel.INFO,
            title="Paper Trading Stopped",
            message=(
                f"Sessions: {len(final_engines)}\n"
                f"Total Trades: {total_trades}\n"
                f"Total PnL: ${total_pnl:+,.2f}\n"
                f"Duration: {elapsed:.1f} days"
            ),
        )
        try:
            await telegram.send(shutdown_alert)
            await telegram.close()
        except Exception:
            pass

    print("\nDone.")


if __name__ == "__main__":
    import time as _time

    from src.utils.geo_block import (
        GEO_BLOCK_EXIT_CODE,
        is_geo_block_error,
        print_geo_block_message,
    )

    parser = argparse.ArgumentParser(description="PARAVANT Paper Trading Runner")
    parser.add_argument(
        "--lite",
        action="store_true",
        help="Run with reduced symbol set (one symbol per strategy)",
    )
    args = parser.parse_args()

    # Crash-loop protection: max retries with cooldown
    MAX_CRASH_RESTARTS = 5
    CRASH_COOLDOWN = 60

    for attempt in range(1, MAX_CRASH_RESTARTS + 1):
        try:
            asyncio.run(main(lite=args.lite))
            break
        except KeyboardInterrupt:
            break
        except Exception as fatal:
            # Fail-fast on Binance geo-block: retries cannot fix a
            # regulatory IP rejection, so exit with the dedicated code
            # that tells the supervisor (run_all.py) NOT to restart.
            # Decision: DEC-2026-06-01-003.
            if is_geo_block_error(fatal):
                print_geo_block_message(context="paper_trading")
                sys.exit(GEO_BLOCK_EXIT_CODE)

            print(
                f"FATAL (attempt {attempt}/{MAX_CRASH_RESTARTS}): {fatal}",
                flush=True,
            )
            if attempt < MAX_CRASH_RESTARTS:
                print(f"Restarting in {CRASH_COOLDOWN}s...", flush=True)
                _time.sleep(CRASH_COOLDOWN)
            else:
                print("Max restarts reached. Exiting.", flush=True)
                sys.exit(1)
