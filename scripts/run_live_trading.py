"""Live trading runner — real Binance orders, single session.

Runs ONE strategy-symbol pair with REAL capital via Binance Spot API.
Designed as the graduation step after paper trading validation.

Default configuration:
    Strategy: bear_trend_follower (BTF) — best performer in 60-day backtest
    Symbol:   BTCUSDT
    Capital:  Configurable via LIVE_CAPITAL_USDT env var (default $20)

Position sizing:
    Uses 25% of available capital per trade ($5 on a $20 account), keeping
    max loss per trade around $0.50-$1.00 with ATR-based stops.
    Clears Binance minimum notional ($5 for BTCUSDT Spot).

Safety:
    - Reads BINANCE_TESTNET env var: set "true" to test on testnet first
    - Sends Telegram alerts on every entry, exit, and error
    - All orders are market orders (guaranteed fills, no stuck limit orders)
    - Position state saved to /app/data/live_state.json every poll cycle
      so restarts don't cause ghost positions

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
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.brokers.binance.client import BinanceClient
from src.brokers.binance.execution import BinanceExecutionAdapter
from src.brokers.binance.rate_limiter import RateLimiter
from src.core.alerting.channels.telegram import TelegramChannel
from src.core.alerting.manager import Alert, AlertLevel
from src.core.strategy.backtest.types import BacktestConfig
from src.core.strategy.factory import SignalGeneratorFactory
from src.core.risk.types import OrderRequest
from src.data.market_data import MarketDataFetcher
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration (all overridable via environment variables)
# ---------------------------------------------------------------------------

LIVE_CAPITAL = float(os.getenv("LIVE_CAPITAL_USDT", "20.0"))
LIVE_SYMBOL = os.getenv("LIVE_SYMBOL", "BTCUSDT")
LIVE_TEMPLATE = os.getenv("LIVE_TEMPLATE", "bear_trend_follower")

# Fraction of capital to deploy per trade — 25% keeps max loss ~$0.50-$1.00
# with ATR-based stops on a $20 account.  Remaining 75% is buffer.
POSITION_SIZE_FRACTION = 0.25

# Binance minimum notional value — BTCUSDT spot minimum is $5
BINANCE_MIN_NOTIONAL = 5.0

# Polling interval in seconds (matches paper trading engine)
POLLING_INTERVAL = 60

# Hourly summary interval in seconds
HOURLY_INTERVAL = 3600

# State file path (must be on a Railway persistent volume)
STATE_FILE = Path(os.getenv("LIVE_STATE_FILE", "/app/data/live_state.json"))

# BTF strategy parameters (matching paper trading config)
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
}

# Minimum bars each strategy needs (BTF needs 810 for 4H EMA200 warmup)
MIN_BARS_LOOKUP: dict[str, int] = {
    "bear_trend_follower": 860,
    "ichimoku_cloud_trend": 220,
    "cascading_momentum_filter": 400,
    "rsi_bb_mean_reversion": 260,
}

STRATEGY_PARAMS_LOOKUP: dict[str, dict[str, Any]] = {
    "bear_trend_follower": BTF_PARAMS,
}


# ---------------------------------------------------------------------------
# Position state — persisted to JSON so restarts don't create ghost positions
# ---------------------------------------------------------------------------


def load_state() -> dict[str, Any]:
    """Load live trading position state from disk.

    Returns:
        State dict with keys: in_position, side, entry_price, quantity,
        entry_time. Returns empty (no position) dict if file does not exist.
    """
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            logger.info(
                "live_state_loaded",
                in_position=data.get("in_position", False),
                symbol=data.get("symbol"),
                side=data.get("side"),
            )
            return data
        except Exception as exc:
            logger.warning("live_state_load_failed", error=str(exc))
    return {"in_position": False, "symbol": LIVE_SYMBOL, "realized_pnl": 0.0,
            "total_trades": 0}


def save_state(state: dict[str, Any]) -> None:
    """Save live trading position state to disk.

    Args:
        state: Current position state dict.
    """
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, default=str, indent=2))
    except Exception as exc:
        logger.warning("live_state_save_failed", error=str(exc))


# ---------------------------------------------------------------------------
# Order helpers
# ---------------------------------------------------------------------------


def calculate_quantity(capital: float, price: float) -> float:
    """Calculate order quantity from capital and current price.

    Uses POSITION_SIZE_FRACTION of capital. Rounds down to 6 decimal
    places to stay within Binance precision requirements.

    Args:
        capital: Total capital in USDT.
        price: Current asset price in USDT.

    Returns:
        Quantity in base asset, or 0.0 if notional would be below minimum.
    """
    usdt_to_spend = capital * POSITION_SIZE_FRACTION
    if usdt_to_spend < BINANCE_MIN_NOTIONAL:
        logger.warning(
            "position_below_minimum_notional",
            usdt_to_spend=usdt_to_spend,
            minimum=BINANCE_MIN_NOTIONAL,
        )
        return 0.0
    quantity = usdt_to_spend / price
    # Round down to 6 decimal places (safe for BTC/ETH precision)
    return math.floor(quantity * 1_000_000) / 1_000_000


async def submit_market_order(
    adapter: BinanceExecutionAdapter,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    strategy_id: str,
) -> bool:
    """Submit a market order and return True on success.

    Args:
        adapter: Binance execution adapter.
        symbol: Trading pair.
        side: "buy" or "sell".
        quantity: Quantity in base asset.
        price: Current price (for OrderRequest validation only).
        strategy_id: Strategy identifier for logging.

    Returns:
        True if order was submitted and filled successfully.
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
        logger.info(
            "live_order_submitted",
            symbol=symbol,
            side=side,
            quantity=quantity,
            status=result.status,
            filled_price=result.filled_price,
            commission=result.commission,
            external_id=result.external_id,
        )
        return result.status == "filled"
    except Exception as exc:
        logger.error(
            "live_order_failed",
            symbol=symbol,
            side=side,
            quantity=quantity,
            error=str(exc),
        )
        return False


# ---------------------------------------------------------------------------
# Main live trading loop
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the live trading loop.

    Polls Binance for new 1H candles every 60 seconds, generates signals
    using the configured strategy, and submits real market orders.
    """
    print("=" * 60)
    print("PARAVANT Live Trading Runner")
    print(f"Strategy:  {LIVE_TEMPLATE}")
    print(f"Symbol:    {LIVE_SYMBOL}")
    print(f"Capital:   ${LIVE_CAPITAL:.2f} USDT")
    print(f"Testnet:   {os.getenv('BINANCE_TESTNET', 'true')}")
    print(f"Started:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Print server IP (useful for Binance IP whitelisting)
    try:
        import urllib.request
        ext_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
        print(f"Server IP: {ext_ip}  <-- add this to Binance API IP whitelist")
    except Exception:
        print("Server IP: could not determine")
    print("=" * 60)

    # Validate capital is enough to clear minimum notional
    usdt_per_trade = LIVE_CAPITAL * POSITION_SIZE_FRACTION
    if usdt_per_trade < BINANCE_MIN_NOTIONAL:
        print(
            f"ERROR: Capital ${LIVE_CAPITAL:.2f} x {POSITION_SIZE_FRACTION:.0%} = "
            f"${usdt_per_trade:.2f} is below Binance minimum notional "
            f"(${BINANCE_MIN_NOTIONAL:.2f}). "
            f"Increase LIVE_CAPITAL_USDT to at least "
            f"${math.ceil(BINANCE_MIN_NOTIONAL / POSITION_SIZE_FRACTION):.0f}."
        )
        sys.exit(1)

    # Initialize Binance client and adapter
    api_key = os.getenv("BINANCE_API_KEY", "")
    secret_key = os.getenv("BINANCE_SECRET_KEY", "")
    testnet = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

    if not api_key or not secret_key:
        print("ERROR: BINANCE_API_KEY and BINANCE_SECRET_KEY must be set.")
        sys.exit(1)

    rate_limiter = RateLimiter()
    client = BinanceClient(
        api_key=api_key,
        secret_key=secret_key,
        testnet=testnet,
        rate_limiter=rate_limiter,
    )
    adapter = BinanceExecutionAdapter(client=client, rate_limiter=rate_limiter)

    # Initialize strategy signal generator
    factory = SignalGeneratorFactory()
    generator = factory.get_generator(LIVE_TEMPLATE)
    params = STRATEGY_PARAMS_LOOKUP.get(LIVE_TEMPLATE, {})
    lookback_bars = MIN_BARS_LOOKUP.get(LIVE_TEMPLATE, 500)

    # Initialize market data fetcher
    fetcher = MarketDataFetcher()

    # Telegram setup
    telegram: TelegramChannel | None = None
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        telegram = TelegramChannel(bot_token=bot_token, chat_id=chat_id)

    strategy_id = f"live_{LIVE_TEMPLATE}_{LIVE_SYMBOL}"

    # Load persisted position state
    state = load_state()

    async def send_alert(title: str, message: str, level: AlertLevel = AlertLevel.INFO) -> None:
        """Send a Telegram alert if configured."""
        if telegram is None:
            return
        alert = Alert(level=level, title=title, message=message, metadata={})
        try:
            await telegram.send(alert)
        except Exception as exc:
            logger.warning("live_telegram_failed", error=str(exc))

    # Startup alert
    mode_label = "TESTNET" if testnet else "REAL MONEY"
    pos_detail = "FLAT (no position)"
    if state.get("in_position"):
        pos_detail = (
            f"IN {state.get('side', '?')} @ ${state.get('entry_price', 0):,.2f} "
            f"(qty: {state.get('quantity', 0):.6f})"
        )
    await send_alert(
        title=f"Live Trading Started [{mode_label}]",
        message=(
            f"Strategy: {LIVE_TEMPLATE}\n"
            f"Symbol: {LIVE_SYMBOL}\n"
            f"Capital: ${LIVE_CAPITAL:.2f}\n"
            f"Per Trade: ${LIVE_CAPITAL * POSITION_SIZE_FRACTION:.2f} "
            f"({POSITION_SIZE_FRACTION:.0%})\n"
            f"Mode: {mode_label}\n"
            f"Position: {pos_detail}\n"
            f"Realized PnL: ${state.get('realized_pnl', 0):+.2f}\n"
            f"Completed Trades: {state.get('total_trades', 0)}"
        ),
    )

    # Graceful shutdown
    stop_event = asyncio.Event()

    def handle_signal(sig: int, frame: Any) -> None:
        """Handle SIGINT/SIGTERM."""
        print(f"\nReceived signal {sig}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"\nPolling every {POLLING_INTERVAL}s. Press Ctrl+C to stop.\n")

    poll_count = 0

    while not stop_event.is_set():
        poll_count += 1

        try:
            # Fetch latest candles
            series = await fetcher.fetch_ohlcv(
                symbol=LIVE_SYMBOL,
                timeframe="1h",
                limit=min(lookback_bars, 1000),
            )

            if series is None or len(series) < generator.min_bars_required + 2:
                logger.warning(
                    "live_insufficient_data",
                    available=len(series) if series else 0,
                    required=generator.min_bars_required + 2,
                )
            else:
                # Use all bars except the last (closed candles only — no lookahead)
                signal_series = series.slice(0, len(series) - 1)
                current_bar = series[-1]
                current_price = current_bar.close

                signal = generator.generate(signal_series, params, LIVE_SYMBOL)

                in_position = state.get("in_position", False)
                current_side = state.get("side", "")

                if signal is not None:
                    sig_dir = signal.direction.value  # "LONG", "SHORT", or "CLOSE"

                    logger.info(
                        "live_signal_generated",
                        symbol=LIVE_SYMBOL,
                        direction=sig_dir,
                        in_position=in_position,
                        poll=poll_count,
                    )

                    # CLOSE existing position
                    if in_position and sig_dir == "CLOSE":
                        qty = state.get("quantity", 0.0)
                        entry_price = state.get("entry_price", current_price)
                        exit_side = "sell" if current_side == "LONG" else "buy"

                        success = await submit_market_order(
                            adapter, LIVE_SYMBOL, exit_side, qty,
                            current_price, strategy_id
                        )
                        if success:
                            pnl = (current_price - entry_price) * qty
                            if current_side == "SHORT":
                                pnl = (entry_price - current_price) * qty
                            state["realized_pnl"] = state.get("realized_pnl", 0.0) + pnl
                            state["total_trades"] = state.get("total_trades", 0) + 1
                            state["in_position"] = False
                            state["side"] = ""
                            state["quantity"] = 0.0
                            save_state(state)

                            hold_time = ""
                            if state.get("entry_time"):
                                try:
                                    entry_dt = datetime.fromisoformat(state["entry_time"])
                                    hold_hrs = (datetime.now(timezone.utc) - entry_dt).total_seconds() / 3600
                                    hold_time = f"\nHold Time: {hold_hrs:.1f} hours"
                                except (ValueError, TypeError):
                                    pass
                            ret_pct = (pnl / (entry_price * qty)) * 100 if entry_price * qty > 0 else 0

                            await send_alert(
                                title=f"TRADE CLOSED: {LIVE_SYMBOL}",
                                message=(
                                    f"Direction: {current_side}\n"
                                    f"Entry: ${entry_price:,.2f} -> Exit: ${current_price:,.2f}\n"
                                    f"PnL: ${pnl:+.2f} ({ret_pct:+.1f}%){hold_time}\n"
                                    f"---\n"
                                    f"Total Realized: ${state['realized_pnl']:+.2f}\n"
                                    f"Completed Trades: {state['total_trades']}"
                                ),
                            )

                    # ENTER new position (only if not already in one)
                    elif not in_position and sig_dir in ("LONG", "SHORT"):
                        order_side = "buy" if sig_dir == "LONG" else "sell"
                        qty = calculate_quantity(LIVE_CAPITAL, current_price)

                        if qty > 0:
                            success = await submit_market_order(
                                adapter, LIVE_SYMBOL, order_side, qty,
                                current_price, strategy_id
                            )
                            if success:
                                state["in_position"] = True
                                state["side"] = sig_dir
                                state["quantity"] = qty
                                state["entry_price"] = current_price
                                state["entry_time"] = datetime.now(timezone.utc).isoformat()
                                save_state(state)

                                await send_alert(
                                    title=f"TRADE OPENED: {LIVE_SYMBOL}",
                                    message=(
                                        f"Direction: {sig_dir}\n"
                                        f"Entry Price: ${current_price:,.2f}\n"
                                        f"Quantity: {qty:.6f}\n"
                                        f"Notional: ${qty * current_price:.2f}\n"
                                        f"Risk (~ATR stop): ~${qty * current_price * 0.15:.2f} max\n"
                                        f"Signal Strength: {signal.strength:.2f}"
                                    ),
                                )

                # Periodic console log (every 12 polls = ~12 minutes)
                if poll_count % 12 == 0:
                    pos_str = (
                        f"IN {state['side']} @ ${state.get('entry_price', 0):,.2f}"
                        if state.get("in_position")
                        else "FLAT"
                    )
                    print(
                        f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] "
                        f"Poll #{poll_count} | {LIVE_SYMBOL} ${current_price:,.2f} | "
                        f"{pos_str} | "
                        f"Realized: ${state.get('realized_pnl', 0):+.2f} | "
                        f"Trades: {state.get('total_trades', 0)}",
                        flush=True,
                    )

                # Hourly Telegram summary (every 60 polls = ~60 minutes)
                if poll_count % 60 == 0:
                    now_utc = datetime.now(timezone.utc)
                    pos_summary = "FLAT (no open position)"
                    unrealized = 0.0
                    if state.get("in_position"):
                        entry_p = state.get("entry_price", 0)
                        qty_held = state.get("quantity", 0)
                        side_held = state.get("side", "?")
                        if side_held == "LONG":
                            unrealized = (current_price - entry_p) * qty_held
                        else:
                            unrealized = (entry_p - current_price) * qty_held
                        hold_h = ""
                        if state.get("entry_time"):
                            try:
                                e_dt = datetime.fromisoformat(state["entry_time"])
                                hold_h = f" ({(now_utc - e_dt).total_seconds() / 3600:.1f}h)"
                            except (ValueError, TypeError):
                                pass
                        pos_summary = (
                            f"{side_held} @ ${entry_p:,.2f}{hold_h}\n"
                            f"Current: ${current_price:,.2f}\n"
                            f"Unrealized: ${unrealized:+.2f}"
                        )

                    total_pnl = state.get("realized_pnl", 0) + unrealized

                    await send_alert(
                        title=f"Hourly Update: {LIVE_SYMBOL}",
                        message=(
                            f"Price: ${current_price:,.2f}\n"
                            f"Position: {pos_summary}\n"
                            f"---\n"
                            f"Realized PnL: ${state.get('realized_pnl', 0):+.2f}\n"
                            f"Total PnL: ${total_pnl:+.2f}\n"
                            f"Completed Trades: {state.get('total_trades', 0)}\n"
                            f"Capital: ${LIVE_CAPITAL:.2f}\n"
                            f"Time: {now_utc.strftime('%Y-%m-%d %H:%M')} UTC"
                        ),
                    )

        except Exception as exc:
            logger.error("live_poll_error", error=str(exc), poll=poll_count)
            await send_alert(
                title="Live Trading Error",
                message=f"Poll #{poll_count} failed: {exc}",
                level=AlertLevel.ERROR,
            )

        # Wait for next poll or stop signal
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLLING_INTERVAL)
            break
        except asyncio.TimeoutError:
            continue

    # Shutdown summary
    pos_at_shutdown = "FLAT"
    if state.get("in_position"):
        pos_at_shutdown = (
            f"IN {state.get('side', '?')} @ ${state.get('entry_price', 0):,.2f} "
            f"(qty: {state.get('quantity', 0):.6f})"
        )
    summary = (
        f"Position: {pos_at_shutdown}\n"
        f"Completed Trades: {state.get('total_trades', 0)}\n"
        f"Realized PnL: ${state.get('realized_pnl', 0):+.2f}\n"
        f"Capital: ${LIVE_CAPITAL:.2f}"
    )
    print(f"\n{summary}")
    await send_alert(title="Live Trading Stopped", message=summary)

    if telegram:
        await telegram.close()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
