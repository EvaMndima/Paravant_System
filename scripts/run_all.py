"""Run paper trading and live trading in parallel from a single Railway service.

Launches both scripts as separate subprocesses so each has its own
asyncio event loop, signal handlers, and crash-restart harness.
If either process crashes, it is restarted after CRASH_COOLDOWN seconds
(up to MAX_RESTARTS times) before the wrapper itself exits and Railway
triggers a service-level restart.

Railway start command:
    python -m scripts.run_all

Environment variables consumed by each child process are passed through
automatically from the Railway service environment.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

MAX_RESTARTS = 5
CRASH_COOLDOWN = 60

# Paper trading always runs. Live trading is fail-closed: it ONLY starts
# when LIVE_TRADING_ENABLED is set to a truthy value ("true"/"1"/"yes").
# Decision: DEC-2026-05-27-001 -- live trading kill switch defaults OFF.
def _live_enabled() -> bool:
    """Return True if live trading is explicitly enabled via env var."""
    raw = os.environ.get("LIVE_TRADING_ENABLED", "").strip().lower()
    return raw in {"true", "1", "yes", "on"}


SCRIPTS_PAPER = ["scripts.run_paper_trading"]
SCRIPTS_LIVE = ["scripts.run_live_trading"]
SCRIPTS = SCRIPTS_PAPER + (SCRIPTS_LIVE if _live_enabled() else [])

# LIVE_CAPITAL_USDT must be set or live trading defaults to $20.
# BINANCE_API_KEY / BINANCE_SECRET_KEY must be present for live trading.
# Paper trading only needs keys for market data (read permission is enough).


def _spawn(module: str) -> subprocess.Popen[bytes]:
    """Start a child process for the given module."""
    return subprocess.Popen(
        [sys.executable, "-m", module],
        env=os.environ.copy(),
    )


def main() -> None:
    """Start both scripts and supervise them until shutdown."""
    print("=" * 60)
    print("PARAVANT Combined Runner")
    for s in SCRIPTS:
        print(f"  Active: {s}")
    if not _live_enabled():
        print("  Live trading DISABLED (set LIVE_TRADING_ENABLED=true to enable)")
    print("=" * 60, flush=True)

    # Track each script with its restart counter.
    procs: dict[str, subprocess.Popen[bytes]] = {}
    restarts: dict[str, int] = {}
    for s in SCRIPTS:
        procs[s] = _spawn(s)
        restarts[s] = 0

    shutting_down = False

    def _stop(sig: int, _frame: object) -> None:
        """Forward SIGTERM/SIGINT to both children and exit cleanly."""
        nonlocal shutting_down
        shutting_down = True
        print(f"\nWrapper received signal {sig} -- stopping children.", flush=True)
        for proc in procs.values():
            try:
                proc.send_signal(signal.SIGTERM)
            except OSError:
                pass

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    # Lazy import to avoid circular concerns; only the supervisor needs this.
    from src.utils.geo_block import GEO_BLOCK_EXIT_CODE

    # Supervision loop -- poll children every 5 seconds.
    while not shutting_down:
        time.sleep(5)
        for s in list(procs.keys()):
            proc = procs[s]
            rc = proc.poll()
            if rc is None:
                continue  # still running

            if shutting_down:
                break

            # Fail-fast contract with the child runners: a geo-block
            # cannot be fixed by retrying, so the child exits with
            # GEO_BLOCK_EXIT_CODE (2) to signal "do not restart."
            # Stop the WHOLE supervisor -- both children share the same
            # Binance API, so if one is geo-blocked, the other is too.
            # Decision: DEC-2026-06-01-003.
            if rc == GEO_BLOCK_EXIT_CODE:
                print(
                    f"[run_all] {s} exited with GEO_BLOCK_EXIT_CODE "
                    f"({GEO_BLOCK_EXIT_CODE}). NOT restarting -- this is a "
                    f"Railway region issue, not a transient failure. "
                    f"Stopping wrapper to surface the problem to the operator.",
                    flush=True,
                )
                shutting_down = True
                break

            restarts[s] += 1
            if restarts[s] > MAX_RESTARTS:
                print(
                    f"[run_all] {s} exceeded max restarts "
                    f"({MAX_RESTARTS}). Stopping wrapper.",
                    flush=True,
                )
                shutting_down = True
                break

            print(
                f"[run_all] {s} exited (rc={rc}), "
                f"restart {restarts[s]}/{MAX_RESTARTS} "
                f"in {CRASH_COOLDOWN}s...",
                flush=True,
            )
            time.sleep(CRASH_COOLDOWN)
            procs[s] = _spawn(s)

    # Wait for children to finish.
    for proc in procs.values():
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("[run_all] All processes stopped.", flush=True)


if __name__ == "__main__":
    main()
