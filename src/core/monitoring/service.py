"""Monitoring service — daily PnL snapshots and equity tracking.

Responsible for:
- Writing daily PnLRecord at EOD or first write of the day
- Writing intraday EquitySnapshot every cycle
- Checking position staleness (>24 h open without a close signal)
- Providing strategy health summaries for the /health/strategies endpoint

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-26-001 - Monitoring service owns PnL record writes
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.data.models.pnl import EquitySnapshot, PnLRecord
from src.data.models.strategy import StrategyStatus
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.data.models.account import Account
    from src.data.models.position import Position
    from src.data.store import DataStore

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Write equity snapshot every N main-loop cycles (5 s/cycle → 60 s)
EQUITY_SNAPSHOT_INTERVAL_CYCLES: int = 12

# Alert when position has been open this many hours without activity
POSITION_STALE_HOURS: int = 24

# Interval between PnL record upserts (seconds) — used to debounce daily writes
PNL_UPSERT_COOLDOWN_SECONDS: int = 300  # 5 minutes


class MonitoringService:
    """Writes daily PnL records, intraday equity snapshots, and staleness alerts.

    Owns:
    - PnLRecord creation / update for each account every cycle
    - EquitySnapshot writes every EQUITY_SNAPSHOT_INTERVAL_CYCLES cycles
    - Position staleness detection

    Does NOT own:
    - Trade execution decisions
    - Risk checks (owned by RiskController)
    - Alert dispatch (callers use AlertManager directly)

    Usage::

        svc = MonitoringService(data_store)
        # In the orchestrator main loop:
        await svc.run_cycle(cycle_count=cycle_count)
        stale = svc.get_stale_positions()
    """

    def __init__(self, data_store: "DataStore") -> None:
        """Initialise monitoring service.

        Args:
            data_store: DataStore instance for all persistence.
        """
        self._store = data_store
        # Track last PnL upsert per account to avoid redundant DB writes
        self._last_pnl_write: dict[str, datetime] = {}

        logger.info("monitoring_service_initialized")

    # ------------------------------------------------------------------
    # Main entry point — called every orchestrator cycle
    # ------------------------------------------------------------------

    async def run_cycle(self, cycle_count: int) -> None:
        """Run one monitoring cycle.

        Args:
            cycle_count: Current orchestrator loop cycle number (1-indexed).
        """
        import asyncio

        try:
            accounts = await asyncio.to_thread(self._store.get_active_accounts)
        except Exception as exc:
            logger.error("monitoring_get_accounts_error", error=str(exc), exc_info=True)
            return

        for account in accounts:
            try:
                await self._update_pnl_record(account)
            except Exception as exc:
                logger.error(
                    "monitoring_pnl_update_error",
                    account_id=account.id,
                    error=str(exc),
                    exc_info=True,
                )

            if cycle_count % EQUITY_SNAPSHOT_INTERVAL_CYCLES == 0:
                try:
                    await self._write_equity_snapshot(account)
                except Exception as exc:
                    logger.error(
                        "monitoring_equity_snapshot_error",
                        account_id=account.id,
                        error=str(exc),
                        exc_info=True,
                    )

    # ------------------------------------------------------------------
    # PnL record — upsert today's record for an account
    # ------------------------------------------------------------------

    async def _update_pnl_record(self, account: "Account") -> None:
        """Upsert today's PnLRecord for an account.

        Checks the cooldown to avoid hammering the database every 5 seconds.
        The upsert logic:
        1. Try to get today's existing record.
        2. If found → update the mutable aggregate fields.
        3. If not found → create a new record.

        Args:
            account: Account to compute PnL for.
        """
        import asyncio

        now = datetime.now(timezone.utc)
        last_write = self._last_pnl_write.get(account.id)
        if last_write and (now - last_write).total_seconds() < PNL_UPSERT_COOLDOWN_SECONDS:
            return  # Debounced — skip

        today = date.today()
        positions = await asyncio.to_thread(
            self._store.get_open_positions, account.id
        )
        trades_today = await asyncio.to_thread(
            self._store.get_trades_for_account,
            account.id,
            datetime(today.year, today.month, today.day, tzinfo=timezone.utc),
        )

        realized = sum(getattr(t, "realized_pnl", 0.0) for t in trades_today)
        unrealized = sum(getattr(p, "unrealized_pnl", 0.0) for p in positions)
        total_pnl = realized + unrealized

        cash_balance = float(account.balance_usdt)
        position_value = unrealized  # Simplification: use unrealised as position value
        portfolio_value = cash_balance + position_value

        winning = sum(
            1 for t in trades_today if getattr(t, "realized_pnl", 0.0) > 0
        )
        losing = sum(
            1 for t in trades_today if getattr(t, "realized_pnl", 0.0) < 0
        )

        existing = await asyncio.to_thread(
            self._store.get_pnl_for_date, account.id, today
        )

        if existing is not None:
            # Update mutable fields in place
            existing.realized_pnl = realized
            existing.unrealized_pnl = unrealized
            existing.total_pnl = total_pnl
            existing.portfolio_value = portfolio_value
            existing.cash_balance = cash_balance
            existing.position_value = position_value
            existing.trades_count = len(trades_today)
            existing.winning_trades = winning
            existing.losing_trades = losing
            await asyncio.to_thread(self._store.save_pnl_record, existing)
        else:
            record = PnLRecord(
                account_id=account.id,
                record_date=today,
                realized_pnl=realized,
                unrealized_pnl=unrealized,
                total_pnl=total_pnl,
                portfolio_value=portfolio_value,
                cash_balance=cash_balance,
                position_value=position_value,
                trades_count=len(trades_today),
                winning_trades=winning,
                losing_trades=losing,
            )
            await asyncio.to_thread(self._store.save_pnl_record, record)

        self._last_pnl_write[account.id] = now
        logger.debug(
            "pnl_record_written",
            account_id=account.id,
            date=today.isoformat(),
            total_pnl=round(total_pnl, 4),
        )

    # ------------------------------------------------------------------
    # Equity snapshot — intraday data point
    # ------------------------------------------------------------------

    async def _write_equity_snapshot(self, account: "Account") -> None:
        """Write an intraday EquitySnapshot for an account.

        Args:
            account: Account to snapshot.
        """
        import asyncio

        positions = await asyncio.to_thread(
            self._store.get_open_positions, account.id
        )
        positions_value = sum(getattr(p, "unrealized_pnl", 0.0) for p in positions)
        cash = float(account.balance_usdt)
        equity = cash + positions_value

        snapshot = EquitySnapshot(
            account_id=account.id,
            timestamp=datetime.now(timezone.utc),
            equity=equity,
            cash=cash,
            positions_value=positions_value,
        )
        await asyncio.to_thread(self._store.save_equity_snapshot, snapshot)
        logger.debug(
            "equity_snapshot_written",
            account_id=account.id,
            equity=round(equity, 4),
        )

    # ------------------------------------------------------------------
    # Position staleness check
    # ------------------------------------------------------------------

    def check_stale_positions(self, positions: list["Position"]) -> list[dict[str, Any]]:
        """Return metadata for positions open longer than POSITION_STALE_HOURS.

        This is a pure computation helper — it does NOT write to DB or send
        alerts. The orchestrator is responsible for forwarding the result to
        the AlertManager.

        Args:
            positions: List of open Position objects from the position tracker.

        Returns:
            List of dicts with {position_id, symbol, account_id, open_hours}.
            Empty list means no stale positions.
        """
        now = datetime.now(timezone.utc)
        stale_threshold = timedelta(hours=POSITION_STALE_HOURS)
        stale: list[dict[str, Any]] = []

        for pos in positions:
            opened_at = getattr(pos, "opened_at", None)
            if opened_at is None:
                continue
            # Ensure timezone-aware comparison
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=timezone.utc)

            age = now - opened_at
            if age >= stale_threshold:
                stale.append(
                    {
                        "position_id": pos.id,
                        "symbol": getattr(pos, "symbol", "unknown"),
                        "account_id": getattr(pos, "account_id", "unknown"),
                        "strategy_id": getattr(pos, "strategy_id", None),
                        "open_hours": round(age.total_seconds() / 3600, 1),
                    }
                )

        if stale:
            logger.warning(
                "stale_positions_detected",
                count=len(stale),
                positions=[s["position_id"] for s in stale],
            )

        return stale

    # ------------------------------------------------------------------
    # Strategy health summary (used by /health/strategies endpoint)
    # ------------------------------------------------------------------

    def get_strategy_health_summary(self) -> list[dict[str, Any]]:
        """Return a health summary for all non-retired strategies.

        Queries all strategies, computes a simple health signal based on
        lifecycle status, and returns the result.

        Returns:
            List of strategy health records, each dict has:
            {strategy_id, name, status, health, last_lifecycle_event,
             backtest_sharpe, paper_win_rate}
        """
        try:
            all_strategies = self._store.get_all_strategies()
        except Exception as exc:
            logger.error("strategy_health_query_error", error=str(exc), exc_info=True)
            return []

        _HEALTHY_STATUSES = {
            StrategyStatus.LIVE,
            StrategyStatus.LIVE_PAPER,
            StrategyStatus.SIMULATED_PAPER,
        }
        _DEGRADED_STATUSES = {
            StrategyStatus.UNDERPERFORMING,
            StrategyStatus.OPTIMIZATION,
            StrategyStatus.PAUSED,
        }

        summaries: list[dict[str, Any]] = []
        for strategy in all_strategies:
            if strategy.status == StrategyStatus.RETIRED:
                continue  # Omit retired strategies from health feed

            if strategy.status in _HEALTHY_STATUSES:
                health = "healthy"
            elif strategy.status in _DEGRADED_STATUSES:
                health = "degraded"
            else:
                health = "unknown"

            lifecycle = strategy.lifecycle or []
            last_event = lifecycle[-1] if lifecycle else None

            backtest_sharpe = None
            paper_win_rate = None
            if strategy.backtest_results:
                backtest_sharpe = strategy.backtest_results.get("sharpe_ratio")
            if strategy.paper_results:
                paper_win_rate = strategy.paper_results.get("win_rate_pct")

            summaries.append(
                {
                    "strategy_id": strategy.id,
                    "name": strategy.name,
                    "status": strategy.status.value,
                    "health": health,
                    "last_lifecycle_event": last_event,
                    "backtest_sharpe": backtest_sharpe,
                    "paper_win_rate": paper_win_rate,
                    "symbols": strategy.symbols,
                }
            )

        return summaries
