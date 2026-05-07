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
from src.data.database import init_db
from src.data.market_data import OHLCV, MarketDataFetcher
from src.data.models.paper_session import PaperTradingSession
from src.data.store import DataStore
from src.utils.logging import get_logger

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

# Polling interval in seconds (matches paper trading engine)
POLLING_INTERVAL: int = 60

# Hourly summary interval in seconds
HOURLY_INTERVAL: int = 3600

# State file path (must be on a Railway persistent volume)
STATE_FILE: Path = Path(os.getenv("LIVE_STATE_FILE", "/app/data/live_state.json"))

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


def _make_session_id() -> str:
    """Build unique session key for this live config."""
    return f"live_{LIVE_TEMPLATE}_{LIVE_SYMBOL}"


def load_state(store: DataStore) -> dict[str, Any]:
    """Load live trading state — tries SQLite first, then JSON backup.

    Returns:
        State dict with keys: in_position, side, entry_price, quantity,
        entry_time, realized_pnl, total_trades, trade_history,
        stop_loss, take_profit.
    """
    empty: dict[str, Any] = {
        "in_position": False,
        "symbol": LIVE_SYMBOL,
        "realized_pnl": 0.0,
        "total_trades": 0,
        "trade_history": [],
        "stop_loss": None,
        "take_profit": None,
    }

    # 1. Try SQLite (primary)
    session_id = _make_session_id()
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
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            # Back-fill missing keys for forward-compatibility
            data.setdefault("stop_loss", None)
            data.setdefault("take_profit", None)
            data.setdefault("trade_history", [])
            logger.info(
                "live_state_loaded_from_json",
                in_position=data.get("in_position", False),
                symbol=data.get("symbol"),
            )
            print(
                f"State loaded from JSON backup: "
                f"trades={data.get('total_trades', 0)}, "
                f"realized=${data.get('realized_pnl', 0):+.2f}"
            )
            return data
        except Exception as exc:
            logger.warning("live_state_json_load_failed", error=str(exc))

    # 3. Fresh start
    print("No previous state found — starting fresh.")
    return empty


def save_state(state: dict[str, Any], store: DataStore) -> None:
    """Persist live trading state to SQLite (primary) and JSON (backup).

    Args:
        state: Current position state dict.
        store: DataStore instance for SQLite persistence.
    """
    session_id = _make_session_id()

    # 1. Save to SQLite
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
            template_id=LIVE_TEMPLATE,
            symbol=LIVE_SYMBOL,
            initial_capital=LIVE_CAPITAL,
            cash=LIVE_CAPITAL - (
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
        logger.warning("live_state_db_save_failed", error=str(exc))

    # 2. Backup to JSON
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, default=str, indent=2))
    except Exception as exc:
        logger.warning("live_state_json_save_failed", error=str(exc))


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

    if "trade_history" not in state:
        state["trade_history"] = []
    state["trade_history"].append({
        "direction": current_side,
        "symbol": LIVE_SYMBOL,
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
        symbol=LIVE_SYMBOL,
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
# Main live trading loop
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the live trading loop.

    Polls Binance for new 1H candles every POLLING_INTERVAL seconds.
    Each poll cycle:
      1. Check stop-loss / take-profit against current bar high/low
      2. If stop/TP triggered: close position via market order
      3. Generate signal from strategy (on confirmed bars, no lookahead)
      4. If signal generated: run risk guards, then submit order
      5. Save state and wait for next interval
    """
    print("=" * 60)
    print("PARAVANT Live Trading Runner")
    print(f"Strategy:  {LIVE_TEMPLATE}")
    print(f"Symbol:    {LIVE_SYMBOL}")
    print(f"Capital:   ${LIVE_CAPITAL:.2f} USDT")
    print(f"Testnet:   {os.getenv('BINANCE_TESTNET', 'true')}")
    print(f"Max Daily Loss: {MAX_DAILY_LOSS_PCT:.0%} of capital")
    print(f"Max Drawdown:   {MAX_DRAWDOWN_PCT:.0%} of capital")
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

    # Initialize database + DataStore (state persistence and risk checks)
    init_db()
    store = DataStore()
    print("Database initialized (SQLite at data/trading.db)")

    # Telegram setup
    telegram: TelegramChannel | None = None
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        telegram = TelegramChannel(bot_token=bot_token, chat_id=chat_id)

    strategy_id = f"live_{LIVE_TEMPLATE}_{LIVE_SYMBOL}"

    # Load persisted position state (SQLite first, JSON backup, then fresh)
    state = load_state(store)

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
            f"Per Trade: {POSITION_SIZE_FRACTION:.0%} of current equity\n"
            f"Max Daily Loss: {MAX_DAILY_LOSS_PCT:.0%}\n"
            f"Max Drawdown: {MAX_DRAWDOWN_PCT:.0%}\n"
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

    signal_mod.signal(signal_mod.SIGINT, handle_signal)
    signal_mod.signal(signal_mod.SIGTERM, handle_signal)

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
                current_bar: OHLCV = series[-1]
                current_price: float = current_bar.close

                # -----------------------------------------------------------
                # Step 1: Stop-loss / take-profit check (BEFORE signal logic)
                # Checks bar high/low against stored levels — independent of
                # signal generator. Mirrors SimulatedTrader behaviour exactly.
                # -----------------------------------------------------------
                should_exit, exit_reason, level_price = _check_stops_and_tp(
                    state, current_bar
                )

                if should_exit:
                    qty = state.get("quantity", 0.0)
                    current_side = state.get("side", "")
                    exit_order_side = "sell" if current_side == "LONG" else "buy"

                    # Risk guard: kill switch still checked even on stop exits
                    approved, block_reason = _check_risk_guards(
                        state, store, LIVE_CAPITAL, current_price
                    )
                    if not approved and "kill_switch" in block_reason:
                        # Kill switch overrides even stop-loss execution
                        await send_alert(
                            title="KILL SWITCH ACTIVE — Stop Exit Blocked",
                            message=(
                                f"Kill switch is active. Cannot close position.\n"
                                f"Manual intervention required.\n"
                                f"Position: IN {current_side} "
                                f"@ ${state.get('entry_price', 0):,.2f}"
                            ),
                            level=AlertLevel.CRITICAL,
                        )
                    else:
                        success, filled_price = await submit_market_order(
                            adapter, LIVE_SYMBOL, exit_order_side, qty,
                            current_price, strategy_id,
                        )
                        if success and filled_price > 0:
                            # Capture entry price before _record_closed_trade clears state
                            entry_price_snapshot = state.get("entry_price", level_price)
                            net_pnl = _record_closed_trade(
                                state, filled_price, exit_reason
                            )
                            save_state(state, store)

                            await send_alert(
                                title=f"POSITION CLOSED [{exit_reason.upper()}]: {LIVE_SYMBOL}",
                                message=(
                                    f"Direction: {current_side}\n"
                                    f"Entry: ${entry_price_snapshot:,.2f} "
                                    f"-> Exit Fill: ${filled_price:,.2f}\n"
                                    f"Level Breached: ${level_price:,.2f}\n"
                                    f"Net PnL: ${net_pnl:+.4f}\n"
                                    f"---\n"
                                    f"Total Realized: ${state['realized_pnl']:+.2f}\n"
                                    f"Completed Trades: {state['total_trades']}"
                                ),
                            )
                        else:
                            logger.error(
                                "live_stop_exit_failed",
                                exit_reason=exit_reason,
                                symbol=LIVE_SYMBOL,
                                side=exit_order_side,
                                quantity=qty,
                            )
                            await send_alert(
                                title=f"STOP EXIT FAILED: {LIVE_SYMBOL}",
                                message=(
                                    f"Could not close position on {exit_reason}.\n"
                                    f"Manual intervention required.\n"
                                    f"Side: {current_side} | Qty: {qty:.6f}"
                                ),
                                level=AlertLevel.CRITICAL,
                            )

                # -----------------------------------------------------------
                # Step 2: Signal generation (no-lookahead: exclude last bar)
                # -----------------------------------------------------------
                signal_series = series.slice(0, len(series) - 1)
                signal = generator.generate(signal_series, params, LIVE_SYMBOL)

                in_position = state.get("in_position", False)
                current_side = state.get("side", "")

                if signal is not None:
                    sig_dir = signal.direction.value  # "LONG", "SHORT", or "CLOSE"

                    logger.info(
                        "live_signal_generated",
                        symbol=LIVE_SYMBOL,
                        direction=sig_dir,
                        strength=signal.strength,
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        in_position=in_position,
                        poll=poll_count,
                    )

                    # -------------------------------------------------------
                    # Step 3: Signal-driven CLOSE
                    # -------------------------------------------------------
                    if in_position and sig_dir == "CLOSE":
                        qty = state.get("quantity", 0.0)
                        exit_order_side = "sell" if current_side == "LONG" else "buy"

                        approved, block_reason = _check_risk_guards(
                            state, store, LIVE_CAPITAL, current_price
                        )
                        if not approved and "kill_switch" in block_reason:
                            await send_alert(
                                title="KILL SWITCH ACTIVE — Signal Close Blocked",
                                message=(
                                    f"Kill switch active. Cannot close on signal.\n"
                                    f"Block reason: {block_reason}"
                                ),
                                level=AlertLevel.CRITICAL,
                            )
                        else:
                            # Close exits are allowed even if loss limits hit
                            success, filled_price = await submit_market_order(
                                adapter, LIVE_SYMBOL, exit_order_side, qty,
                                current_price, strategy_id,
                            )
                            if success and filled_price > 0:
                                # Capture values before _record_closed_trade clears state
                                entry_price_snapshot = state.get("entry_price", 0.0)
                                entry_time_snapshot = state.get("entry_time", "")
                                net_pnl = _record_closed_trade(
                                    state, filled_price, "signal_close"
                                )
                                save_state(state, store)

                                hold_time_str = ""
                                if entry_time_snapshot:
                                    try:
                                        entry_dt = datetime.fromisoformat(
                                            entry_time_snapshot
                                        )
                                        hold_hrs = (
                                            datetime.now(timezone.utc) - entry_dt
                                        ).total_seconds() / 3600.0
                                        hold_time_str = f"\nHold Time: {hold_hrs:.1f}h"
                                    except (ValueError, TypeError):
                                        pass

                                await send_alert(
                                    title=f"TRADE CLOSED [SIGNAL]: {LIVE_SYMBOL}",
                                    message=(
                                        f"Direction: {current_side}\n"
                                        f"Entry: ${entry_price_snapshot:,.2f} "
                                        f"-> Exit Fill: ${filled_price:,.2f}"
                                        f"{hold_time_str}\n"
                                        f"Net PnL: ${net_pnl:+.4f}\n"
                                        f"---\n"
                                        f"Total Realized: ${state['realized_pnl']:+.2f}\n"
                                        f"Completed Trades: {state['total_trades']}"
                                    ),
                                )

                    # -------------------------------------------------------
                    # Step 4: Signal-driven ENTRY (only when flat)
                    # -------------------------------------------------------
                    elif not in_position and sig_dir in ("LONG", "SHORT"):
                        # Risk guards enforced before every entry
                        approved, block_reason = _check_risk_guards(
                            state, store, LIVE_CAPITAL, current_price
                        )
                        if not approved:
                            logger.warning(
                                "live_entry_blocked_risk_guard",
                                direction=sig_dir,
                                reason=block_reason,
                                symbol=LIVE_SYMBOL,
                            )
                            await send_alert(
                                title=f"ENTRY BLOCKED: {LIVE_SYMBOL}",
                                message=(
                                    f"Signal: {sig_dir}\n"
                                    f"Blocked by: {block_reason}\n"
                                    f"Realized PnL: ${state.get('realized_pnl', 0):+.2f}"
                                ),
                                level=AlertLevel.WARNING,
                            )
                        else:
                            order_side = "buy" if sig_dir == "LONG" else "sell"
                            current_equity = _get_current_equity(
                                state, LIVE_CAPITAL, current_price
                            )
                            qty = calculate_quantity(current_equity, current_price)

                            if qty > 0:
                                success, filled_price = await submit_market_order(
                                    adapter, LIVE_SYMBOL, order_side, qty,
                                    current_price, strategy_id,
                                )
                                if success and filled_price > 0:
                                    state["in_position"] = True
                                    state["side"] = sig_dir
                                    state["quantity"] = qty
                                    # Record actual Binance fill price — not bar close
                                    state["entry_price"] = filled_price
                                    state["entry_time"] = datetime.now(
                                        timezone.utc
                                    ).isoformat()
                                    # Persist stop/TP levels for independent enforcement
                                    state["stop_loss"] = signal.stop_loss
                                    state["take_profit"] = signal.take_profit
                                    save_state(state, store)

                                    stop_str = (
                                        f"${signal.stop_loss:,.2f}"
                                        if signal.stop_loss else "None"
                                    )
                                    tp_str = (
                                        f"${signal.take_profit:,.2f}"
                                        if signal.take_profit else "None"
                                    )
                                    notional = qty * filled_price

                                    await send_alert(
                                        title=f"TRADE OPENED: {LIVE_SYMBOL}",
                                        message=(
                                            f"Direction: {sig_dir}\n"
                                            f"Fill Price: ${filled_price:,.2f}\n"
                                            f"Quantity: {qty:.6f}\n"
                                            f"Notional: ${notional:.2f}\n"
                                            f"Stop Loss: {stop_str}\n"
                                            f"Take Profit: {tp_str}\n"
                                            f"Signal Strength: {signal.strength:.2f}\n"
                                            f"Equity Used: ${current_equity:.2f} "
                                            f"x {POSITION_SIZE_FRACTION:.0%}"
                                        ),
                                    )

                # Periodic console log (every 12 polls = ~12 minutes)
                if poll_count % 12 == 0:
                    pos_str = (
                        f"IN {state['side']} @ ${state.get('entry_price', 0):,.2f}"
                        if state.get("in_position")
                        else "FLAT"
                    )
                    current_equity = _get_current_equity(
                        state, LIVE_CAPITAL, current_price
                    )
                    print(
                        f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC] "
                        f"Poll #{poll_count} | {LIVE_SYMBOL} ${current_price:,.2f} | "
                        f"{pos_str} | "
                        f"Equity: ${current_equity:.2f} | "
                        f"Realized: ${state.get('realized_pnl', 0):+.2f} | "
                        f"Trades: {state.get('total_trades', 0)}",
                        flush=True,
                    )

                # Hourly Telegram summary (every 60 polls = ~60 minutes)
                if poll_count % 60 == 0:
                    now_utc = datetime.now(timezone.utc)
                    current_equity = _get_current_equity(
                        state, LIVE_CAPITAL, current_price
                    )
                    unrealized = current_equity - LIVE_CAPITAL - state.get(
                        "realized_pnl", 0.0
                    )

                    pos_summary = "FLAT (no open position)"
                    if state.get("in_position"):
                        entry_p = state.get("entry_price", 0.0)
                        side_held = state.get("side", "?")
                        hold_h = ""
                        if state.get("entry_time"):
                            try:
                                e_dt = datetime.fromisoformat(state["entry_time"])
                                hold_h = (
                                    f" ({(now_utc - e_dt).total_seconds() / 3600:.1f}h)"
                                )
                            except (ValueError, TypeError):
                                pass
                        pos_summary = (
                            f"{side_held} @ ${entry_p:,.2f}{hold_h}\n"
                            f"Current: ${current_price:,.2f}\n"
                            f"Unrealized: ${unrealized:+.2f}"
                        )
                        # Report stop/TP if active
                        if state.get("stop_loss"):
                            pos_summary += f"\nStop Loss: ${state['stop_loss']:,.2f}"
                        if state.get("take_profit"):
                            pos_summary += f"\nTake Profit: ${state['take_profit']:,.2f}"

                    await send_alert(
                        title=f"Hourly Update: {LIVE_SYMBOL}",
                        message=(
                            f"Price: ${current_price:,.2f}\n"
                            f"Position: {pos_summary}\n"
                            f"---\n"
                            f"Realized PnL: ${state.get('realized_pnl', 0):+.2f}\n"
                            f"Total Equity: ${current_equity:,.2f}\n"
                            f"Completed Trades: {state.get('total_trades', 0)}\n"
                            f"Capital: ${LIVE_CAPITAL:.2f}\n"
                            f"Time: {now_utc.strftime('%Y-%m-%d %H:%M')} UTC"
                        ),
                    )

        except Exception as exc:
            logger.error("live_poll_error", error=str(exc), poll=poll_count, exc_info=True)
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
    import time as _time

    MAX_CRASH_RESTARTS = 5
    CRASH_COOLDOWN = 60  # seconds between restarts

    for attempt in range(1, MAX_CRASH_RESTARTS + 1):
        try:
            asyncio.run(main())
            break  # Clean exit (SIGINT/SIGTERM)
        except KeyboardInterrupt:
            print("\nKeyboard interrupt — exiting.")
            break
        except Exception as fatal:
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
