"""Unit tests for SubRegime-aware routing (DEC-2026-05-28-003).

Tests two layers:
  1. SubRegimeDetector confirmation contract (fail-closed on disagreement,
     UNKNOWN, or TRANSITIONAL).
  2. RegimeRouter._get_template_ids_for_regime new precedence:
     regime_tags > legacy regime field, with fail-closed on UNKNOWN sub.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.strategy.regime.detector import RegimeState
from src.core.strategy.regime.historical_classifier import SubRegime
from src.core.strategy.regime.router import RegimeRouter
from src.core.strategy.regime.sub_regime_detector import SubRegimeDetector


# ---------------------------------------------------------------------------
# SubRegimeDetector tests
# ---------------------------------------------------------------------------


class TestSubRegimeDetectorContract:
    """Verifies the fail-closed contract of confirmation."""

    def _detector_with_labels(self, labels: list[SubRegime]) -> SubRegimeDetector:
        """Build a SubRegimeDetector whose classifier returns the given labels."""
        det = SubRegimeDetector(fetcher=MagicMock())
        det._fetch_btc_daily = AsyncMock(return_value=MagicMock())  # type: ignore[method-assign]
        det._classifier = MagicMock()  # type: ignore[assignment]
        det._classifier.classify_series = MagicMock(return_value=labels)
        return det

    def test_invalid_confirmation_bars_rejected(self) -> None:
        with pytest.raises(ValueError, match="confirmation_bars"):
            SubRegimeDetector(fetcher=MagicMock(), confirmation_bars=0)

    def test_insufficient_daily_bars_rejected(self) -> None:
        with pytest.raises(ValueError, match="daily_bars"):
            SubRegimeDetector(fetcher=MagicMock(), daily_bars=100)

    def test_fetch_failure_returns_unknown(self) -> None:
        det = SubRegimeDetector(fetcher=MagicMock())
        det._fetch_btc_daily = AsyncMock(return_value=None)  # type: ignore[method-assign]
        assert asyncio.run(det.get_confirmed_state()) == SubRegime.UNKNOWN

    def test_agreement_returns_state(self) -> None:
        det = self._detector_with_labels([SubRegime.CHOPPY_BEAR, SubRegime.CHOPPY_BEAR])
        assert asyncio.run(det.get_confirmed_state()) == SubRegime.CHOPPY_BEAR

    def test_disagreement_returns_unknown(self) -> None:
        det = self._detector_with_labels(
            [SubRegime.CHOPPY_BEAR, SubRegime.TRENDING_BEAR]
        )
        assert asyncio.run(det.get_confirmed_state()) == SubRegime.UNKNOWN

    def test_anchor_unknown_returns_unknown(self) -> None:
        det = self._detector_with_labels(
            [SubRegime.UNKNOWN, SubRegime.CHOPPY_BEAR]
        )
        assert asyncio.run(det.get_confirmed_state()) == SubRegime.UNKNOWN

    def test_anchor_transitional_returns_unknown(self) -> None:
        det = self._detector_with_labels(
            [SubRegime.TRANSITIONAL, SubRegime.TRANSITIONAL]
        )
        assert asyncio.run(det.get_confirmed_state()) == SubRegime.UNKNOWN

    def test_three_bar_confirmation_strict(self) -> None:
        det = SubRegimeDetector(fetcher=MagicMock(), confirmation_bars=3)
        det._fetch_btc_daily = AsyncMock(return_value=MagicMock())  # type: ignore[method-assign]
        det._classifier = MagicMock()  # type: ignore[assignment]
        # 2 agree, 1 disagrees → UNKNOWN
        det._classifier.classify_series = MagicMock(
            return_value=[SubRegime.CHOPPY_BEAR, SubRegime.CHOPPY_BEAR, SubRegime.TRENDING_BEAR]
        )
        assert asyncio.run(det.get_confirmed_state()) == SubRegime.UNKNOWN
        # All 3 agree → state
        det._classifier.classify_series = MagicMock(
            return_value=[SubRegime.CHOPPY_BEAR] * 3
        )
        assert asyncio.run(det.get_confirmed_state()) == SubRegime.CHOPPY_BEAR


# ---------------------------------------------------------------------------
# RegimeRouter routing-precedence tests
# ---------------------------------------------------------------------------


def _router_with_config(cfg: dict[str, dict[str, Any]]) -> RegimeRouter:
    """Build a RegimeRouter with the given config (no detectors needed for these tests)."""
    return RegimeRouter(
        detector=MagicMock(),
        engine_factory=lambda ids: [],
        full_config=cfg,
        stop_event=asyncio.Event(),
        sub_detector=MagicMock(),  # presence only; we call _get directly
    )


class TestRouterTagPrecedence:
    """The new precedence (regime_tags > legacy regime > fail-closed on UNKNOWN sub)."""

    def test_regime_tags_match_activates(self) -> None:
        router = _router_with_config({
            "btp": {
                "regime": "bull",  # legacy says bull
                "regime_tags": ["choppy_bear"],  # but real edge is choppy_bear
            },
        })
        # In coarse STRONG_BEAR but confirmed CHOPPY_BEAR — should activate
        assert "btp" in router._get_template_ids_for_regime(
            RegimeState.STRONG_BEAR, SubRegime.CHOPPY_BEAR
        )

    def test_regime_tags_no_match_does_not_activate(self) -> None:
        router = _router_with_config({
            "btp": {"regime": "bull", "regime_tags": ["choppy_bear"]},
        })
        # SubRegime is trending_bear, not in BTP's tags → no activation
        assert "btp" not in router._get_template_ids_for_regime(
            RegimeState.STRONG_BEAR, SubRegime.TRENDING_BEAR
        )

    def test_regime_tags_with_unknown_sub_fails_closed(self) -> None:
        """The critical fail-closed contract — UNKNOWN sub_regime never activates a tagged strategy."""
        router = _router_with_config({
            "btp": {"regime": "bull", "regime_tags": ["choppy_bear"]},
        })
        # Even if coarse regime is_bull would normally activate, regime_tags
        # WITH unknown sub_regime must NOT activate.
        assert "btp" not in router._get_template_ids_for_regime(
            RegimeState.STRONG_BULL, SubRegime.UNKNOWN
        )

    def test_legacy_regime_fallback_unchanged(self) -> None:
        """Strategies without regime_tags still route via the legacy coarse field."""
        router = _router_with_config({
            "legacy_bull": {"regime": "bull"},
            "legacy_bear": {"regime": "bear"},
            "legacy_all": {"regime": "all"},
        })
        # In bull regime
        ids = router._get_template_ids_for_regime(
            RegimeState.STRONG_BULL, SubRegime.UNKNOWN
        )
        assert "legacy_bull" in ids
        assert "legacy_all" in ids
        assert "legacy_bear" not in ids

    def test_observe_only_never_activates(self) -> None:
        """observe_only=True keeps a tagged strategy out of router activation."""
        router = _router_with_config({
            "rvcb": {
                "regime": "bull",
                "regime_tags": ["trending_bear"],
                "observe_only": True,
            },
        })
        # Even with matching SubRegime, observe_only blocks activation
        assert "rvcb" not in router._get_template_ids_for_regime(
            RegimeState.STRONG_BEAR, SubRegime.TRENDING_BEAR
        )

    def test_mixed_config_routing(self) -> None:
        """Realistic mix: legacy + tagged + observe_only entries in same config."""
        router = _router_with_config({
            "macd_pb": {
                "regime": "bull",
                "regime_tags": ["choppy_bull", "choppy_bear", "trending_bull"],
            },
            "btp": {"regime": "bull", "regime_tags": ["choppy_bear"]},
            "vbb": {"regime": "bull", "regime_tags": ["choppy_bear"]},
            "icvp": {
                "regime": "all",
                "regime_tags": ["choppy_bull", "choppy_bear", "trending_bear"],
            },
            "rvcb": {
                "regime": "bull",
                "regime_tags": ["trending_bear"],
                "observe_only": True,
            },
            "legacy_all": {"regime": "all"},  # no regime_tags → coarse routing
        })
        # Current regime: STRONG_BEAR + CHOPPY_BEAR
        ids = router._get_template_ids_for_regime(
            RegimeState.STRONG_BEAR, SubRegime.CHOPPY_BEAR
        )
        assert "macd_pb" in ids  # choppy_bear in tags
        assert "btp" in ids
        assert "vbb" in ids
        assert "icvp" in ids
        assert "rvcb" not in ids  # observe_only
        assert "legacy_all" in ids  # coarse "all"


# ---------------------------------------------------------------------------
# Router alert tests — DEC-2026-05-28-003 SubRegime alerting
# ---------------------------------------------------------------------------


class TestRouterFlipAlert:
    """Verifies the unified alert covers both coarse and sub-regime changes."""

    def _make_router_with_telegram(self) -> tuple[RegimeRouter, MagicMock]:
        """Build a router with a mock Telegram channel that captures sent alerts."""
        telegram = MagicMock()
        telegram.send = AsyncMock()
        router = RegimeRouter(
            detector=MagicMock(),
            engine_factory=lambda ids: [],
            full_config={},
            stop_event=asyncio.Event(),
            telegram=telegram,
            sub_detector=MagicMock(),
        )
        return router, telegram

    def test_coarse_flip_alert_includes_sub(self) -> None:
        """Coarse macro flip alert should include the sub_regime info."""
        router, telegram = self._make_router_with_telegram()
        asyncio.run(router._send_flip_alert(
            RegimeState.STRONG_BULL, RegimeState.STRONG_BEAR,
            SubRegime.CHOPPY_BULL, SubRegime.CHOPPY_BEAR,
        ))
        assert telegram.send.call_count == 1
        alert = telegram.send.call_args.args[0]
        assert "REGIME FLIP" in alert.title
        assert "strong_bear" in alert.title.lower()
        assert "strong_bull" in alert.message  # old coarse
        assert "strong_bear" in alert.message  # new coarse
        assert "choppy_bull" in alert.message  # old sub
        assert "choppy_bear" in alert.message  # new sub

    def test_sub_only_change_uses_sub_alert_title(self) -> None:
        """Sub-regime change without coarse flip uses the SUB-REGIME CHANGE title."""
        router, telegram = self._make_router_with_telegram()
        asyncio.run(router._send_flip_alert(
            RegimeState.STRONG_BEAR, RegimeState.STRONG_BEAR,  # coarse unchanged
            SubRegime.TRENDING_BEAR, SubRegime.CHOPPY_BEAR,   # sub changed
        ))
        assert telegram.send.call_count == 1
        alert = telegram.send.call_args.args[0]
        assert "SUB-REGIME CHANGE" in alert.title
        assert "choppy_bear" in alert.title.lower()
        assert "trending_bear" in alert.message  # old sub
        assert "unchanged" in alert.message.lower()  # coarse marked unchanged

    def test_alert_omits_sub_line_when_no_sub_detector(self) -> None:
        """Router without sub_detector should not include the Sub: line."""
        telegram = MagicMock()
        telegram.send = AsyncMock()
        router = RegimeRouter(
            detector=MagicMock(),
            engine_factory=lambda ids: [],
            full_config={},
            stop_event=asyncio.Event(),
            telegram=telegram,
            sub_detector=None,  # explicitly no sub detector
        )
        asyncio.run(router._send_flip_alert(
            RegimeState.STRONG_BULL, RegimeState.STRONG_BEAR,
        ))
        alert = telegram.send.call_args.args[0]
        # Coarse info should be present
        assert "strong_bear" in alert.message
        # Sub line should NOT be present since no sub detector
        assert "Sub:" not in alert.message

    def test_no_telegram_means_no_alert(self) -> None:
        """When telegram is None, the alert call is a no-op (no crash)."""
        router = RegimeRouter(
            detector=MagicMock(),
            engine_factory=lambda ids: [],
            full_config={},
            stop_event=asyncio.Event(),
            telegram=None,
        )
        # Should not raise
        asyncio.run(router._send_flip_alert(
            RegimeState.STRONG_BULL, RegimeState.STRONG_BEAR,
        ))

    def test_telegram_failure_is_caught(self) -> None:
        """Telegram send failure should be logged, not raised."""
        router, telegram = self._make_router_with_telegram()
        telegram.send = AsyncMock(side_effect=RuntimeError("network broke"))
        # Should not raise — error swallowed and logged
        asyncio.run(router._send_flip_alert(
            RegimeState.STRONG_BULL, RegimeState.STRONG_BEAR,
        ))
