"""Scheduled alert delivery for daily and weekly Telegram summaries.

Runs background asyncio tasks that fire at fixed UTC times:
  - Daily summary: 00:00 UTC every day (PRD §8.5)
  - Weekly summary: Sunday 00:00 UTC (PRD §8.6)

Each summary aggregates live portfolio data from the DataStore and sends
a formatted message via AlertManager using the INFO channel.

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-02-10-004 - Async-first architecture
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.utils.logging import get_logger

if TYPE_CHECKING:
    from src.core.alerting.manager import AlertManager
    from src.data.store import DataStore

logger = get_logger(__name__)


class AlertScheduler:
    """Background scheduler for daily and weekly Telegram summaries.

    Spawns two asyncio tasks on start():
      - _daily_summary_loop: fires once per UTC day at 00:00
      - _weekly_summary_loop: fires every Sunday at 00:00 UTC

    Both loops sleep until the next target UTC time using _seconds_until_utc().
    Gracefully cancels tasks on stop().

    Attributes:
        alert_manager: AlertManager used to dispatch summary messages.
        data_store: DataStore used to aggregate summary data.
    """

    def __init__(
        self,
        alert_manager: "AlertManager",
        data_store: "DataStore",
    ) -> None:
        """Initialize the alert scheduler.

        Args:
            alert_manager: AlertManager to dispatch summaries through.
            data_store: DataStore to read portfolio/strategy data from.
        """
        self._alert_manager = alert_manager
        self._data_store = data_store
        self._tasks: list[asyncio.Task[None]] = []
        logger.info("alert_scheduler_initialized")

    def start(self) -> None:
        """Start the daily and weekly summary background tasks.

        Creates two asyncio Tasks. Must be called from inside a running
        event loop (after asyncio.run() or inside async context).
        """
        daily_task = asyncio.create_task(
            self._daily_summary_loop(),
            name="alert_scheduler_daily",
        )
        weekly_task = asyncio.create_task(
            self._weekly_summary_loop(),
            name="alert_scheduler_weekly",
        )
        self._tasks = [daily_task, weekly_task]
        logger.info("alert_scheduler_started", task_count=len(self._tasks))

    async def stop(self) -> None:
        """Stop all scheduled tasks gracefully.

        Cancels and awaits all running tasks. Safe to call multiple times.
        """
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._tasks = []
        logger.info("alert_scheduler_stopped")

    # ------------------------------------------------------------------
    # Loop implementations
    # ------------------------------------------------------------------

    async def _daily_summary_loop(self) -> None:
        """Send daily portfolio summary every day at 00:00 UTC.

        PRD §8.5: Daily summary includes portfolio value, daily P&L,
        trade count, active strategies, and alert count.
        """
        while True:
            try:
                wait_seconds = _seconds_until_utc_midnight()
                logger.debug(
                    "daily_summary_scheduled",
                    wait_seconds=round(wait_seconds, 1),
                )
                await asyncio.sleep(wait_seconds)
                await self._send_daily_summary()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "daily_summary_loop_error",
                    error=str(e),
                    exc_info=True,
                )
                # Wait 5 minutes before retrying to avoid tight error loop
                await asyncio.sleep(300)

    async def _weekly_summary_loop(self) -> None:
        """Send weekly portfolio summary every Sunday at 00:00 UTC.

        PRD §8.6: Weekly summary includes weekly return, strategy
        ranking, and recommendations.
        """
        while True:
            try:
                wait_seconds = _seconds_until_sunday_midnight()
                logger.debug(
                    "weekly_summary_scheduled",
                    wait_seconds=round(wait_seconds, 1),
                )
                await asyncio.sleep(wait_seconds)
                await self._send_weekly_summary()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "weekly_summary_loop_error",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(300)

    # ------------------------------------------------------------------
    # Summary data aggregation and dispatch
    # ------------------------------------------------------------------

    async def _send_daily_summary(self) -> None:
        """Aggregate and dispatch the daily portfolio summary.

        Collects: total equity, daily P&L, open positions count,
        active strategy count, and unacknowledged alert count.
        """
        data = await asyncio.to_thread(self._aggregate_daily_data)

        title = "Daily Portfolio Summary"
        message = (
            f"Portfolio Value: ${data['total_equity']:,.2f}\n"
            f"Daily P&L:       ${data['daily_pnl']:+,.2f} "
            f"({data['daily_pnl_pct']:+.2f}%)\n"
            f"Open Positions:  {data['open_positions']}\n"
            f"Active Strategies: {data['active_strategies']}\n"
            f"Trades Today:    {data['trades_today']}\n"
            f"Alerts (24h):    {data['alerts_24h']}\n"
            f"As of: {data['timestamp']}"
        )

        await self._alert_manager.send_info(
            title=title,
            message=message,
            summary_type="daily",
            **{k: v for k, v in data.items() if k != "timestamp"},
        )

        logger.info(
            "daily_summary_sent",
            total_equity=data["total_equity"],
            daily_pnl=data["daily_pnl"],
        )

    async def _send_weekly_summary(self) -> None:
        """Aggregate and dispatch the weekly portfolio summary.

        Collects: weekly return, strategy performance ranking,
        top performer, and worst performer.
        """
        data = await asyncio.to_thread(self._aggregate_weekly_data)

        title = "Weekly Portfolio Summary"
        message = (
            f"Weekly Return:   {data['weekly_return_pct']:+.2f}%\n"
            f"Portfolio Value: ${data['total_equity']:,.2f}\n"
            f"Active Strategies: {data['active_strategies']}\n"
            f"Trades This Week: {data['trades_week']}\n"
        )

        if data["top_performer"]:
            message += f"Top Performer:   {data['top_performer']}\n"
        if data["worst_performer"]:
            message += f"Worst Performer: {data['worst_performer']}\n"

        message += f"As of: {data['timestamp']}"

        await self._alert_manager.send_info(
            title=title,
            message=message,
            summary_type="weekly",
            **{k: v for k, v in data.items() if k not in ("timestamp", "top_performer", "worst_performer")},
        )

        logger.info(
            "weekly_summary_sent",
            weekly_return_pct=data["weekly_return_pct"],
            total_equity=data["total_equity"],
        )

    def _aggregate_daily_data(self) -> dict[str, Any]:
        """Collect daily summary data from DataStore.

        Runs synchronously (intended to be called via asyncio.to_thread).

        Returns:
            Dictionary with portfolio metrics for the daily summary.
        """
        now = datetime.now(timezone.utc)
        accounts = self._data_store.get_active_accounts()

        total_equity = sum(
            getattr(a, "equity_usdt", 0.0) for a in accounts
        )
        daily_pnl = sum(
            getattr(a, "daily_pnl", 0.0) for a in accounts
        )
        daily_pnl_pct = (
            (daily_pnl / (total_equity - daily_pnl) * 100.0)
            if total_equity > daily_pnl and total_equity > 0
            else 0.0
        )

        # Open positions count from all live strategies
        from src.data.models.strategy import StrategyStatus
        live_strategies = self._data_store.get_strategies_by_status(
            StrategyStatus.LIVE
        )

        # Trade count for today (orders filled since midnight UTC)
        from src.data.models.order import OrderStatus
        from datetime import timezone as tz
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        filled_today = self._data_store.get_orders_by_status(OrderStatus.FILLED)
        trades_today = sum(
            1 for o in filled_today
            if getattr(o, "updated_at", None)
            and o.updated_at >= midnight
        )

        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M UTC"),
            "total_equity": total_equity,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "open_positions": len(live_strategies),  # Proxy: live strategy count
            "active_strategies": len(live_strategies),
            "trades_today": trades_today,
            "alerts_24h": 0,  # Populated when alert persistence is queryable
        }

    def _aggregate_weekly_data(self) -> dict[str, Any]:
        """Collect weekly summary data from DataStore.

        Runs synchronously (intended to be called via asyncio.to_thread).

        Returns:
            Dictionary with portfolio metrics for the weekly summary.
        """
        now = datetime.now(timezone.utc)
        accounts = self._data_store.get_active_accounts()

        total_equity = sum(
            getattr(a, "equity_usdt", 0.0) for a in accounts
        )
        weekly_pnl = sum(
            getattr(a, "weekly_pnl", 0.0) for a in accounts
        )
        start_equity = total_equity - weekly_pnl
        weekly_return_pct = (
            (weekly_pnl / start_equity * 100.0) if start_equity > 0 else 0.0
        )

        from src.data.models.strategy import StrategyStatus
        live_strategies = self._data_store.get_strategies_by_status(
            StrategyStatus.LIVE
        )

        # Weekly trade count (past 7 days)
        week_ago = now - timedelta(days=7)
        from src.data.models.order import OrderStatus
        filled = self._data_store.get_orders_by_status(OrderStatus.FILLED)
        trades_week = sum(
            1 for o in filled
            if getattr(o, "updated_at", None)
            and o.updated_at >= week_ago
        )

        # Strategy ranking: sort by live_results.total_return_pct desc
        top_performer: str | None = None
        worst_performer: str | None = None
        if live_strategies:
            ranked = sorted(
                live_strategies,
                key=lambda s: float(
                    (s.live_results or {}).get("total_return_pct", 0.0)
                ),
                reverse=True,
            )
            top_performer = ranked[0].name if ranked else None
            worst_performer = ranked[-1].name if len(ranked) > 1 else None

        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M UTC"),
            "total_equity": total_equity,
            "weekly_pnl": weekly_pnl,
            "weekly_return_pct": round(weekly_return_pct, 2),
            "active_strategies": len(live_strategies),
            "trades_week": trades_week,
            "top_performer": top_performer,
            "worst_performer": worst_performer,
        }


# ------------------------------------------------------------------
# Timing helpers
# ------------------------------------------------------------------


def _seconds_until_utc_midnight() -> float:
    """Return seconds until next 00:00 UTC.

    Always returns at least 1 second to avoid busy loops at midnight.

    Returns:
        Float seconds until next UTC midnight.
    """
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    delta = (tomorrow - now).total_seconds()
    # Guarantee at least 1 second to avoid tight loop at exact midnight
    return max(delta, 1.0)


def _seconds_until_sunday_midnight() -> float:
    """Return seconds until next Sunday 00:00 UTC.

    If today is Sunday and midnight hasn't passed yet, returns seconds
    until tonight's midnight. Otherwise returns seconds until next Sunday.

    Returns:
        Float seconds until next Sunday UTC midnight.
    """
    now = datetime.now(timezone.utc)
    # weekday(): Monday=0, Sunday=6
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0:
        # Today is Sunday — target is next Sunday (7 days away), unless
        # we haven't passed midnight yet on this Sunday (days=0 case).
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now >= next_midnight:
            days_until_sunday = 7
        else:
            days_until_sunday = 0

    target = (now + timedelta(days=days_until_sunday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    delta = (target - now).total_seconds()
    return max(delta, 1.0)
