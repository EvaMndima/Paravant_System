"""Tests for the point-in-time feature store and its leakage audits.

The load-bearing tests are:

  TestBarAlignmentLeak    reproduces the real defect found in this repository --
                          a 1H bar stamped with its OPEN time whose CLOSE was
                          readable mid-bar -- and asserts the store rejects it.
  TestWhyTwoAudits        asserts that the intuitive audit (future invariance)
                          does NOT catch that defect while the knowability audit
                          does. This is why both exist.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from research.features import (
    FeatureKind,
    FeatureSpec,
    LeakageError,
    Observation,
    PointInTimeFeatureStore,
    audit_future_invariance,
    audit_knowability,
    render_reports,
)

_T0 = datetime(2026, 6, 11, 10, 0, 0, tzinfo=timezone.utc)
_HOUR = timedelta(hours=1)
_DAY = timedelta(days=1)


def _hourly_bar_spec(name: str = "bar_close") -> FeatureSpec:
    """A 1H bar close: an interval feature stamped with the bar's open."""
    return FeatureSpec(
        name=name,
        description="1H bar close, stamped with the bar open",
        kind=FeatureKind.INTERVAL,
        interval=_HOUR,
        publication_lag=timedelta(0),
        unit="USD",
        source="test",
    )


def _bars(n: int = 4) -> list[tuple[datetime, float]]:
    """n hourly bars starting at _T0, close = 100, 101, ..."""
    return [(_T0 + i * _HOUR, 100.0 + i) for i in range(n)]


def _bar_resolver(bars):
    """The DEFECTIVE adapter: latest bar whose OPEN is at or before ts.

    This reproduces what coinbase_prices and btc_reference did. The `<=` on an
    open time is itself the bug: at 10:30 the 10:00 bar qualifies, and its close
    is a price from 11:00.
    """

    def resolve(symbol: str | None, ts: datetime) -> Observation | None:
        eligible = [b for b in bars if b[0] <= ts]
        if not eligible:
            return None
        opened_at, close = eligible[-1]
        return Observation(value=close, observed_at=opened_at)

    return resolve


def _completed_bar_resolver(bars, interval: timedelta = _HOUR):
    """The CORRECT adapter: latest bar that has actually CLOSED by ts.

    The remedy for the defect above -- select on the bar's end, not its start.
    Still reports the bar's open as observed_at, because that is the honest
    timestamp; the store adds the interval to work out knowability.
    """

    def resolve(symbol: str | None, ts: datetime) -> Observation | None:
        eligible = [b for b in bars if b[0] + interval <= ts]
        if not eligible:
            return None
        opened_at, close = eligible[-1]
        return Observation(value=close, observed_at=opened_at)

    return resolve


# ---------------------------------------------------------------------------
# FeatureSpec
# ---------------------------------------------------------------------------


class TestFeatureSpec:
    """Specification validation and knowability arithmetic."""

    def test_interval_feature_requires_an_interval(self) -> None:
        """An INTERVAL feature without a duration cannot be checked at all."""
        with pytest.raises(ValueError, match="require a positive interval"):
            FeatureSpec(
                name="x", description="", kind=FeatureKind.INTERVAL,
                publication_lag=timedelta(0), unit="", source="test",
            )

    def test_instant_feature_rejects_an_interval(self) -> None:
        """Declaring both is contradictory and is refused."""
        with pytest.raises(ValueError, match="must not declare an interval"):
            FeatureSpec(
                name="x", description="", kind=FeatureKind.INSTANT,
                interval=_HOUR, publication_lag=timedelta(0), unit="", source="test",
            )

    def test_negative_publication_lag_rejected(self) -> None:
        """A negative lag would mean data is known before it exists."""
        with pytest.raises(ValueError, match="cannot be negative"):
            FeatureSpec(
                name="x", description="", kind=FeatureKind.INSTANT,
                publication_lag=-_HOUR, unit="", source="test",
            )

    def test_instant_knowable_immediately(self) -> None:
        """An instant observation with no lag is knowable at its timestamp."""
        spec = FeatureSpec(
            name="f", description="", kind=FeatureKind.INSTANT,
            publication_lag=timedelta(0), unit="", source="test",
        )
        assert spec.knowable_at(_T0) == _T0

    def test_interval_knowable_only_after_the_period_ends(self) -> None:
        """A 1H bar opened at 10:00 is not knowable until 11:00."""
        assert _hourly_bar_spec().knowable_at(_T0) == _T0 + _HOUR

    def test_publication_lag_adds_to_the_interval_end(self) -> None:
        """Day D flow, reported T+1, is knowable at D+2 00:00."""
        spec = FeatureSpec(
            name="etf", description="", kind=FeatureKind.INTERVAL,
            interval=_DAY, publication_lag=_DAY, unit="", source="test",
        )
        assert spec.knowable_at(_T0) == _T0 + 2 * _DAY

    def test_naive_timestamp_rejected(self) -> None:
        """UTC discipline is enforced at the boundary."""
        with pytest.raises(ValueError, match="timezone-aware"):
            _hourly_bar_spec().knowable_at(datetime(2026, 6, 11, 10, 0, 0))


# ---------------------------------------------------------------------------
# The real defect
# ---------------------------------------------------------------------------


class TestBarAlignmentLeak:
    """Reproduces the defect found in coinbase_prices and btc_reference.

    Both channels stored bar OPEN times alongside values derived from the bar's
    CLOSE, so a mid-bar query received a price from the end of the bar -- up to
    59 minutes of future information. Each channel's accessor was documented as
    causal and, read alone, looked correct.
    """

    def test_mid_bar_read_of_a_bar_close_is_rejected(self) -> None:
        """Querying at 10:30 must not return the 10:00-11:00 bar's close."""
        store = PointInTimeFeatureStore()
        store.register(_hourly_bar_spec(), _bar_resolver(_bars()))

        with pytest.raises(LeakageError, match="after the query instant"):
            store.as_of(_T0 + timedelta(minutes=30))

    def test_the_same_bar_is_fine_once_it_has_closed(self) -> None:
        """At 11:00 the 10:00 bar is complete and legitimately readable.

        Uses the corrected adapter, which selects on the bar's close. The
        defective one returns the 11:00 bar here -- still open -- and is
        correctly rejected; that is the previous test.
        """
        store = PointInTimeFeatureStore()
        store.register(_hourly_bar_spec(), _completed_bar_resolver(_bars()))

        values = store.as_of(_T0 + _HOUR)
        assert values["bar_close"].value == 100.0
        assert values["bar_close"].knowable_at == _T0 + _HOUR

    def test_non_strict_mode_records_the_leak_as_missing(self) -> None:
        """Auditing a suspect channel should not require aborting the run."""
        store = PointInTimeFeatureStore()
        store.register(_hourly_bar_spec(), _bar_resolver(_bars()))

        values = store.as_of(_T0 + timedelta(minutes=30), strict=False)
        assert values["bar_close"].value is None
        # The provenance is preserved so the caller can see WHY it is missing.
        assert values["bar_close"].observed_at == _T0
        assert values["bar_close"].knowable_at == _T0 + _HOUR

    def test_audit_reports_the_leak_and_its_size(self) -> None:
        """The audit quantifies the leak rather than just flagging it."""
        spec = _hourly_bar_spec()
        report = audit_knowability(
            spec,
            _bar_resolver(_bars()),
            [_T0 + timedelta(minutes=m) for m in (30, 45, 59)],
        )
        assert not report.clean
        assert len(report.findings) == 3
        # Worst leak is at 10:30: the bar closes 30 minutes later.
        assert report.worst_leak_seconds == pytest.approx(30 * 60)
        assert "[LEAK]" in report.summary()


class TestWhyTwoAudits:
    """The intuitive audit does not catch the defect the repo actually had.

    `audit_future_invariance` asks whether removing observations after t changes
    the answer at t. For the bar-alignment defect it does not: the 10:00 bar's
    timestamp is genuinely at or before 10:30, so truncating at 10:30 keeps it,
    and both variants return the same (leaked) value.

    A suite containing only that check would have passed on a channel leaking
    59 minutes of future prices.
    """

    def test_future_invariance_does_not_catch_bar_alignment(self) -> None:
        """The counterfactual check passes on genuinely leaking data."""
        spec = _hourly_bar_spec()
        bars = _bars()
        report = audit_future_invariance(
            spec,
            lambda obs: _bar_resolver([(t, v) for t, v in obs]),
            [(t, v) for t, v in bars],
            [_T0 + timedelta(minutes=30)],
        )
        assert report.clean, "expected the counterfactual check to miss this"

    def test_knowability_does_catch_bar_alignment(self) -> None:
        """The spec-based check catches what the counterfactual misses."""
        report = audit_knowability(
            _hourly_bar_spec(), _bar_resolver(_bars()), [_T0 + timedelta(minutes=30)]
        )
        assert not report.clean

    def test_future_invariance_catches_a_resolver_reading_ahead(self) -> None:
        """And the counterfactual catches what the spec check cannot."""
        spec = FeatureSpec(
            name="peeker", description="", kind=FeatureKind.INSTANT,
            publication_lag=timedelta(0), unit="", source="test",
        )

        def build_peeking_resolver(obs):
            # Bug: returns the LAST observation in the dataset regardless of ts,
            # then mislabels it with an in-range timestamp. Knowability cannot
            # see this; invariance can.
            def resolve(symbol: str | None, ts: datetime) -> Observation | None:
                if not obs:
                    return None
                return Observation(value=obs[-1][1], observed_at=ts)
            return resolve

        report = audit_future_invariance(
            spec,
            build_peeking_resolver,
            [(t, v) for t, v in _bars()],
            [_T0 + timedelta(minutes=30)],
        )
        assert not report.clean
        assert report.findings[0].check == "future_invariance"


# ---------------------------------------------------------------------------
# Store behaviour
# ---------------------------------------------------------------------------


class TestStore:
    """Registration, resolution and matrix construction."""

    @staticmethod
    def _instant_spec(name: str) -> FeatureSpec:
        return FeatureSpec(
            name=name, description="", kind=FeatureKind.INSTANT,
            publication_lag=timedelta(0), unit="", source="test",
        )

    def test_duplicate_registration_rejected(self) -> None:
        """Two definitions of one name is how training and live diverge."""
        store = PointInTimeFeatureStore()
        spec = self._instant_spec("f")
        store.register(spec, lambda s, t: None)
        with pytest.raises(ValueError, match="already registered"):
            store.register(spec, lambda s, t: None)

    def test_unknown_feature_raises(self) -> None:
        """Asking for an unregistered feature is an error, not a silent None."""
        store = PointInTimeFeatureStore()
        with pytest.raises(KeyError, match="not registered"):
            store.as_of(_T0, names=["nope"])

    def test_naive_query_instant_rejected(self) -> None:
        """UTC discipline at the query boundary."""
        store = PointInTimeFeatureStore()
        with pytest.raises(ValueError, match="timezone-aware"):
            store.as_of(datetime(2026, 6, 11, 10, 0, 0))

    def test_missing_history_yields_a_present_but_empty_value(self) -> None:
        """Callers get a stable shape rather than an absent key."""
        store = PointInTimeFeatureStore()
        store.register(self._instant_spec("f"), lambda s, t: None)

        value = store.as_of(_T0)["f"]
        assert value.is_missing
        assert value.value is None
        assert value.staleness is None

    def test_staleness_is_reported(self) -> None:
        """A value queried an hour after it became knowable is an hour stale."""
        store = PointInTimeFeatureStore()
        store.register(
            self._instant_spec("f"),
            lambda s, t: Observation(value=1.0, observed_at=_T0),
        )
        assert store.as_of(_T0 + _HOUR)["f"].staleness == _HOUR

    def test_publication_lag_hides_a_value_until_it_is_published(self) -> None:
        """ETF-style T+1: day D's value is invisible until D+2 here."""
        spec = FeatureSpec(
            name="flow", description="", kind=FeatureKind.INTERVAL,
            interval=_DAY, publication_lag=_DAY, unit="", source="test",
        )
        store = PointInTimeFeatureStore()
        store.register(spec, lambda s, t: Observation(value=42.0, observed_at=_T0))

        # One day later the period has closed but it is not yet published.
        with pytest.raises(LeakageError):
            store.as_of(_T0 + _DAY)

        assert store.as_of(_T0 + 2 * _DAY)["flow"].value == 42.0


class TestFeatureMatrix:
    """Matrix construction, the training-set path."""

    def test_rows_are_resolved_independently_per_instant(self) -> None:
        """Each row may only contain what existed at its own timestamp."""
        store = PointInTimeFeatureStore()
        store.register(_hourly_bar_spec(), _completed_bar_resolver(_bars(4)))

        # Query on the hour, when each bar has just closed.
        stamps = [_T0 + (i + 1) * _HOUR for i in range(3)]
        matrix = store.build_matrix(stamps)

        assert matrix.names == ("bar_close",)
        assert len(matrix) == 3
        # At 11:00 only the 10:00 bar has closed, and so on.
        assert [row[0] for row in matrix.rows] == [100.0, 101.0, 102.0]

    def test_missing_rate_is_reported(self) -> None:
        """A feature with no history for the range is visibly empty."""
        store = PointInTimeFeatureStore()
        store.register(_hourly_bar_spec(), _completed_bar_resolver(_bars(1)))

        # Query before the series starts: nothing knowable.
        matrix = store.build_matrix([_T0 - _HOUR, _T0 - 2 * _HOUR])
        assert matrix.missing_rate() == {"bar_close": 1.0}

    def test_matrix_refuses_to_build_over_a_leaking_feature(self) -> None:
        """A training set is exactly where lookahead must not be tolerated."""
        store = PointInTimeFeatureStore()
        store.register(_hourly_bar_spec(), _bar_resolver(_bars()))

        with pytest.raises(LeakageError):
            store.build_matrix([_T0 + timedelta(minutes=30)])


def test_render_reports_separates_clean_from_leaking() -> None:
    """The rendered block is ASCII and names the leaking features last."""
    clean = audit_knowability(
        _hourly_bar_spec("clean"), _completed_bar_resolver(_bars()), [_T0 + _HOUR]
    )
    leaking = audit_knowability(
        _hourly_bar_spec("leaky"), _bar_resolver(_bars()), [_T0 + timedelta(minutes=30)]
    )
    rendered = render_reports([clean, leaking])

    assert "[OK]   clean" in rendered
    assert "[LEAK] leaky" in rendered
    assert "1 clean, 1 leaking" in rendered
    assert rendered.isascii()
