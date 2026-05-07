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
from src.core.strategy.regime import RegimeDetector, RegimeRouter, RegimeState
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

BULL_STRATEGY_CONFIG: dict[str, dict[str, Any]] = {
    "macd_pullback": {
        # SUPERVISED-validated: 2 passes (DOGE Sharpe=3.8/PF=1.60, AVAX Sharpe=2.1/PF=1.45)
        # stop=2.5x ATR (sweep-validated, widened from 2.0), tol=0.5% pullback zone
        "label": "MACD_PB",
        "regime": "bull",
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
        },
    },
    "bull_trend_pullback": {
        # Quality-validated (90d): BTC PF=1.79/Sharpe=1.60, ETH PF=2.21/Sharpe=2.27,
        # BNB PF=1.72/Sharpe=1.73. DD <2.5% on all three. Observing Gate 2 (40 trades).
        # htf_ema=150 and rsi_high=60 are sweep-optimal from 272-run parameter scan.
        "label": "BTP",
        "regime": "bull",
        "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
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

BEAR_STRATEGY_CONFIG: dict[str, dict[str, Any]] = {
    "bear_trend_follower": {
        # Validated bear: 100% WR, Sharpe 2.4-3.6 in Q1 2026 bear regime.
        "label": "BTF",
        "regime": "bear",
        "symbols": [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
            "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT",
        ],
        "params": {
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
        },
    },
    "cascading_momentum_filter": {
        # Validated bear (SOL/XRP/AVAX/ETH). Highest conviction in bear downtrends.
        "label": "CMF",
        "regime": "bear",
        "symbols": ["SOLUSDT", "XRPUSDT", "AVAXUSDT", "ETHUSDT"],
        "params": {
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
        },
    },
    "rsi_bb_mean_reversion": {
        # Mean-reversion: underperforms strong bull trends despite internal EMA(200) gate.
        # Reactivate in bear or extended ranging/consolidation conditions.
        "label": "RSI_BB",
        "regime": "bear",
        "symbols": ["ETHUSDT", "BNBUSDT", "DOGEUSDT"],
        "params": {
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
        },
    },
}

# ---------------------------------------------------------------------------
# All-regime strategies (run regardless of bull/bear)
# ---------------------------------------------------------------------------

ALL_REGIME_CONFIG: dict[str, dict[str, Any]] = {
    "ichimoku_cloud_trend": {
        # Regime-agnostic: Ichimoku cloud determines direction internally.
        # LONG above cloud, SHORT below — self-adjusts to bull and bear regimes.
        "label": "ICVP",
        "regime": "all",
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
                active_lines.append(
                    f"  {status.strategy_id}: "
                    f"IN {direction.upper()} "
                    f"unrealized ${status.unrealized_pnl:+.0f}"
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

    # Create regime router — auto-detects regime and manages engine lifecycle
    detector = RegimeDetector(fetcher=fetcher)
    router = RegimeRouter(
        detector=detector,
        engine_factory=engine_factory,
        full_config=FULL_STRATEGY_CONFIG,
        stop_event=stop_event,
        check_interval=86400,  # re-check daily
        telegram=telegram,
        store=store,
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
