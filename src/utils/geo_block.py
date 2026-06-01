"""Geo-block detection for fail-fast Binance regulatory rejections.

When a Binance API call is rejected because the calling IP is in a
restricted region (e.g., US states without an exchange license),
Binance returns an APIError with a distinctive message referencing
their Eligibility terms. This module detects that signature so the
crash-restart harness can exit immediately with a special code rather
than wasting the full retry budget on a failure that cannot self-heal.

Decision: DEC-2026-06-01-003.

Contract:
    is_geo_block_error(exc) -> bool
        True iff the exception text contains a Binance-specific
        geo-restriction signature. False positives are minimised by
        requiring distinctive Binance phrasing (not generic strings
        like "Service unavailable" which could match unrelated errors).

    GEO_BLOCK_EXIT_CODE
        The exit code used by both run_paper_trading and run_live_trading
        when they detect a geo-block. The supervisor (run_all.py)
        recognises this code and does NOT restart — geo restrictions
        cannot be fixed by retrying.

    print_geo_block_message(stream=stdout)
        Prints a clear operator-facing message explaining the diagnosis
        and the fix. Used by both the inner runners and the supervisor.
"""
from __future__ import annotations

import sys
from typing import TextIO

# Distinctive Binance signatures for geo-restriction errors. We use these
# instead of generic phrases ("Service unavailable" alone) to avoid false
# positives from unrelated transient errors. ANY match triggers fail-fast.
GEO_BLOCK_SIGNATURES: tuple[str, ...] = (
    "restricted location",  # Binance's specific phrasing
    "b. Eligibility",       # Reference to their Eligibility terms (geo-only)
)

# Exit code used by inner runners on geo-block detection. The supervisor
# (run_all.py) treats this code as "do not restart — operator must
# intervene." Any code in [1, 255] would work; 2 is conventional for
# "misuse / configuration error" in Unix exit-code conventions.
GEO_BLOCK_EXIT_CODE: int = 2


def is_geo_block_error(exc: BaseException | str) -> bool:
    """Return True iff the exception text matches a geo-block signature.

    Args:
        exc: Either an exception instance (str() is applied) or a raw
            string (e.g., from a captured stderr line).

    Returns:
        True if the text contains at least one distinctive Binance
        geo-restriction signature; False otherwise. Case-sensitive
        because Binance is consistent in their error phrasing.
    """
    text = str(exc) if isinstance(exc, BaseException) else exc
    return any(sig in text for sig in GEO_BLOCK_SIGNATURES)


def print_geo_block_message(
    stream: TextIO = sys.stdout,
    context: str = "",
) -> None:
    """Print the operator-facing geo-block diagnosis and fix instructions.

    Args:
        stream: Where to print (default stdout for Railway log capture).
        context: Optional context string (e.g., the subprocess name)
            for log clarity.
    """
    ctx = f" [{context}]" if context else ""
    msg = (
        "\n"
        "============================================================\n"
        f"GEO-BLOCK DETECTED{ctx}\n"
        "============================================================\n"
        "Binance has rejected our request because the server IP is in\n"
        "a restricted region. This is NOT a code bug — retries cannot\n"
        "fix it. The runner is exiting with code "
        f"{GEO_BLOCK_EXIT_CODE} so the supervisor\n"
        "stops restarting (saves ~30 min of wasted attempts).\n"
        "\n"
        "Fix (Railway dashboard, ~5 min):\n"
        "  1. Open the service Settings\n"
        "  2. Change the deployment region to a Binance-friendly one:\n"
        "     - europe-west4 (Netherlands) -- previously confirmed working\n"
        "     - asia-southeast1 (Singapore) -- alternative\n"
        "     - europe-west1 (Belgium) -- alternative\n"
        "  3. Redeploy. Should see this banner disappear within 3 min.\n"
        "\n"
        "Background: see DEC-2026-06-01-003 in .claude/DECISIONS.md\n"
        "and the original fix attempt in commit 476878e.\n"
        "============================================================\n"
    )
    print(msg, file=stream, flush=True)
