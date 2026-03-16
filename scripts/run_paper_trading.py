"""Paper trading runner for PARAVANT Tier 1 promoted strategies.

Runs promoted strategies (BTF, ICVP, CMF, RSI_BB v1.2) on live market data
via Binance 1H polling. Each strategy-symbol pair runs as an independent
paper trading session with $10,000 simulated capital.

Sends Telegram alerts on new trades and hourly status updates (if configured).

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
"""
from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from src.core.alerting.channels.telegram import TelegramChannel
from src.core.alerting.manager import Alert, AlertLevel
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.paper.engine import PaperTradingEngine
from src.core.strategy.paper.types import PaperTradingMode
from src.data.database import init_db
from src.data.market_data import MarketDataFetcher
from src.data.store import DataStore
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Strategy Configuration — Tier 1 promoted strategies
# ---------------------------------------------------------------------------

STRATEGY_CONFIG: dict[str, dict[str, Any]] = {
    "bear_trend_follower": {
        "label": "BTF",
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
        },
    },
    "ichimoku_cloud_trend": {
        "label": "ICVP",
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
    "cascading_momentum_filter": {
        "label": "CMF",
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
        "label": "RSI_BB",
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

# Lite mode: fewer sessions for local testing
LITE_SYMBOLS: dict[str, list[str]] = {
    "bear_trend_follower": ["BTCUSDT", "ETHUSDT"],
    "ichimoku_cloud_trend": ["BTCUSDT", "ETHUSDT"],
    "cascading_momentum_filter": ["ETHUSDT"],
    "rsi_bb_mean_reversion": ["ETHUSDT"],
}

# Status report interval (seconds)
STATUS_INTERVAL = 300  # 5 minutes
# Telegram trade check interval (seconds)
TRADE_CHECK_INTERVAL = 120  # 2 minutes


# ---------------------------------------------------------------------------
# Engine Builder
# ---------------------------------------------------------------------------


def build_engines(
    factory: SignalGeneratorFactory,
    series_provider: Any,
    config: BacktestConfig,
    store: DataStore,
    lite: bool = False,
) -> list[PaperTradingEngine]:
    """Create PaperTradingEngine instances for all strategy-symbol pairs.

    Args:
        factory: Signal generator factory.
        series_provider: Async callable for OHLCV data.
        config: Backtest/paper trading configuration.
        lite: If True, use reduced symbol set for testing.

    Returns:
        List of PaperTradingEngine instances ready to start.
    """
    engines: list[PaperTradingEngine] = []

    for template_id, cfg in STRATEGY_CONFIG.items():
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
# ---------------------------------------------------------------------------


async def status_reporter(
    engines: list[PaperTradingEngine],
    stop_event: asyncio.Event,
) -> None:
    """Periodically log status of all running engines.

    Args:
        engines: List of running engines.
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

        running = [e for e in engines if e.is_running]
        if not running:
            continue

        total_realized = 0.0
        total_unrealized = 0.0
        total_completed = 0
        total_open = 0
        lines = []
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
    engines: list[PaperTradingEngine],
    telegram: TelegramChannel | None,
    stop_event: asyncio.Event,
) -> None:
    """Monitor engines for position entries AND trade exits, send Telegram alerts.

    Tracks two state changes per engine:
    - Position opened (was flat, now has_open_position) -> ENTRY alert
    - Trade completed (num_trades incremented) -> EXIT alert with PnL

    Args:
        engines: List of running engines.
        telegram: Telegram channel for alerts (or None to skip).
        stop_event: Signal to stop monitoring.
    """
    if telegram is None:
        return

    # Track state per engine: trade count + whether position was open
    last_counts: dict[str, int] = {e.strategy_id: 0 for e in engines}
    had_position: dict[str, bool] = {e.strategy_id: False for e in engines}

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=TRADE_CHECK_INTERVAL
            )
            break
        except asyncio.TimeoutError:
            pass

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
    engines: list[PaperTradingEngine],
    telegram: TelegramChannel | None,
    stop_event: asyncio.Event,
) -> None:
    """Send hourly portfolio summary via Telegram.

    Args:
        engines: List of running engines.
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

        total_completed = 0
        total_open = 0
        total_realized = 0.0
        total_unrealized = 0.0
        active_lines = []

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
    """Main paper trading runner.

    Launches all Tier 1 strategies on approved symbols, monitors for trades,
    and sends Telegram alerts. Runs until SIGINT/SIGTERM.

    Args:
        lite: If True, use reduced symbol set (6 sessions vs 23).
    """
    print("=" * 60)
    print("PARAVANT Paper Trading Runner")
    print(f"Mode: {'LITE (6 sessions)' if lite else 'FULL (23 sessions)'}")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    # Initialize database (creates tables if they don't exist, idempotent)
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

    # Series provider: wraps MarketDataFetcher for the engine
    async def series_provider(symbol: str, lookback_bars: int):
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

    # Build engines
    engines = build_engines(factory, series_provider, config, store, lite=lite)
    print(f"Created {len(engines)} paper trading sessions")

    for engine in engines:
        print(f"  {engine.strategy_id}")

    # Telegram setup (optional)
    telegram: TelegramChannel | None = None
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        telegram = TelegramChannel(bot_token=bot_token, chat_id=chat_id)
        print("Telegram alerts: ENABLED")

        # Send startup alert
        startup_alert = Alert(
            level=AlertLevel.INFO,
            title="Paper Trading Started",
            message=(
                f"Mode: {'LITE' if lite else 'FULL'}\n"
                f"Sessions: {len(engines)}\n"
                f"Capital: $10,000 per session\n"
                f"Strategies: BTF, ICVP, CMF, RSI_BB v1.2"
            ),
        )
        try:
            await telegram.send(startup_alert)
        except Exception:
            pass
    else:
        print("Telegram alerts: DISABLED (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)")

    print("\nStarting engines... (Ctrl+C to stop)")
    print("-" * 60)

    # Graceful shutdown event
    stop_event = asyncio.Event()

    def handle_signal(sig: int, frame: Any) -> None:
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        print(f"\nReceived signal {sig}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Launch all engines as concurrent tasks
    engine_tasks = [asyncio.create_task(engine.start()) for engine in engines]

    # Launch monitoring tasks
    monitor_tasks = [
        asyncio.create_task(status_reporter(engines, stop_event)),
        asyncio.create_task(trade_monitor(engines, telegram, stop_event)),
        asyncio.create_task(hourly_summary(engines, telegram, stop_event)),
    ]

    # Wait for shutdown signal or engine completion
    try:
        # Wait for the stop event
        await stop_event.wait()
    except asyncio.CancelledError:
        pass

    # Graceful shutdown: stop all engines
    print("\nStopping engines...")
    for engine in engines:
        try:
            await engine.stop()
        except Exception as exc:
            logger.error("engine_stop_failed", error=str(exc))

    # Wait for engine tasks to finish (they should exit after stop_event)
    for task in engine_tasks:
        try:
            await asyncio.wait_for(task, timeout=30)
        except (asyncio.TimeoutError, Exception):
            task.cancel()

    # Cancel monitor tasks
    for task in monitor_tasks:
        task.cancel()

    # Print final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    total_trades = 0
    total_pnl = 0.0
    for engine in engines:
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
    elapsed = engines[0].get_status().days_elapsed if engines else 0
    print(f"Elapsed: {elapsed:.1f} days")

    # Send shutdown alert
    if telegram:
        shutdown_alert = Alert(
            level=AlertLevel.INFO,
            title="Paper Trading Stopped",
            message=(
                f"Sessions: {len(engines)}\n"
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
        help="Run with reduced symbol set (6 sessions instead of 23)",
    )
    args = parser.parse_args()

    # Crash-loop protection: max retries with cooldown to prevent
    # Railway restart spam (Telegram alert flood on repeated crashes).
    MAX_CRASH_RESTARTS = 5
    CRASH_COOLDOWN = 60

    for attempt in range(1, MAX_CRASH_RESTARTS + 1):
        try:
            asyncio.run(main(lite=args.lite))
            break  # Clean exit
        except KeyboardInterrupt:
            break
        except Exception as fatal:
            print(
                f"FATAL (attempt {attempt}/{MAX_CRASH_RESTARTS}): {fatal}",
                flush=True,
            )
            if attempt < MAX_CRASH_RESTARTS:
                print(
                    f"Restarting in {CRASH_COOLDOWN}s...",
                    flush=True,
                )
                _time.sleep(CRASH_COOLDOWN)
            else:
                print("Max restarts reached. Exiting.", flush=True)
                sys.exit(1)
