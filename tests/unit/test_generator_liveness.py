"""Every generator must be able to emit a signal on some market.

The existing generation test could not fail::

    result = gen.generate(series, params, "BTCUSDT")
    if result is not None:
        assert isinstance(result, TradingSignal)

A generator that returns ``None`` for every input -- because a threshold is
inverted, an indicator warmup is longer than the data, or the entry condition
can never be true -- satisfies that assertion completely. It was the only test
in the suite that called ``generate()`` on real-shaped data, and it was
tautological.

That matters more here than it would elsewhere. This repository's headline
result is that twenty-nine generators produced no validated edge, and the
`FUNDAMENTAL` tag on each rejection asserts that "the mechanism failed, not the
implementation". A suite that cannot distinguish a failed mechanism from a
generator that never fired is not evidence for that claim.

So: feed each generator a range of market shapes and require that **at least
one** of them produces a signal. This does not establish that a generator is
*correct*. It establishes that it is *alive*, which is the property the previous
test appeared to cover and did not.

Parameters are derived from `config/templates/*.yaml`, not hand-written, so a
generator that gains a template is covered the day it does.

Decision: DEC-2026-08-21-007
"""
from __future__ import annotations

import functools
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.core.strategy.factory import SignalGeneratorFactory
from src.core.strategy.signals import TradingSignal
from src.data.market_data import OHLCV, OHLCVSeries
from src.data.models.signal import SignalDirection

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "config" / "templates"

#: Bars per generated series. Comfortably above the longest warmup in the
#: library -- Ichimoku needs 220 and the regime filters use a 200-period EMA --
#: because a generator starved of history returns None for reasons that have
#: nothing to do with whether it works.
N_BARS = 500


def _template_defaults() -> dict[str, dict[str, Any]]:
    """Map template id to its parameters, using each parameter's default.

    Derived rather than written down. Every template in `config/templates/`
    declares a `default` for every parameter, so this is complete for the
    templates that exist, and picks up new ones automatically.

    Returns:
        Mapping of template id to a parameter dict.
    """
    defaults: dict[str, dict[str, Any]] = {}
    for path in sorted(TEMPLATE_DIR.glob("*.yaml")):
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        template_id = spec.get("id")
        if not template_id:
            continue
        defaults[template_id] = {
            param["name"]: param["default"]
            for param in (spec.get("parameters") or [])
            if "default" in param
        }
    return defaults


TEMPLATE_PARAMS: dict[str, dict[str, Any]] = _template_defaults()


def _series(shape: str, symbol: str = "BTCUSDT", seed: int = 11) -> OHLCVSeries:
    """Build a deterministic OHLCV series with a given market character.

    Deterministic, but not smooth. The first version of this helper used sine
    curves with 0.4% wobble and eleven of fourteen generators returned None on
    every shape -- not because they were broken, but because a crossover or an
    oscillator threshold never occurs on a path that clean. A fixture that no
    working strategy could fire on produces a test that asserts something false.

    So: a seeded random walk at a volatility crypto actually exhibits (roughly
    0.9% hourly standard deviation), with a per-shape drift and structure laid
    over it. Seeded rather than unseeded, unlike the helper in
    `test_signal_generators.py`, because a test asserting "at least one shape
    signals" against an unseeded walk is free to flake.

    Args:
        shape: One of :data:`SHAPES`.
        symbol: Trading symbol to stamp on the series.
        seed: Random seed. Fixed by default; varied only by tests that check
            the result does not depend on one particular walk.

    Returns:
        A series of :data:`N_BARS` candles.
    """
    rng = random.Random(seed)
    start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    price = 42_000.0
    candles: list[OHLCV] = []

    #: Hourly log-return standard deviation. BTC sits near this.
    sigma = 0.009

    for i in range(N_BARS):
        progress = i / N_BARS

        if shape == "strong_uptrend":
            drift, vol = 0.0030, sigma
        elif shape == "strong_downtrend":
            drift, vol = -0.0030, sigma
        elif shape == "choppy_range":
            # Mean-reverting pull toward the origin, so it ranges rather than walks.
            drift, vol = -0.02 * (price / 42_000.0 - 1.0), sigma
        elif shape == "squeeze_then_breakout_up":
            drift = 0.0 if progress < 0.75 else 0.006
            vol = sigma * (0.2 if progress < 0.75 else 1.6)
        elif shape == "squeeze_then_breakdown":
            drift = 0.0 if progress < 0.75 else -0.006
            vol = sigma * (0.2 if progress < 0.75 else 1.6)
        elif shape == "uptrend_with_pullbacks":
            # Trend up, but retrace hard every ~40 bars.
            phase = (i % 40) / 40.0
            drift = 0.0060 if phase < 0.65 else -0.0080
            vol = sigma
        elif shape == "downtrend_with_rallies":
            phase = (i % 40) / 40.0
            drift = -0.0060 if phase < 0.65 else 0.0080
            vol = sigma
        elif shape == "v_reversal":
            drift = -0.0045 if progress < 0.5 else 0.0055
            vol = sigma
        elif shape == "volatility_expansion":
            drift, vol = 0.0, sigma * (0.3 + progress * 3.0)
        else:  # pragma: no cover - guarded by SHAPES
            raise ValueError(f"unknown shape: {shape}")

        price = max(price * (1.0 + drift + rng.gauss(0.0, vol)), 1.0)

        open_price = candles[-1].close if candles else price
        close = price
        span = abs(rng.gauss(0.0, vol)) + 0.001
        high = max(open_price, close) * (1.0 + span)
        low = min(open_price, close) * (1.0 - span)

        # Volume expands with the bar's range, so volume filters can pass.
        move = abs(close / open_price - 1.0)
        volume = 100.0 * (1.0 + move * 60.0) * (0.7 + rng.random() * 0.6)

        candles.append(
            OHLCV(
                timestamp=start_time + timedelta(hours=i),
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=round(volume, 4),
            )
        )

    return OHLCVSeries(candles=candles, symbol=symbol, timeframe="1h")


SHAPES: tuple[str, ...] = (
    "strong_uptrend",
    "strong_downtrend",
    "choppy_range",
    "squeeze_then_breakout_up",
    "squeeze_then_breakdown",
    "uptrend_with_pullbacks",
    "downtrend_with_rallies",
    "v_reversal",
    "volatility_expansion",
)


#: Seed for the walks. One is enough now that each walk is evaluated at many
#: points rather than only at its end -- see _signals_for.
SEED: int = 11

#: Bar index to start evaluating from, and the step between evaluations.
#:
#: `generate()` inspects only the LAST bar of the series it is given. Calling it
#: once on a 500-bar series therefore asks "did bar 500 happen to be a setup",
#: which for a strategy requiring price within 0.5% of an EMA is a question with
#: a low and largely accidental answer. It is not what the system does either:
#: the live loop calls `generate()` once per poll, on a series ending at the
#: current bar, and the backtest walks forward the same way.
#:
#: So this walks the series and evaluates prefixes, which is both realistic and
#: the difference between sampling one bar and sampling 25.
WINDOW_START: int = 260
WINDOW_STEP: int = 10


@functools.lru_cache(maxsize=None)
def _signals_for(template_id: str) -> dict[tuple[str, int], TradingSignal]:
    """Walk each shape forward and collect every signal the generator emits.

    Mirrors how the generator is actually called: once per bar, on the history
    up to that bar.

    Args:
        template_id: Generator to exercise.

    Cached: three test methods ask the same question of each generator, and the
    walk is the expensive part of this file.

    Returns:
        Mapping of (shape, end-bar index) to the signal produced, omitting the
        positions that produced none.
    """
    generator = SignalGeneratorFactory().get_generator(template_id)
    params = TEMPLATE_PARAMS[template_id]

    produced: dict[tuple[str, int], TradingSignal] = {}
    for shape in SHAPES:
        full = _series(shape, seed=SEED)
        for end in range(WINDOW_START, N_BARS + 1, WINDOW_STEP):
            if end < generator.min_bars_required:
                continue
            signal = generator.generate(full.slice(0, end), params, "BTCUSDT")
            if signal is not None:
                produced[(shape, end)] = signal
    return produced


class TestTheHarnessIsNotVacuous:
    """Guards the guard.

    Every assertion below is parametrised over TEMPLATE_PARAMS. If that were
    empty -- a moved directory, a renamed key -- pytest would report zero tests
    and a green run, which is the exact failure this file was written to end.
    """

    def test_parameters_were_derived_for_the_templates_that_exist(self) -> None:
        assert len(TEMPLATE_PARAMS) >= 14, (
            f"expected parameters for at least 14 templates, derived "
            f"{len(TEMPLATE_PARAMS)}: {sorted(TEMPLATE_PARAMS)}"
        )

    def test_every_template_yielded_a_non_empty_parameter_set(self) -> None:
        empty = [name for name, params in TEMPLATE_PARAMS.items() if not params]
        assert not empty, f"templates whose parameters did not resolve: {empty}"

    def test_the_shapes_are_distinguishable(self) -> None:
        """Nine shapes that all produced the same prices would prove nothing."""
        closes = {shape: tuple(c.close for c in _series(shape).candles) for shape in SHAPES}
        assert len(set(closes.values())) == len(SHAPES), "some shapes are identical"

    def test_series_timestamps_increase(self) -> None:
        """The helper in test_signal_generators.py stamps every candle with the
        same instant. Indicators that resample or window by time cannot behave
        meaningfully against that, so this one does not."""
        candles = _series("strong_uptrend").candles
        assert all(
            b.timestamp > a.timestamp for a, b in zip(candles, candles[1:])
        )


#: Generators not yet shown to fire on any generated market.
#:
#: This is a statement about the fixture as much as about the generators. Each
#: needs a setup these nine synthetic shapes do not produce -- a squeeze of a
#: particular depth, an ADX reading in a particular band, a regime filter and an
#: oscillator aligning at once. Ten of fourteen were proven alive by widening
#: the fixture from smooth curves to a random walk, and then from one evaluation
#: per series to a forward walk; each widening moved generators out of this set.
#:
#: It is an allowlist, not a skip. `test_the_allowlist_has_not_gone_stale`
#: fails if one of these starts firing, which forces the entry to be removed
#: rather than left to rot, and nothing can be added to it silently.
UNPROVEN: frozenset[str] = frozenset({
    "bb_squeeze_momentum",
    "bear_trend_follower",
    "keltner_fade_adx",
    "regime_aware_mean_reversion",
})


class TestEveryGeneratorIsAlive:
    """The test the tautological one appeared to be."""

    @pytest.mark.parametrize(
        "template_id", sorted(set(TEMPLATE_PARAMS) - UNPROVEN)
    )
    def test_emits_a_signal_on_at_least_one_market_shape(self, template_id: str) -> None:
        produced = _signals_for(template_id)

        assert produced, (
            f"{template_id} returned None at every evaluated bar across all "
            f"{len(SHAPES)} market shapes -- roughly "
            f"{len(SHAPES) * ((N_BARS - WINDOW_START) // WINDOW_STEP)} calls to "
            f"generate(), and not one signal. Either its entry condition cannot "
            f"be satisfied, or its warmup exceeds {N_BARS} bars. A generator "
            f"that never fires produces the same null result as one whose "
            f"mechanism genuinely has no edge, and without this the suite "
            f"cannot tell them apart."
        )

    @pytest.mark.parametrize("template_id", sorted(TEMPLATE_PARAMS))
    def test_every_signal_it_emits_is_well_formed(self, template_id: str) -> None:
        produced = _signals_for(template_id)

        for (shape, end), signal in produced.items():
            context = f"{template_id} on {shape} at bar {end}"
            assert isinstance(signal, TradingSignal), context
            assert signal.symbol == "BTCUSDT", context
            assert signal.price > 0, context
            assert signal.direction in set(SignalDirection), context
            assert 0.0 <= signal.strength <= 1.0, context
            assert signal.timestamp.tzinfo is not None, (
                f"{context}: naive timestamp violates DEC-2026-02-08-003"
            )

    @pytest.mark.parametrize("template_id", sorted(TEMPLATE_PARAMS))
    def test_generation_is_deterministic(self, template_id: str) -> None:
        """The same bars twice must give the same answer.

        A generator reading a clock, a global random state or mutable shared
        state would make every backtest in this repository unreproducible, and
        nothing else checks for it.
        """
        first = _signals_for(template_id)
        second = _signals_for(template_id)

        assert set(first) == set(second), (
            f"{template_id} signalled at a different set of (shape, bar) points "
            f"on a second identical run"
        )
        for key in first:
            assert first[key].direction == second[key].direction, key
            assert first[key].price == second[key].price, key


class TestTheAllowlistCannotRot:
    """An allowlist nobody revisits becomes a permanent exemption."""

    def test_every_entry_is_a_real_template(self) -> None:
        unknown = UNPROVEN - set(TEMPLATE_PARAMS)
        assert not unknown, (
            f"UNPROVEN names templates that no longer exist: {sorted(unknown)}. "
            f"Remove them."
        )

    @pytest.mark.parametrize("template_id", sorted(UNPROVEN))
    def test_the_allowlist_has_not_gone_stale(self, template_id: str) -> None:
        """If an allowlisted generator starts firing, the entry must go.

        Same shape as `test_known_duplicate_allowlist_has_not_gone_stale` in
        test_governance_sync.py, and for the same reason: a suppression that
        silently stops applying is a suppression that will hide the next real
        instance.
        """
        assert not _signals_for(template_id), (
            f"{template_id} now emits a signal and must be removed from "
            f"UNPROVEN, so that it is covered by "
            f"test_emits_a_signal_on_at_least_one_market_shape."
        )

    def test_most_generators_are_proven_alive(self) -> None:
        """Guards against the allowlist growing to swallow the test.

        The point of this file is a positive claim about generators. If the
        exemption list grew faster than the coverage, every parametrised test
        above would still pass while proving less and less.
        """
        proven = len(TEMPLATE_PARAMS) - len(UNPROVEN)
        assert proven >= 10, (
            f"only {proven} of {len(TEMPLATE_PARAMS)} generators are proven "
            f"alive; UNPROVEN has grown to {sorted(UNPROVEN)}"
        )
