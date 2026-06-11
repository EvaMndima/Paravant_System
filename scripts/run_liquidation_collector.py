"""Forward Binance liquidation collector runner (DATA process only).

Runs ``research.data.liquidation_collector.LiquidationCollector`` continuously,
persisting Binance USD-M futures forced-liquidation events to the append-only
JSONL store under ``research/data/liquidations/``. It starts the data clock for
the liquidation hypotheses (H-2026-06-004 / H-2026-06-009) that passed Stage-1 and
were blocked only on liquidation-history accessibility.

THIS PROCESS PLACES NO ORDERS. It imports no execution code and does not touch
``LIVE_TRADING_ENABLED`` (which stays OFF). Its only side effect is writing JSONL
fragments.

HOST / GEO. The Binance market-data websocket is rejected from geo-blocked regions
(the DEC-2026-06-04-003 root cause). Run this on an always-on, non-geo-blocked host.
Operator decision (DEC-2026-06-04-021): deploy target is Railway, gated on the
Railway region geo-block being fixed. Until then it can run on any always-on host
in a permitted region.

Usage:
    PYTHONPATH=. .venv/Scripts/python scripts/run_liquidation_collector.py
    PYTHONPATH=. .venv/Scripts/python scripts/run_liquidation_collector.py \
        --flush-interval 30 --flush-max-events 200 --store research/data/liquidations

Stop with Ctrl-C; the buffer is flushed on shutdown.

Decision: DEC-2026-06-04-021 -- forward liquidation data channel + collector.
Decision: DEC-2026-02-08-003 -- Timezone-aware UTC timestamps.
Decision: DEC-2026-02-08-008 -- Structured logging.
"""
from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path

from research.data.liquidation_collector import LiquidationCollector
from research.data.liquidations import LiquidationStore
from src.utils.logging import get_logger, setup_logging


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the collector runner."""
    parser = argparse.ArgumentParser(
        description="Forward Binance liquidation collector (data process only).",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=None,
        help="Parquet store root (default: research/data/liquidations).",
    )
    parser.add_argument(
        "--flush-interval",
        type=float,
        default=30.0,
        help="Seconds of stream silence before a buffer flush (default: 30).",
    )
    parser.add_argument(
        "--flush-max-events",
        type=int,
        default=200,
        help="Flush when the buffer reaches this many events (default: 200).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO).",
    )
    return parser.parse_args()


async def _run(collector: LiquidationCollector) -> None:
    """Run the collector, installing signal handlers for a graceful stop."""
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        collector.stop()

    # SIGINT/SIGTERM request a graceful stop; the run loop flushes on exit.
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # add_signal_handler is unsupported on Windows ProactorEventLoop;
            # KeyboardInterrupt is handled by the caller instead.
            pass

    await collector.run()


def main() -> None:
    """Entry point: build the collector and run until stopped."""
    args = _parse_args()
    setup_logging(level=args.log_level)
    logger = get_logger(__name__)

    store = LiquidationStore(args.store) if args.store is not None else LiquidationStore()
    collector = LiquidationCollector(
        store=store,
        flush_interval_s=args.flush_interval,
        flush_max_events=args.flush_max_events,
    )

    logger.info(
        "liquidation_collector_starting",
        store=str(store.root),
        flush_interval_s=args.flush_interval,
        flush_max_events=args.flush_max_events,
    )
    try:
        asyncio.run(_run(collector))
    except KeyboardInterrupt:
        # Windows path: signal handler unavailable; flush whatever is buffered.
        collector.stop()
        collector.flush()
        logger.info("liquidation_collector_stopped_keyboard", **collector.stats)


if __name__ == "__main__":
    main()
