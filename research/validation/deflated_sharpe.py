"""Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).

The DSR corrects an observed Sharpe ratio for three biases that make naive
Sharpe ratios systematically overstate true edge:

1. Selection bias from testing many strategy configurations (the effective
   number of trials, K). Testing many things and keeping the winner inflates
   the winner's apparent Sharpe.
2. Non-normality of returns (skewness and kurtosis), which the classic Sharpe
   ratio ignores.
3. Small sample size (few independent return observations).

It returns the probability that the strategy's TRUE Sharpe ratio exceeds the
maximum Sharpe you would expect to observe by pure luck across K trials. This
module is the non-negotiable statistical floor for the PARAVANT promotion gate
(DEC-2026-06-04-008): a strategy with ``dsr_p_value >= 0.3`` may NOT deploy at
any capital allocation.

Design notes (addressing the 2026-06-05 external review of the spec):

- FREQUENCY / FRAMING. We compute the DSR on PER-TRADE ("per-bet") returns,
  NOT a reconstructed daily equity curve. This is a deliberate, documented
  choice for three reasons: (a) the existing live promotion gate already
  standardises on per-trade Sharpe (`scripts/validation_report._sharpe_per_trade`,
  DEC-2026-05-27-004) and a second, divergent daily-Sharpe definition would
  create two inconsistent "Sharpe" numbers in one system; (b) per-trade returns
  are closer to the IID assumption the PSR formula requires than daily returns
  are -- consecutive daily returns WHILE HOLDING one multi-day position are
  serially correlated (same position, same direction), which violates IID more
  badly than treating each independent entry/exit as one bet; (c) it avoids a
  mark-to-market dependency on OHLCV during holding periods. The cost: a
  per-trade Sharpe is not annualised and must not be compared naively against
  an annualised benchmark. Everything in this module stays in consistent
  per-trade units -- the observed Sharpe, the expected-maximum-Sharpe benchmark,
  and the cross-sectional variance are all per-trade. See the PRD Section 8.5
  rationale and DEC-2026-06-04-002.

- UNITS CONSISTENCY. The expected-maximum-Sharpe benchmark (`expected_max_sharpe`)
  is built from `sqrt(variance_sr) * [inverse-normal terms]`, where
  `variance_sr` is the cross-sectional variance of the per-trade Sharpe
  estimates across the K trials. Because it is scaled by that per-trade
  variance, the benchmark is in the same per-trade Sharpe units as the observed
  Sharpe. The earlier spec used a bare ``sqrt(2*ln(K))`` term whose units did
  not match the observed per-trade Sharpe; that is corrected here by using the
  full Bailey-Lopez de Prado estimator with the inverse-normal CDF.

- VARIANCE GUARD. The Sharpe-estimator variance term
  ``1 - skew*SR + ((kurt-1)/4)*SR**2`` is guarded: `probabilistic_sharpe_ratio`
  raises ``ValueError`` if it is non-positive rather than letting ``math.sqrt``
  crash or silently produce a garbage z-score. NOTE on what this actually
  protects against: for any VALID distribution, kurtosis >= 1 + skewness**2, and
  substituting that bound shows the term is >= ``(1 - skew*SR/2)**2 >= 0`` for
  moment-consistent inputs. So the term cannot go negative on real data -- the
  guard's true job is to catch the EXCESS-KURTOSIS FOOTGUN: if excess kurtosis
  (normal = 0) is mistakenly passed where raw kurtosis (normal = 3) is required,
  the term can go negative at a high Sharpe, and the guard fires. It is a
  tripwire for the very bug the kurtosis convention below prevents.

- KURTOSIS CONVENTION. This module consumes RAW (non-excess) kurtosis: a normal
  distribution has kurtosis 3.0, not 0.0. `sample_kurtosis` returns raw
  kurtosis explicitly so the common ``scipy.stats.kurtosis`` Fisher/excess
  footgun (which defaults to excess) cannot silently corrupt every number.

- NO HEAVY DEPENDENCY. The normal CDF uses ``math.erf`` (exact, stdlib) and the
  inverse normal CDF uses Acklam's algorithm (pure Python, ~1.15e-9 accurate).
  A capital-gating instrument should not depend on a large library whose
  internals can drift across versions; pure stdlib is verifiable from first
  principles. Tests may optionally cross-check against scipy when it is present.

References:
    Bailey, D. and Lopez de Prado, M. (2014). "The Deflated Sharpe Ratio:
        Correcting for Selection Bias, Backtest Overfitting and Non-Normality."
        Journal of Portfolio Management, 40(5).
    Lo, A. (2002). "The Statistics of Sharpe Ratios." Financial Analysts
        Journal, 58(4). (Variance of the Sharpe estimator.)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Euler-Mascheroni constant, used in the expected-maximum-order-statistic term.
_EULER_MASCHERONI: float = 0.5772156649015329


@dataclass(frozen=True)
class DeflatedSharpeResult:
    """Result of a Deflated Sharpe Ratio computation.

    Attributes:
        dsr: The Deflated Sharpe Ratio = P(true Sharpe > expected-max-under-null).
            HIGH (towards 1.0) is GOOD: the observed Sharpe is unlikely to be a
            selection-bias artefact.
        dsr_p_value: ``1 - dsr``. LOW (towards 0.0) is GOOD. This is the value the
            PRD Tier floors are expressed against (DEC-2026-06-04-008):
            Tier A floor p < 0.2, Tier B floor p < 0.3, reject at p >= 0.5.
        observed_sharpe: The per-trade Sharpe ratio that was tested.
        expected_max_sharpe: The selection-bias benchmark the observed Sharpe was
            deflated against (per-trade units).
        n_returns: Number of per-trade return observations used.
        n_trials: Effective number of trials (K) used for the deflation.
        skewness: Sample skewness of the per-trade returns.
        kurtosis: RAW (non-excess) sample kurtosis of the per-trade returns.
        variance_sr: Cross-sectional variance of per-trade Sharpe estimates across
            the K trials, used to scale the benchmark into per-trade units.
    """

    dsr: float
    dsr_p_value: float
    observed_sharpe: float
    expected_max_sharpe: float
    n_returns: int
    n_trials: int
    skewness: float
    kurtosis: float
    variance_sr: float


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function (exact, stdlib).

    Uses the error function: ``Phi(x) = 0.5 * (1 + erf(x / sqrt(2)))``.

    Args:
        x: Point at which to evaluate the CDF.

    Returns:
        ``P(Z <= x)`` for a standard normal Z, in (0, 1).
    """
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_ppf(p: float) -> float:
    """Inverse standard normal CDF (quantile function) via Acklam's algorithm.

    Accurate to roughly 1.15e-9 absolute error over the open interval (0, 1),
    which is far tighter than any tolerance a p-value gate requires. Pure
    stdlib so the capital-gating math carries no external dependency.

    Args:
        p: Probability in the open interval (0, 1).

    Returns:
        The value ``z`` such that ``normal_cdf(z) == p``.

    Raises:
        ValueError: If ``p`` is not strictly inside (0, 1).
    """
    if not 0.0 < p < 1.0:
        raise ValueError(f"normal_ppf requires 0 < p < 1, got {p}")

    # Acklam rational-approximation coefficients.
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        # Lower tail.
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p <= p_high:
        # Central region.
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    # Upper tail.
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
    )


def sample_sharpe(returns: list[float]) -> float:
    """Per-trade Sharpe ratio = mean / sample-std of per-trade returns.

    Uses the SAMPLE standard deviation (ddof=1), matching the existing live
    promotion gate (``scripts/validation_report._sharpe_per_trade``,
    DEC-2026-05-27-004) so the research layer and the live gate cannot disagree
    on what "Sharpe" means.

    Args:
        returns: Per-trade percentage (or fractional) returns.

    Returns:
        The per-trade (non-annualised) Sharpe ratio. Returns 0.0 if fewer than
        two observations or if the standard deviation is zero.
    """
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    if variance <= 0.0:
        return 0.0
    return mean / math.sqrt(variance)


def sample_skewness(returns: list[float]) -> float:
    """Method-of-moments (population) skewness of a return series.

    Uses the population standard deviation (ddof=0) standardisation, matching
    the default convention of ``scipy.stats.skew`` (bias=True). A symmetric
    distribution has skewness 0.0.

    Args:
        returns: Per-trade returns.

    Returns:
        Sample skewness. Returns 0.0 if fewer than three observations or zero
        dispersion.
    """
    n = len(returns)
    if n < 3:
        return 0.0
    mean = sum(returns) / n
    m2 = sum((r - mean) ** 2 for r in returns) / n
    if m2 <= 0.0:
        return 0.0
    m3 = sum((r - mean) ** 3 for r in returns) / n
    return m3 / (m2**1.5)


def sample_kurtosis(returns: list[float]) -> float:
    """RAW (non-excess) method-of-moments kurtosis of a return series.

    RAW means a normal distribution returns 3.0, NOT 0.0. This is the
    convention the Bailey-Lopez de Prado variance term requires. It is stated
    explicitly here because ``scipy.stats.kurtosis`` returns EXCESS kurtosis
    (normal -> 0.0) by default (Fisher's definition); silently feeding excess
    kurtosis into the PSR formula would corrupt every number.

    Args:
        returns: Per-trade returns.

    Returns:
        Raw (non-excess) sample kurtosis. Returns 3.0 (the normal value) if
        fewer than four observations or zero dispersion, so a degenerate input
        does not spuriously alter the variance term.
    """
    n = len(returns)
    if n < 4:
        return 3.0
    mean = sum(returns) / n
    m2 = sum((r - mean) ** 2 for r in returns) / n
    if m2 <= 0.0:
        return 3.0
    m4 = sum((r - mean) ** 4 for r in returns) / n
    return m4 / (m2**2)


def probabilistic_sharpe_ratio(
    observed_sharpe: float,
    benchmark_sharpe: float,
    n_returns: int,
    skewness: float,
    kurtosis: float,
) -> float:
    """Probabilistic Sharpe Ratio: P(true Sharpe > ``benchmark_sharpe``).

    The PSR (Bailey & Lopez de Prado 2012/2014; Lo 2002 for the variance term)
    accounts for sample size and the non-normality of returns. All Sharpe inputs
    must be in the SAME per-observation (non-annualised) units.

    Formula::

        z   = (SR_hat - SR_benchmark) * sqrt(n - 1) / sqrt(V)
        V   = 1 - skew * SR_hat + ((kurt - 1) / 4) * SR_hat**2
        PSR = Phi(z)

    where ``kurt`` is RAW (non-excess) kurtosis.

    Args:
        observed_sharpe: The observed per-trade Sharpe ratio (SR_hat).
        benchmark_sharpe: The threshold Sharpe to test against (SR_benchmark).
            For a plain significance test this is 0.0; for the DSR it is the
            expected maximum Sharpe under the null (see `expected_max_sharpe`).
        n_returns: Number of per-trade return observations (n).
        skewness: Sample skewness of the returns.
        kurtosis: RAW (non-excess) sample kurtosis of the returns (normal = 3).

    Returns:
        The probability in (0, 1) that the true Sharpe exceeds the benchmark.

    Raises:
        ValueError: If ``n_returns < 2`` or if the Sharpe-estimator variance
            term is non-positive (which makes the PSR undefined; this happens
            only at extreme skew/kurtosis combined with a high Sharpe and must
            be surfaced, never silently swallowed).
    """
    if n_returns < 2:
        raise ValueError(f"PSR requires n_returns >= 2, got {n_returns}")

    variance_term = (
        1.0
        - skewness * observed_sharpe
        + ((kurtosis - 1.0) / 4.0) * observed_sharpe**2
    )
    if variance_term <= 0.0:
        raise ValueError(
            "Sharpe-estimator variance term is non-positive "
            f"({variance_term:.6g}); PSR is undefined. This indicates extreme "
            f"skew ({skewness:.4g}) / kurtosis ({kurtosis:.4g}) at Sharpe "
            f"{observed_sharpe:.4g}. Inspect the return distribution rather than "
            "trusting a deflated Sharpe here."
        )

    z = (observed_sharpe - benchmark_sharpe) * math.sqrt(n_returns - 1) / math.sqrt(
        variance_term
    )
    return normal_cdf(z)


def expected_max_sharpe(variance_sr: float, n_trials: int) -> float:
    """Expected maximum of K IID Sharpe estimates under the null (true SR = 0).

    This is the selection-bias benchmark: if you test ``n_trials`` strategies
    that all genuinely have zero edge, this is the Sharpe you would expect the
    luckiest of them to show. Bailey-Lopez de Prado estimator::

        E[max] = sqrt(V) * [ (1 - gamma) * Phi_inv(1 - 1/K)
                             + gamma * Phi_inv(1 - 1/(K * e)) ]

    where ``V`` is the cross-sectional variance of the per-trade Sharpe
    estimates across the K trials, ``gamma`` is the Euler-Mascheroni constant,
    ``Phi_inv`` is the inverse standard-normal CDF, and ``e`` is Euler's number.
    Because the term is scaled by ``sqrt(V)`` (a per-trade Sharpe variance), the
    result is in per-trade Sharpe units, matching the observed Sharpe.

    Args:
        variance_sr: Cross-sectional variance of the per-trade Sharpe estimates
            across the K trials. Must be non-negative. When the true trial
            Sharpes are unknown (a retrospective), estimate this from the
            dispersion of the Sharpe ratios actually observed across the
            strategies tested, and record the derivation for auditability.
        n_trials: Effective number of trials (K). Must be >= 1.

    Returns:
        The expected maximum Sharpe under the null, in per-trade units. Returns
        0.0 when ``n_trials == 1`` (no selection bias with a single trial).

    Raises:
        ValueError: If ``n_trials < 1`` or ``variance_sr < 0``.
    """
    if n_trials < 1:
        raise ValueError(f"expected_max_sharpe requires n_trials >= 1, got {n_trials}")
    if variance_sr < 0.0:
        raise ValueError(
            f"expected_max_sharpe requires variance_sr >= 0, got {variance_sr}"
        )
    if n_trials == 1:
        return 0.0

    gamma = _EULER_MASCHERONI
    term = (1.0 - gamma) * normal_ppf(1.0 - 1.0 / n_trials) + gamma * normal_ppf(
        1.0 - 1.0 / (n_trials * math.e)
    )
    return math.sqrt(variance_sr) * term


def deflated_sharpe_ratio(
    observed_sharpe: float,
    variance_sr: float,
    n_trials: int,
    n_returns: int,
    skewness: float,
    kurtosis: float,
) -> DeflatedSharpeResult:
    """Compute the Deflated Sharpe Ratio.

    Deflates the observed Sharpe against the expected MAXIMUM Sharpe that
    ``n_trials`` zero-edge strategies would produce by luck, then returns the
    probability the true Sharpe still exceeds that benchmark.

    Args:
        observed_sharpe: Observed per-trade Sharpe ratio (cost-adjusted).
        variance_sr: Cross-sectional variance of per-trade Sharpe estimates
            across the K trials (see `expected_max_sharpe`).
        n_trials: Effective number of trials (K) -- parameter combinations x
            symbols x timeframes x hypotheses, NOT just the ledger count
            (DEC-2026-06-04-002). Drives the deflation: larger K => stronger
            deflation => lower DSR.
        n_returns: Number of per-trade return observations.
        skewness: Sample skewness of the per-trade returns.
        kurtosis: RAW (non-excess) sample kurtosis of the per-trade returns.

    Returns:
        A `DeflatedSharpeResult`. The ``dsr_p_value`` field (= 1 - dsr) is what
        the PRD Tier floors gate against; LOW is good.

    Raises:
        ValueError: Propagated from `expected_max_sharpe` or
            `probabilistic_sharpe_ratio` on invalid inputs or a non-positive
            variance term.
    """
    sr_star = expected_max_sharpe(variance_sr, n_trials)
    dsr = probabilistic_sharpe_ratio(
        observed_sharpe=observed_sharpe,
        benchmark_sharpe=sr_star,
        n_returns=n_returns,
        skewness=skewness,
        kurtosis=kurtosis,
    )
    return DeflatedSharpeResult(
        dsr=dsr,
        dsr_p_value=1.0 - dsr,
        observed_sharpe=observed_sharpe,
        expected_max_sharpe=sr_star,
        n_returns=n_returns,
        n_trials=n_trials,
        skewness=skewness,
        kurtosis=kurtosis,
        variance_sr=variance_sr,
    )
