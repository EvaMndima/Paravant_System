"""Unit tests for the geo-block fail-fast helper (DEC-2026-06-01-003).

The detector's job is dual: (1) reliably catch the actual Binance
geo-restriction error so the supervisor can fail fast, and (2) NOT
fire on superficially-similar errors that would self-heal on retry.
The false-positive direction matters more than the false-negative
direction — a false negative wastes 30 minutes of retries; a false
positive permanently halts the system on a transient blip.
"""
from __future__ import annotations

import io

import pytest

from src.utils.geo_block import (
    GEO_BLOCK_EXIT_CODE,
    GEO_BLOCK_SIGNATURES,
    is_geo_block_error,
    print_geo_block_message,
)


# ---------------------------------------------------------------------------
# Detection — must-catch cases (the actual production error text)
# ---------------------------------------------------------------------------


class TestDetectsRealBinanceErrors:
    """Real Binance geo-restriction error messages MUST be detected."""

    def test_full_actual_production_error(self) -> None:
        """The exact text from Railway logs on 2026-06-01."""
        err = (
            "APIError(code=0): Service unavailable from a restricted "
            "location according to 'b. Eligibility' in "
            "https://www.binance.com/en/terms. Please contact customer "
            "service if you believe you received this message in error."
        )
        assert is_geo_block_error(err) is True

    def test_exception_instance(self) -> None:
        """Detector should accept an exception, not just a string."""
        exc = RuntimeError(
            "APIError(code=0): Service unavailable from a restricted location"
        )
        assert is_geo_block_error(exc) is True

    def test_only_restricted_location_phrase(self) -> None:
        """Either signature alone is sufficient (defensive against minor wording changes)."""
        err = "Some new wrapper text: restricted location detected"
        assert is_geo_block_error(err) is True

    def test_only_eligibility_phrase(self) -> None:
        """The 'b. Eligibility' marker alone is also sufficient."""
        err = "Some other phrasing pointing to 'b. Eligibility' clause"
        assert is_geo_block_error(err) is True


# ---------------------------------------------------------------------------
# Rejection — must-NOT-fire cases (critical for avoiding false positives)
# ---------------------------------------------------------------------------


class TestRejectsUnrelatedErrors:
    """Generic / unrelated errors MUST NOT trigger fail-fast."""

    def test_generic_service_unavailable(self) -> None:
        """A bare 'Service unavailable' (e.g. 503) is NOT geo-block.

        This is a common transient error that legitimately should
        trigger restart. We deliberately do NOT include this phrase in
        the signatures.
        """
        assert is_geo_block_error("Service unavailable") is False
        assert is_geo_block_error("503 Service Unavailable") is False

    def test_network_timeout(self) -> None:
        assert is_geo_block_error("Read timed out") is False
        assert is_geo_block_error("ConnectTimeout") is False

    def test_invalid_api_key(self) -> None:
        """An invalid API key error is not a geo issue."""
        assert (
            is_geo_block_error("Invalid API-key, IP, or permissions for action")
            is False
        )

    def test_random_runtime_error(self) -> None:
        assert is_geo_block_error("ValueError: bad value") is False

    def test_empty_string(self) -> None:
        assert is_geo_block_error("") is False

    def test_random_keyboard_interrupt(self) -> None:
        assert is_geo_block_error(KeyboardInterrupt()) is False


# ---------------------------------------------------------------------------
# Constants — exit code contract with the supervisor
# ---------------------------------------------------------------------------


class TestExitCodeContract:
    """The supervisor reads this constant; it must remain stable."""

    def test_exit_code_is_2(self) -> None:
        """GEO_BLOCK_EXIT_CODE must be 2 (the supervisor's expectation)."""
        assert GEO_BLOCK_EXIT_CODE == 2

    def test_signatures_are_immutable_tuple(self) -> None:
        """Signatures must be a tuple — not mutable from outside."""
        assert isinstance(GEO_BLOCK_SIGNATURES, tuple)
        assert len(GEO_BLOCK_SIGNATURES) >= 1


# ---------------------------------------------------------------------------
# Operator message — printed on fail-fast
# ---------------------------------------------------------------------------


class TestOperatorMessage:
    """The printed message must include the critical operator info."""

    def _capture(self, context: str = "") -> str:
        buf = io.StringIO()
        print_geo_block_message(stream=buf, context=context)
        return buf.getvalue()

    def test_message_mentions_geo_block(self) -> None:
        out = self._capture()
        assert "GEO-BLOCK" in out

    def test_message_mentions_fix_action(self) -> None:
        """Message must tell the operator how to fix it."""
        out = self._capture()
        assert "Railway" in out
        assert "region" in out.lower()

    def test_message_lists_known_good_regions(self) -> None:
        """At least one previously-confirmed-working region should appear."""
        out = self._capture()
        assert "europe-west4" in out

    def test_message_references_decision_doc(self) -> None:
        """Message points back to the canonical decision record."""
        out = self._capture()
        assert "DEC-2026-06-01-003" in out

    def test_message_includes_context_when_provided(self) -> None:
        out = self._capture(context="paper_trading")
        assert "paper_trading" in out

    def test_message_includes_exit_code(self) -> None:
        """Operator should see the exit code so they can correlate with supervisor logs."""
        out = self._capture()
        assert str(GEO_BLOCK_EXIT_CODE) in out
