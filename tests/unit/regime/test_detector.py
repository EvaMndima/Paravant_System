"""Unit tests for RegimeDetector and RegimeState.

Uses small EMA periods (fast=3, slow=7) with synthetic price series so
tests do not call real Binance and are deterministic.

Decision: DEC-2026-05-04-001 - Dual-EMA composite 4-state approach
Decision: DEC-2026-05-04-002 - 2-consecutive-close confirmation rule
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.strategy.regime.detector import RegimeDetector, RegimeState
from src.data.market_data import OHLCV, OHLCVSeries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_series(closes: list[float]) -> OHLCVSeries:
    """Build a synthetic BTC 1d OHLCVSeries from a list of close prices.

    Each candle has open=close (flat), high=close*1.001, low=close*0.999
    so all OHLCV validation rules pass.
    """
    base_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles: list[OHLCV] = []
    for i, close in enumerate(closes):
        h = close * 1.001
        lo = close * 0.999
        candles.append(
            OHLCV(
                timestamp=base_time + timedelta(days=i),
                open=close,
                high=h,
                low=lo,
                close=close,
                volume=1_000.0,
            )
        )
    return OHLCVSeries(candles=candles, symbol="BTCUSDT", timeframe="1d")


def _make_fetcher(series: OHLCVSeries) -> MagicMock:
    """Return a mock MarketDataFetcher that returns the given series."""
    fetcher = MagicMock()
    fetcher.fetch_ohlcv = AsyncMock(return_value=series)
    return fetcher


def _make_detector(fetcher: MagicMock) -> RegimeDetector:
    """Create a RegimeDetector with small EMA periods for unit testing."""
    return RegimeDetector(
        fetcher=fetcher,
        ema_fast=3,
        ema_slow=7,
        confirmation_bars=2,
        daily_bars=20,
    )


# ---------------------------------------------------------------------------
# Strongly trending price series
# ---------------------------------------------------------------------------

# 20 bars of steady uptrend (100 -> 290). EMA(3) closely tracks recent
# prices; EMA(7) lags. Final close (290) > EMA(3) > EMA(7) → STRONG_BULL.
UPTREND_CLOSES: list[float] = [float(100 + 10 * i) for i in range(20)]

# 20 bars of steady downtrend (290 -> 100). EMA(3) < EMA(7) and close
# (100) far below both → STRONG_BEAR.
DOWNTREND_CLOSES: list[float] = [float(290 - 10 * i) for i in range(20)]

# 18 bars uptrend then a sharp crash that flips EMA(3) below EMA(7).
# Used for confirmation disagreement: second-to-last bar is BULL, last is BEAR.
CRASH_CLOSES: list[float] = [float(100 + 10 * i) for i in range(18)] + [240.0, 40.0]


# ---------------------------------------------------------------------------
# Tests: detect()
# ---------------------------------------------------------------------------


class TestDetect:
    """Tests for RegimeDetector.detect() — raw single-bar classification."""

    @pytest.mark.asyncio
    async def test_strong_bull_when_ema_fast_above_ema_slow_and_close_above_fast(
        self,
    ) -> None:
        """detect() returns STRONG_BULL on a clear uptrend.

        Decision: DEC-2026-05-04-001
        """
        series = _make_series(UPTREND_CLOSES)
        detector = _make_detector(_make_fetcher(series))

        state = await detector.detect()

        assert state == RegimeState.STRONG_BULL
        assert state.is_bull is True
        assert state.is_bear is False

    @pytest.mark.asyncio
    async def test_strong_bear_when_ema_fast_below_ema_slow_and_close_below_fast(
        self,
    ) -> None:
        """detect() returns STRONG_BEAR on a clear downtrend.

        Decision: DEC-2026-05-04-001
        """
        series = _make_series(DOWNTREND_CLOSES)
        detector = _make_detector(_make_fetcher(series))

        state = await detector.detect()

        assert state == RegimeState.STRONG_BEAR
        assert state.is_bear is True
        assert state.is_bull is False

    @pytest.mark.asyncio
    async def test_unknown_when_fetcher_raises(self) -> None:
        """detect() returns UNKNOWN when the data fetch fails — does not propagate.

        Ensures network failures degrade gracefully rather than crashing the runner.
        """
        fetcher = MagicMock()
        fetcher.fetch_ohlcv = AsyncMock(side_effect=ConnectionError("timeout"))
        detector = _make_detector(fetcher)

        state = await detector.detect()

        assert state == RegimeState.UNKNOWN

    @pytest.mark.asyncio
    async def test_unknown_when_series_too_short_for_ema_warmup(self) -> None:
        """detect() returns UNKNOWN when series is shorter than ema_slow — not ValueError.

        EMA(7) requires at least 7 bars; with only 4 bars it cannot compute.
        The detector must handle this gracefully and return UNKNOWN.
        """
        series = _make_series([100.0, 110.0, 120.0, 130.0])
        detector = _make_detector(_make_fetcher(series))

        state = await detector.detect()

        assert state == RegimeState.UNKNOWN


# ---------------------------------------------------------------------------
# Tests: get_confirmed_state()
# ---------------------------------------------------------------------------


class TestGetConfirmedState:
    """Tests for RegimeDetector.get_confirmed_state() — 2-bar confirmation."""

    @pytest.mark.asyncio
    async def test_confirmed_bull_when_last_two_bars_agree(self) -> None:
        """get_confirmed_state() returns a bull state when both closes agree.

        Decision: DEC-2026-05-04-002
        """
        series = _make_series(UPTREND_CLOSES)
        detector = _make_detector(_make_fetcher(series))

        state = await detector.get_confirmed_state()

        assert state.is_bull is True
        assert state != RegimeState.UNKNOWN

    @pytest.mark.asyncio
    async def test_unknown_when_last_two_bars_disagree_on_macro_side(self) -> None:
        """get_confirmed_state() returns UNKNOWN on a bull-bear disagreement.

        Decision: DEC-2026-05-04-002 - 2-consecutive-close rule prevents whipsaws.

        CRASH_CLOSES has 18 bars of uptrend then a severe crash.
        Bar[-2] (240) is in bull territory; bar[-1] (40) flips EMA(3) below
        EMA(7), making it bear. Since the two closes disagree on macro side,
        confirmation fails and UNKNOWN is returned.
        """
        series = _make_series(CRASH_CLOSES)
        detector = _make_detector(_make_fetcher(series))

        state = await detector.get_confirmed_state()

        assert state == RegimeState.UNKNOWN

    @pytest.mark.asyncio
    async def test_confirmed_bear_when_last_two_bars_agree(self) -> None:
        """get_confirmed_state() returns a bear state when both closes agree.

        Decision: DEC-2026-05-04-002
        """
        series = _make_series(DOWNTREND_CLOSES)
        detector = _make_detector(_make_fetcher(series))

        state = await detector.get_confirmed_state()

        assert state.is_bear is True
        assert state != RegimeState.UNKNOWN

    @pytest.mark.asyncio
    async def test_unknown_when_fetcher_raises_during_confirmation(self) -> None:
        """get_confirmed_state() returns UNKNOWN on fetch failure — does not propagate."""
        fetcher = MagicMock()
        fetcher.fetch_ohlcv = AsyncMock(side_effect=RuntimeError("api down"))
        detector = _make_detector(fetcher)

        state = await detector.get_confirmed_state()

        assert state == RegimeState.UNKNOWN


# ---------------------------------------------------------------------------
# Tests: RegimeState properties
# ---------------------------------------------------------------------------


class TestRegimeState:
    """Tests for RegimeState.is_bull / is_bear properties."""

    def test_strong_bull_is_bull(self) -> None:
        assert RegimeState.STRONG_BULL.is_bull is True
        assert RegimeState.STRONG_BULL.is_bear is False

    def test_pullback_bull_is_bull(self) -> None:
        assert RegimeState.PULLBACK_BULL.is_bull is True
        assert RegimeState.PULLBACK_BULL.is_bear is False

    def test_strong_bear_is_bear(self) -> None:
        assert RegimeState.STRONG_BEAR.is_bear is True
        assert RegimeState.STRONG_BEAR.is_bull is False

    def test_bounce_bear_is_bear(self) -> None:
        assert RegimeState.BOUNCE_BEAR.is_bear is True
        assert RegimeState.BOUNCE_BEAR.is_bull is False

    def test_unknown_is_neither(self) -> None:
        assert RegimeState.UNKNOWN.is_bull is False
        assert RegimeState.UNKNOWN.is_bear is False

    def test_all_states_have_string_values(self) -> None:
        for state in RegimeState:
            assert isinstance(state.value, str)
            assert len(state.value) > 0


# ---------------------------------------------------------------------------
# Tests: RegimeDetector.__init__ validation
# ---------------------------------------------------------------------------


class TestRegimeDetectorInit:
    """Validate RegimeDetector constructor raises on invalid parameters."""

    def test_raises_when_ema_fast_not_less_than_ema_slow(self) -> None:
        fetcher = MagicMock()
        with pytest.raises(ValueError, match="ema_fast"):
            RegimeDetector(fetcher=fetcher, ema_fast=7, ema_slow=7)

    def test_raises_when_confirmation_bars_is_zero(self) -> None:
        fetcher = MagicMock()
        with pytest.raises(ValueError, match="confirmation_bars"):
            RegimeDetector(fetcher=fetcher, ema_fast=3, ema_slow=7, confirmation_bars=0)

    def test_raises_when_daily_bars_too_small_for_warmup(self) -> None:
        fetcher = MagicMock()
        with pytest.raises(ValueError, match="daily_bars"):
            RegimeDetector(
                fetcher=fetcher, ema_fast=3, ema_slow=7, confirmation_bars=2,
                daily_bars=8  # must exceed ema_slow (7) + confirmation_bars (2) = 9
            )
