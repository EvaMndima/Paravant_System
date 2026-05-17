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

SCRIPTS = [
    "scripts.run_paper_trading",
    "scripts.run_live_trading",
]

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
    print(f"  Paper trading: {SCRIPTS[0]}")
    print(f"  Live trading:  {SCRIPTS[1]}")
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
        print(f"\nWrapper received signal {sig} — stopping children.", flush=True)
        for proc in procs.values():
            try:
                proc.send_signal(signal.SIGTERM)
            except OSError:
                pass

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    # Supervision loop — poll children every 5 seconds.
    while not shutting_down:
        time.sleep(5)
        for s in list(procs.keys()):
            proc = procs[s]
            rc = proc.poll()
            if rc is None:
                continue  # still running

            if shutting_down:
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
