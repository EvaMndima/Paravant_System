"""Feature specs and resolvers for the existing research data channels.

Each channel in ``research/data/`` already exposes a causal accessor. What it
does not expose is *when* the value it returns was observed, which is the fact
the store needs to verify knowability. These adapters supply that.

The adapters are deliberately thin. They do not fetch, cache, or transform --
those remain the channel's job. They locate the observation the channel would
return and report it together with its timestamp.

Declared semantics per channel
------------------------------
``funding_rate``    INSTANT. A settlement print is complete at its settlement
                    time and immediately public.
``etf_net_flow``    INTERVAL of one day, plus a one-day publication lag. Day D's
                    total is neither complete nor reported until D+1. The
                    channel already applies this lag internally; declaring it
                    here lets the store verify rather than assume it.
``coinbase_close``  INTERVAL of one hour. The series is stamped with bar OPEN
                    times while the value is the bar's CLOSE, so the
                    observation is not complete until the bar ends. Declaring
                    the interval is what makes a read at 10:30 of the 10:00
                    bar's close a detected leak rather than a silent one.
``btc_thrust``      INTERVAL of one hour, same reason: thrust at index i is
                    computed from ``closes[i]`` while ``times_ms[i]`` is the
                    bar's open.
``xs_in_top_k``     INTERVAL of one hour, same panel-bar convention.
"""

from __future__ import annotations

import bisect
from datetime import datetime, timedelta, timezone

from research.data.btc_reference import BtcThrustSeries
from research.data.coinbase_prices import CoinbasePriceSeries
from research.data.etf_flows import EtfFlowSeries
from research.data.funding_rates import FundingSeries
from research.data.xs_rank import RankSeries
from research.features.spec import FeatureKind, FeatureSpec
from research.features.store import Observation, Resolver

_HOUR = timedelta(hours=1)
_DAY = timedelta(days=1)


def _at_or_before(times_ms: tuple[int, ...], ts: datetime) -> int | None:
    """Return the index of the latest timestamp at or before ``ts``.

    Args:
        times_ms: Ascending epoch-millisecond timestamps.
        ts: Timezone-aware UTC query instant.

    Returns:
        Index into ``times_ms``, or None if ``ts`` precedes the series.

    Raises:
        ValueError: If ``ts`` is naive.
    """
    if ts.tzinfo is None:
        raise ValueError("query instant must be timezone-aware")
    pos = bisect.bisect_right(times_ms, int(ts.timestamp() * 1000))
    return pos - 1 if pos else None


def _utc(ms: int) -> datetime:
    """Convert epoch milliseconds to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

FUNDING_RATE = FeatureSpec(
    name="funding_rate",
    description="Binance perpetual funding rate at the latest settlement",
    kind=FeatureKind.INSTANT,
    publication_lag=timedelta(0),
    unit="fraction per 8h",
    source="research.data.funding_rates",
)

ETF_NET_FLOW = FeatureSpec(
    name="etf_net_flow",
    description="Daily spot-ETF net flow, reported one day in arrears",
    kind=FeatureKind.INTERVAL,
    interval=_DAY,
    publication_lag=_DAY,
    unit="US$ millions",
    source="research.data.etf_flows",
)

COINBASE_CLOSE = FeatureSpec(
    name="coinbase_close",
    description="Coinbase 1H bar close (complete only at the bar's end)",
    kind=FeatureKind.INTERVAL,
    interval=_HOUR,
    publication_lag=timedelta(0),
    unit="USD",
    source="research.data.coinbase_prices",
)

BTC_THRUST = FeatureSpec(
    name="btc_thrust",
    description="BTC trailing return over the lookback window, from 1H closes",
    kind=FeatureKind.INTERVAL,
    interval=_HOUR,
    publication_lag=timedelta(0),
    unit="fraction",
    source="research.data.btc_reference",
)

XS_IN_TOP_K = FeatureSpec(
    name="xs_in_top_k",
    description="Whether the symbol ranked in the top K by cross-sectional momentum",
    kind=FeatureKind.INTERVAL,
    interval=_HOUR,
    publication_lag=timedelta(0),
    unit="bool",
    source="research.data.xs_rank",
)


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def funding_resolver(series: FundingSeries) -> Resolver:
    """Build a resolver over a funding series.

    Args:
        series: The funding history to read.

    Returns:
        A Resolver returning the latest settlement at or before the instant.
    """

    def resolve(symbol: str | None, ts: datetime) -> Observation | None:
        idx = _at_or_before(series.times_ms, ts)
        if idx is None:
            return None
        return Observation(value=float(series.rates[idx]), observed_at=_utc(series.times_ms[idx]))

    return resolve


def etf_flow_resolver(series: EtfFlowSeries) -> Resolver:
    """Build a resolver over an ETF net-flow series.

    Args:
        series: The flow history to read.

    Returns:
        A Resolver returning the latest flow day at or before the instant. The
        one-day interval and one-day publication lag are applied by the store
        from ETF_NET_FLOW, not here.
    """

    def resolve(symbol: str | None, ts: datetime) -> Observation | None:
        idx = _at_or_before(series.dates_ms, ts)
        if idx is None:
            return None
        return Observation(value=float(series.flows[idx]), observed_at=_utc(series.dates_ms[idx]))

    return resolve


def coinbase_close_resolver(series: CoinbasePriceSeries) -> Resolver:
    """Build a resolver over a Coinbase price series.

    Args:
        series: The price history to read.

    Returns:
        A Resolver returning the latest bar at or before the instant, stamped
        with the bar's OPEN time. Because COINBASE_CLOSE declares a one-hour
        interval, the store will reject that bar until it has closed.
    """

    def resolve(symbol: str | None, ts: datetime) -> Observation | None:
        idx = _at_or_before(series.times_ms, ts)
        if idx is None:
            return None
        return Observation(value=float(series.closes[idx]), observed_at=_utc(series.times_ms[idx]))

    return resolve


def btc_thrust_resolver(series: BtcThrustSeries) -> Resolver:
    """Build a resolver over a BTC thrust series.

    Args:
        series: The thrust history to read.

    Returns:
        A Resolver returning the latest non-NaN thrust at or before the instant,
        stamped with the bar's open time.
    """

    def resolve(symbol: str | None, ts: datetime) -> Observation | None:
        idx = _at_or_before(series.times_ms, ts)
        if idx is None:
            return None
        value = series.thrust[idx]
        if value != value:  # NaN during warmup
            return None
        return Observation(value=float(value), observed_at=_utc(series.times_ms[idx]))

    return resolve


def xs_rank_resolver(series: RankSeries) -> Resolver:
    """Build a resolver over a cross-sectional rank series.

    Args:
        series: The rank history to read.

    Returns:
        A Resolver returning the latest top-K membership at or before the
        instant, stamped with the panel bar's open time.
    """

    def resolve(symbol: str | None, ts: datetime) -> Observation | None:
        idx = _at_or_before(series.times_ms, ts)
        if idx is None:
            return None
        return Observation(value=bool(series.in_top_k[idx]), observed_at=_utc(series.times_ms[idx]))

    return resolve
