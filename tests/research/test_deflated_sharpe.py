"""Gating tests for the Deflated Sharpe Ratio module.

This module is the non-negotiable statistical floor for the PARAVANT promotion
gate (DEC-2026-06-04-008). A miscalibrated DSR that LOOKS rigorous is worse than
no DSR -- it manufactures false confidence exactly when capital is risked. These
tests therefore validate the math from FIRST PRINCIPLES (closed-form analytical
reductions), not against remembered "paper values" that could be misquoted.

The single most important test is ``test_psr_normal_reduction_is_exact``: under
normality the PSR collapses to a closed form, and we assert the implementation
reproduces it to ~1e-12. Per the spec's execution-gate requirement
(RETROSPECTIVE_DSR_SPEC Section 10), the retrospective runner must refuse to run
on real data unless these tests pass.
"""
from __future__ import annotations

import math
import random

import pytest

from research.validation.deflated_sharpe import (
    DeflatedSharpeResult,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    normal_cdf,
    normal_ppf,
    probabilistic_sharpe_ratio,
    sample_kurtosis,
    sample_sharpe,
    sample_skewness,
)


# ---------------------------------------------------------------------------
# normal_cdf -- exact via math.erf
# ---------------------------------------------------------------------------


class TestNormalCdf:
    def test_center(self) -> None:
        assert normal_cdf(0.0) == pytest.approx(0.5, abs=1e-12)

    def test_known_quantiles(self) -> None:
        # 1.959963985 is the 97.5th percentile of the standard normal.
        assert normal_cdf(1.959963984540054) == pytest.approx(0.975, abs=1e-9)
        assert normal_cdf(-1.959963984540054) == pytest.approx(0.025, abs=1e-9)

    def test_symmetry(self) -> None:
        for x in (0.3, 1.0, 2.5, 4.0):
            assert normal_cdf(x) + normal_cdf(-x) == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# normal_ppf -- Acklam inverse, must round-trip with normal_cdf
# ---------------------------------------------------------------------------


class TestNormalPpf:
    def test_center(self) -> None:
        assert normal_ppf(0.5) == pytest.approx(0.0, abs=1e-9)

    def test_known_quantiles(self) -> None:
        assert normal_ppf(0.975) == pytest.approx(1.959963984540054, abs=1e-6)
        assert normal_ppf(0.025) == pytest.approx(-1.959963984540054, abs=1e-6)

    def test_round_trip_against_cdf(self) -> None:
        # The inverse must invert: cdf(ppf(p)) == p across the whole range.
        for p in (0.001, 0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99, 0.999):
            assert normal_cdf(normal_ppf(p)) == pytest.approx(p, abs=1e-7)

    def test_rejects_out_of_range(self) -> None:
        for bad in (0.0, 1.0, -0.1, 1.1):
            with pytest.raises(ValueError):
                normal_ppf(bad)


# ---------------------------------------------------------------------------
# Moment helpers -- the KURTOSIS CONVENTION is the critical footgun
# ---------------------------------------------------------------------------


class TestMomentConventions:
    def test_kurtosis_is_raw_not_excess(self) -> None:
        """A (near-)normal sample must give RAW kurtosis ~3.0, NOT ~0.0.

        This is THE guard against the scipy Fisher/excess footgun: if kurtosis
        were accidentally excess, this assertion fails loudly.
        """
        rng = random.Random(20260605)
        normal_sample = [rng.gauss(0.0, 1.0) for _ in range(200_000)]
        k = sample_kurtosis(normal_sample)
        assert k == pytest.approx(3.0, abs=0.1)
        # And it must be nowhere near the excess-kurtosis value of 0.
        assert abs(k) > 2.0

    def test_skewness_symmetric_is_zero(self) -> None:
        rng = random.Random(11)
        normal_sample = [rng.gauss(0.0, 1.0) for _ in range(200_000)]
        assert sample_skewness(normal_sample) == pytest.approx(0.0, abs=0.05)

    def test_skewness_positive_for_right_skewed(self) -> None:
        # Exponential-like data is right-skewed (positive skew).
        rng = random.Random(7)
        skewed = [rng.expovariate(1.0) for _ in range(100_000)]
        assert sample_skewness(skewed) > 1.0

    def test_sample_sharpe_matches_definition(self) -> None:
        returns = [0.02, -0.01, 0.03, 0.00, 0.015, -0.005]
        n = len(returns)
        mean = sum(returns) / n
        var = sum((r - mean) ** 2 for r in returns) / (n - 1)
        expected = mean / math.sqrt(var)
        assert sample_sharpe(returns) == pytest.approx(expected, abs=1e-12)

    def test_degenerate_inputs_are_safe(self) -> None:
        assert sample_sharpe([0.01]) == 0.0
        assert sample_sharpe([0.01, 0.01, 0.01]) == 0.0  # zero variance
        assert sample_kurtosis([0.01, 0.02]) == 3.0  # too few -> normal default
        assert sample_skewness([0.01, 0.02]) == 0.0


# ---------------------------------------------------------------------------
# PSR -- the closed-form analytical reduction (the keystone gate)
# ---------------------------------------------------------------------------


def _psr_normal_closed_form(sr: float, n: int) -> float:
    """PSR(benchmark=0) under normality, computed directly from the formula.

    For skew=0, kurt=3 the variance term is ``1 + 0.5 * SR**2`` (the classic
    Lo 2002 result), so PSR = Phi( SR * sqrt(n-1) / sqrt(1 + 0.5*SR**2) ).
    """
    z = sr * math.sqrt(n - 1) / math.sqrt(1.0 + 0.5 * sr**2)
    return normal_cdf(z)


class TestProbabilisticSharpeRatio:
    def test_psr_normal_reduction_is_exact(self) -> None:
        """KEYSTONE: PSR must equal the closed-form normal reduction exactly."""
        for sr in (0.05, 0.1, 0.25, 0.5, 1.0):
            for n in (20, 50, 100, 500):
                got = probabilistic_sharpe_ratio(
                    observed_sharpe=sr,
                    benchmark_sharpe=0.0,
                    n_returns=n,
                    skewness=0.0,
                    kurtosis=3.0,
                )
                want = _psr_normal_closed_form(sr, n)
                assert got == pytest.approx(want, abs=1e-12)

    def test_psr_at_benchmark_is_half(self) -> None:
        # When observed == benchmark the numerator is 0 -> Phi(0) = 0.5.
        psr = probabilistic_sharpe_ratio(
            observed_sharpe=0.4,
            benchmark_sharpe=0.4,
            n_returns=50,
            skewness=-0.2,
            kurtosis=4.0,
        )
        assert psr == pytest.approx(0.5, abs=1e-12)

    def test_psr_monotonic_in_observed_sharpe(self) -> None:
        base = dict(benchmark_sharpe=0.0, n_returns=60, skewness=0.0, kurtosis=3.0)
        lo = probabilistic_sharpe_ratio(observed_sharpe=0.1, **base)
        hi = probabilistic_sharpe_ratio(observed_sharpe=0.5, **base)
        assert hi > lo

    def test_psr_monotonic_in_sample_size(self) -> None:
        base = dict(
            observed_sharpe=0.3, benchmark_sharpe=0.0, skewness=0.0, kurtosis=3.0
        )
        small = probabilistic_sharpe_ratio(n_returns=20, **base)
        large = probabilistic_sharpe_ratio(n_returns=400, **base)
        assert large > small

    def test_negative_skew_lowers_psr(self) -> None:
        """Negative skew (fat left tail) must REDUCE confidence vs symmetric."""
        base = dict(observed_sharpe=0.5, benchmark_sharpe=0.0, n_returns=60)
        symmetric = probabilistic_sharpe_ratio(skewness=0.0, kurtosis=3.0, **base)
        left_tailed = probabilistic_sharpe_ratio(skewness=-1.0, kurtosis=6.0, **base)
        assert left_tailed < symmetric

    def test_variance_guard_catches_excess_kurtosis_footgun(self) -> None:
        """The variance guard fires on the excess-kurtosis (Fisher) footgun.

        For any VALID distribution kurtosis >= 1 + skewness**2, which makes the
        variance term ``1 - skew*SR + ((kurt-1)/4)*SR**2`` provably >= 0 for
        moment-consistent inputs. So the guard cannot fire on real data -- its
        real job is to catch the mistake of passing EXCESS kurtosis (normal=0)
        where RAW kurtosis (normal=3) is required. Excess kurtosis near 0 at a
        high Sharpe drives the term negative, and the guard must raise rather
        than let math.sqrt crash or emit a garbage z-score.
        """
        # kurt=0.0 is the excess-kurtosis value for a normal -> the footgun.
        # variance_term = 1 - 0 + ((0 - 1)/4) * 3**2 = 1 - 2.25 = -1.25 < 0.
        with pytest.raises(ValueError, match="variance term is non-positive"):
            probabilistic_sharpe_ratio(
                observed_sharpe=3.0,
                benchmark_sharpe=0.0,
                n_returns=30,
                skewness=0.0,
                kurtosis=0.0,  # WRONG: excess kurtosis passed where raw expected
            )

    def test_variance_term_safe_for_valid_extreme_moments(self) -> None:
        """For moment-consistent inputs the term stays positive even at extremes.

        kurtosis >= 1 + skewness**2 is a hard mathematical bound; with raw
        kurtosis respecting it, the PSR is always well-defined. This documents
        that the guard does NOT reject legitimate fat-tailed crypto returns.
        """
        # Strong negative skew with a consistent (large) raw kurtosis.
        psr = probabilistic_sharpe_ratio(
            observed_sharpe=1.0,
            benchmark_sharpe=0.0,
            n_returns=40,
            skewness=-1.5,
            kurtosis=8.0,  # >= 1 + (-1.5)**2 = 3.25, so valid
        )
        assert 0.0 < psr < 1.0

    def test_rejects_tiny_sample(self) -> None:
        with pytest.raises(ValueError, match="n_returns >= 2"):
            probabilistic_sharpe_ratio(
                observed_sharpe=0.3,
                benchmark_sharpe=0.0,
                n_returns=1,
                skewness=0.0,
                kurtosis=3.0,
            )


# ---------------------------------------------------------------------------
# expected_max_sharpe -- selection-bias benchmark
# ---------------------------------------------------------------------------


class TestExpectedMaxSharpe:
    def test_single_trial_is_zero(self) -> None:
        # With one trial there is no selection bias.
        assert expected_max_sharpe(variance_sr=0.01, n_trials=1) == 0.0

    def test_monotonic_increasing_in_trials(self) -> None:
        v = 0.01
        prev = expected_max_sharpe(v, 2)
        for k in (5, 20, 115, 500, 2000):
            cur = expected_max_sharpe(v, k)
            assert cur > prev
            prev = cur

    def test_scales_with_sqrt_variance(self) -> None:
        # Doubling variance scales the benchmark by sqrt(2).
        a = expected_max_sharpe(variance_sr=0.01, n_trials=100)
        b = expected_max_sharpe(variance_sr=0.04, n_trials=100)  # 4x variance
        assert b == pytest.approx(2.0 * a, rel=1e-9)

    def test_zero_variance_gives_zero_benchmark(self) -> None:
        assert expected_max_sharpe(variance_sr=0.0, n_trials=500) == 0.0

    def test_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            expected_max_sharpe(variance_sr=0.01, n_trials=0)
        with pytest.raises(ValueError):
            expected_max_sharpe(variance_sr=-0.01, n_trials=100)


# ---------------------------------------------------------------------------
# deflated_sharpe_ratio -- the full instrument
# ---------------------------------------------------------------------------


class TestDeflatedSharpeRatio:
    def test_returns_result_dataclass(self) -> None:
        res = deflated_sharpe_ratio(
            observed_sharpe=0.5,
            variance_sr=0.01,
            n_trials=115,
            n_returns=50,
            skewness=-0.1,
            kurtosis=3.5,
        )
        assert isinstance(res, DeflatedSharpeResult)
        assert res.dsr_p_value == pytest.approx(1.0 - res.dsr, abs=1e-12)
        assert 0.0 <= res.dsr <= 1.0

    def test_more_trials_lowers_dsr(self) -> None:
        """The honesty property: larger effective K => stronger deflation.

        This is the multi-K sensitivity the spec requires. A strategy can be
        Tier A at K=115 yet fail at K=2000 -- that fragility IS the finding.
        """
        common = dict(
            observed_sharpe=0.45,
            variance_sr=0.01,
            n_returns=50,
            skewness=-0.1,
            kurtosis=3.5,
        )
        dsr_low_k = deflated_sharpe_ratio(n_trials=115, **common)
        dsr_high_k = deflated_sharpe_ratio(n_trials=2000, **common)
        assert dsr_high_k.dsr < dsr_low_k.dsr
        # p-value moves the opposite way (higher K -> higher p -> less confident).
        assert dsr_high_k.dsr_p_value > dsr_low_k.dsr_p_value

    def test_higher_observed_sharpe_raises_dsr(self) -> None:
        common = dict(
            variance_sr=0.01,
            n_trials=115,
            n_returns=50,
            skewness=0.0,
            kurtosis=3.0,
        )
        weak = deflated_sharpe_ratio(observed_sharpe=0.15, **common)
        strong = deflated_sharpe_ratio(observed_sharpe=0.6, **common)
        assert strong.dsr > weak.dsr

    def test_single_trial_equals_plain_psr(self) -> None:
        # With K=1 the deflation benchmark is 0, so DSR == PSR(benchmark=0).
        res = deflated_sharpe_ratio(
            observed_sharpe=0.4,
            variance_sr=0.02,
            n_trials=1,
            n_returns=40,
            skewness=0.0,
            kurtosis=3.0,
        )
        plain = probabilistic_sharpe_ratio(
            observed_sharpe=0.4,
            benchmark_sharpe=0.0,
            n_returns=40,
            skewness=0.0,
            kurtosis=3.0,
        )
        assert res.dsr == pytest.approx(plain, abs=1e-12)


# ---------------------------------------------------------------------------
# Optional cross-check against scipy when present (not required to pass)
# ---------------------------------------------------------------------------


class TestScipyCrossCheck:
    def test_cdf_ppf_match_scipy_if_available(self) -> None:
        scipy_stats = pytest.importorskip("scipy.stats")
        for x in (-2.0, -0.5, 0.0, 1.0, 2.5):
            assert normal_cdf(x) == pytest.approx(
                float(scipy_stats.norm.cdf(x)), abs=1e-10
            )
        for p in (0.05, 0.5, 0.95):
            assert normal_ppf(p) == pytest.approx(
                float(scipy_stats.norm.ppf(p)), abs=1e-6
            )
