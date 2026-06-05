#!/usr/bin/env python
"""Retrospective Deflated Sharpe Ratio + conservative cost model (spec v2).

Applies the (already-built, verified) Deflated Sharpe Ratio
(``research/validation/deflated_sharpe.py``) plus a conservative v0 cost model
retroactively to the 5 KEEP strategies (MACD_PB, BTP, VBB, SRC, ICVP) and the 6
RETIRED strategies (BTF, CMF, RSI_BB, HATP, VRB, VPT).

PRIMARY output: updates to strategy biography YAMLs at
``research/biographies/{active,retired}/<strategy_id>.yaml`` (canonical store).
DERIVED output: per-strategy markdown, a portfolio summary, and a JSON file in
``docs/research/retrospective/`` -- all regenerable from the biographies.

Key methodology (see ``docs/research/RETROSPECTIVE_DSR_SPEC.md``):

- POOLED DSR (Section 5.5): each strategy's cost-adjusted, quarantine-filtered
  per-trade returns are pooled across symbols into ONE chronological series; DSR
  is computed ONCE on it. Per-symbol metrics are DESCRIPTIVE only, never gating.
- INCREMENTAL-PAD COST (operator decision 2026-06-05): recorded returns already
  net the simulator's costs, so the conservative case subtracts only the EXCESS
  of the v0 model over what was already booked (see ``research.backtest.cost_model``).
- BASE vs CONSERVATIVE (Section 6.5): every strategy is evaluated at a realistic
  base point and a worst-case conservative point. The GATE uses the conservative
  tier; the report SHOWS both. Fragility = base_tier != conservative_tier.
- MULTI-K + variance_sr SWEEPS (Sections 6.3, 6.4): both decisive knobs are
  swept; the gating verdict uses the most conservative end.
- PARA-02 QUARANTINE (DEC-2026-05-31-002): corrupt force-close trades are
  excluded using the single-source-of-truth helper from ``scripts.validation_report``.
- EXECUTION GATE (Section 10.1): the DSR test suite must pass before any real
  strategy is classified.

DATA SOURCE: ``PaperTradingSession.trade_log`` (JSON array of TradeRecord dicts),
selected by ``session_id`` prefix ``paper_<LABEL>_`` so it works for retired
strategies whose STRATEGY_CONFIG entries were removed. The trade logs live in
Neon; this environment's DATABASE_URL points at a local (empty) SQLite, so the
real run is executed by the operator with DATABASE_URL set to Neon.

Usage:
    python -m scripts.retrospective_dsr [options]

Options:
    --strategy <id>     Analyze a single strategy (default: all 11)
    --output-dir <path> Override docs/research/retrospective/
    --json-only         Skip markdown reports, write JSON only
    --skip-dsr-gate     Skip the DSR test-suite pre-flight (TESTING ONLY -- never
                        use on a real classification run)
    --verbose           Verbose per-strategy logging

Read-only with respect to the database. NEVER writes to Neon. Writes only to
``research/biographies/`` and the derived report directory.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from research.backtest.cost_model import (
    CostModel,
    apply_cost_model,
    mean_booked_and_incremental_pct,
    mean_round_trip_cost_pct_by_symbol,
)
from research.biographies.schema import (
    ClassificationHistoryEntry,
    CostComponentSource,
    EffectiveKDerivation,
    HardFloorStatus,
    KSensitivityCell,
    PerSymbolBreakdown,
    StatisticalValidationEntry,
    StrategyBiography,
    StrategyStatus,
    Tier,
    VarianceSrSensitivityCell,
)
from research.promotion.classifier import (
    action_description,
    build_hard_floor_status,
    classify_tier,
    recommended_action,
    resolve_final_tier,
)
from research.validation.deflated_sharpe import (
    DeflatedSharpeResult,
    deflated_sharpe_ratio,
    normal_ppf,
    sample_kurtosis,
    sample_sharpe,
    sample_skewness,
)
from research.validation.effective_k import (
    EffectiveKEstimate,
    estimate_portfolio_k,
    variance_sr_point_estimate,
    variance_sr_sweep,
)
from scripts.validation_report import _is_corrupt_force_close, _profit_factor
from src.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "research" / "retrospective"
BIOGRAPHIES_DIR = REPO_ROOT / "research" / "biographies"

# Effective-K derivation inputs (spec Section 6.2). No parameter-combination
# counts are recorded in the database for these eleven strategies, so K is an
# ESTIMATED lower bound. ~23 historical hypotheses across ~5 symbols each; ~50
# parameter combinations per hypothesis is a conservative-but-plausible estimate
# for runs whose sweep was not recorded.
HYPOTHESES_COUNTED: int = 23
AVG_SYMBOLS_PER_HYPOTHESIS: float = 5.0
PARAM_COMBOS_ESTIMATED_PER_HYPOTHESIS: int = 50
K_DERIVATION_NOTES: str = (
    "No parameter-combination counts recorded in the trade-log database for "
    "these strategies; param_combos estimated at 50/hypothesis. True K is "
    "higher -- treat as a lower bound. Gating verdict uses the highest swept K."
)


@dataclass(frozen=True)
class StrategySpec:
    """Identity of a strategy in the retrospective universe.

    Attributes:
        strategy_id: The label used in session_ids (e.g. ``MACD_PB``).
        status: Lifecycle status (drives active/ vs retired/ biography path).
        was_kept: True for the 5 KEEP strategies, False for the 6 RETIRED.
        known_symbols: Symbols from STRATEGY_CONFIG (KEEP only); empty for
            retired strategies, whose symbols are discovered from the sessions.
    """

    strategy_id: str
    status: StrategyStatus
    was_kept: bool
    known_symbols: list[str] = field(default_factory=list)


# The retrospective universe (spec Section 2.2). Symbols for KEEP strategies come
# from STRATEGY_CONFIG in scripts/run_paper_trading.py; retired strategies'
# symbols are discovered from their sessions.
STRATEGY_UNIVERSE: tuple[StrategySpec, ...] = (
    StrategySpec("MACD_PB", StrategyStatus.ACTIVE_LIVE, True, ["DOGEUSDT", "AVAXUSDT"]),
    StrategySpec(
        "BTP",
        StrategyStatus.ACTIVE_LIVE,
        True,
        ["BTCUSDT", "ETHUSDT", "BNBUSDT", "DOGEUSDT"],
    ),
    StrategySpec("VBB", StrategyStatus.ACTIVE_LIVE, True, ["BTCUSDT", "ETHUSDT", "SOLUSDT"]),
    StrategySpec("SRC", StrategyStatus.ACTIVE_LIVE, True, ["BTCUSDT", "ETHUSDT", "SOLUSDT"]),
    StrategySpec(
        "ICVP",
        StrategyStatus.ACTIVE_PAPER,
        True,
        [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
            "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT",
        ],
    ),
    StrategySpec("BTF", StrategyStatus.RETIRED, False),
    StrategySpec("CMF", StrategyStatus.RETIRED, False),
    StrategySpec("RSI_BB", StrategyStatus.RETIRED, False),
    StrategySpec("HATP", StrategyStatus.RETIRED, False),
    StrategySpec("VRB", StrategyStatus.RETIRED, False),
    StrategySpec("VPT", StrategyStatus.RETIRED, False),
)


# ---------------------------------------------------------------------------
# Execution gate (spec Section 10.1)
# ---------------------------------------------------------------------------
def assert_dsr_math_verified() -> None:
    """Refuse to classify on real data unless the DSR math tests pass.

    A miscalibrated capital-gating instrument that LOOKS rigorous is worse than
    none. Runs the DSR test suite as a subprocess and raises ``SystemExit`` on
    failure (spec Section 10.1).

    Raises:
        SystemExit: If the DSR test suite does not pass.
    """
    logger.info("dsr_gate_running")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/research/test_deflated_sharpe.py",
            "-q",
        ],
        capture_output=True,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        logger.error(
            "dsr_gate_failed",
            returncode=result.returncode,
            stdout=result.stdout.decode(errors="replace")[-2000:],
        )
        raise SystemExit(
            "DSR math verification FAILED. Refusing to classify strategies on an "
            "unverified instrument. Fix tests/research/test_deflated_sharpe.py first."
        )
    logger.info("dsr_gate_passed")


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------
def _profit_factor_from_returns(returns_pct: list[float]) -> float:
    """Return-weighted profit factor from a per-trade return series.

    Uses the single-source-of-truth ``_profit_factor`` (gross positive returns
    over absolute gross negative returns), keeping the definition identical to
    the live validation report.

    Args:
        returns_pct: Per-trade percentage returns.

    Returns:
        Profit factor (0.0 if no positive returns; +inf if positive with no
        negative).
    """
    wins = sum(r for r in returns_pct if r > 0.0)
    losses = sum(r for r in returns_pct if r <= 0.0)
    return _profit_factor(wins, losses)


def _max_drawdown_pct_from_returns(returns_pct: list[float]) -> float:
    """Max drawdown (%) on the compounded equity curve of per-trade returns.

    Recomputed on the pooled, cost-adjusted series (spec Section 9.1) rather than
    carried from a legacy backtest figure. Equity starts at 1.0 and compounds
    each trade's return; drawdown is measured against the running peak.

    Args:
        returns_pct: Per-trade percentage returns in chronological order.

    Returns:
        Maximum drawdown as a percentage of the running equity peak.
    """
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns_pct:
        equity *= 1.0 + r / 100.0
        if equity > peak:
            peak = equity
        if peak > 0.0:
            dd = (peak - equity) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _dsr_p_value(
    returns_pct: list[float], k: int, variance_sr: float
) -> tuple[float, DeflatedSharpeResult | None]:
    """Compute the DSR p-value for a return series at a given K and variance_sr.

    Args:
        returns_pct: Per-trade percentage returns.
        k: Effective number of trials.
        variance_sr: Cross-sectional Sharpe variance.

    Returns:
        A tuple ``(p_value, result)``. On a degenerate input (fewer than two
        returns, or a non-positive PSR variance term), returns ``(1.0, None)``
        -- the worst p-value, so an uncomputable strategy can never pass a floor.
    """
    if len(returns_pct) < 2:
        return 1.0, None
    observed = sample_sharpe(returns_pct)
    skew = sample_skewness(returns_pct)
    kurt = sample_kurtosis(returns_pct)
    try:
        result = deflated_sharpe_ratio(
            observed_sharpe=observed,
            variance_sr=variance_sr,
            n_trials=k,
            n_returns=len(returns_pct),
            skewness=skew,
            kurtosis=kurt,
        )
    except ValueError as exc:
        logger.warning("dsr_uncomputable", error=str(exc), n=len(returns_pct))
        return 1.0, None
    return result.dsr_p_value, result


def _z_from_dsr(dsr: float) -> float:
    """Convert a DSR (= Phi(z)) back to its z-score, clamped away from 0/1.

    Args:
        dsr: The Deflated Sharpe Ratio (a probability in (0, 1)).

    Returns:
        The z-score ``Phi_inv(dsr)``, with ``dsr`` clamped to (1e-9, 1-1e-9).
    """
    clamped = min(max(dsr, 1e-9), 1.0 - 1e-9)
    return normal_ppf(clamped)


# ---------------------------------------------------------------------------
# Core per-strategy analysis (pure; testable without a database)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalysisResult:
    """Full retrospective analysis result for one strategy."""

    strategy_id: str
    status: StrategyStatus
    n_trades_analyzed: int
    n_trades_quarantined: int
    final_tier: Tier
    validation_entry: StatisticalValidationEntry
    per_symbol_round_trip_cost_pct: dict[str, float]
    mean_booked_cost_pct: float
    mean_incremental_pad_pct: float


def analyze_strategy(
    strategy_id: str,
    status: StrategyStatus,
    raw_trades: list[dict[str, Any]],
    *,
    k_estimate: EffectiveKEstimate,
    variance_sr_point: float,
    cost_model: CostModel,
    run_id: str,
    run_date: str,
) -> AnalysisResult:
    """Run the full retrospective analysis for one strategy on its pooled trades.

    Pools the (quarantine-filtered) trades chronologically, applies the
    incremental-pad cost model to produce base and conservative return series,
    computes pooled DSR at both operating points, sweeps K and variance_sr,
    classifies the tier (gating on the conservative case), and assembles the
    canonical ``StatisticalValidationEntry``.

    Args:
        strategy_id: Strategy label (e.g. ``MACD_PB``).
        status: Lifecycle status.
        raw_trades: All trade dicts pooled across the strategy's symbols (may
            include corrupt force-closes; they are quarantined here).
        k_estimate: Portfolio effective-K estimate + sweep.
        variance_sr_point: Cross-sectional Sharpe-variance point estimate.
        cost_model: The cost model to apply.
        run_id: Idempotency key for this retrospective run.
        run_date: ``YYYY-MM-DD`` run date.

    Returns:
        An ``AnalysisResult`` carrying the canonical validation entry and the
        per-symbol round-trip costs for the operator sanity-check print.
    """
    # PARA-02 quarantine (single source of truth).
    trades = [t for t in raw_trades if not _is_corrupt_force_close(t)]
    n_quarantined = len(raw_trades) - len(trades)

    # Pool chronologically by exit time (ISO8601 strings sort correctly), then
    # entry time as a tiebreaker.
    trades.sort(key=lambda t: (str(t.get("exit_time", "")), str(t.get("entry_time", ""))))

    # Apply the cost model -> base (recorded) and conservative (incremental-pad)
    # per-trade return series, in the same chronological order.
    base_returns: list[float] = []
    conservative_returns: list[float] = []
    for trade in trades:
        adjusted = apply_cost_model(trade, cost_model)
        base_returns.append(adjusted.base_return_pct)
        conservative_returns.append(adjusted.conservative_return_pct)

    n = len(trades)

    # Pooled metrics at each operating point.
    pf_raw = _profit_factor_from_returns(base_returns)
    pf_adjusted = _profit_factor_from_returns(conservative_returns)
    sharpe_raw = sample_sharpe(base_returns)
    sharpe_adjusted = sample_sharpe(conservative_returns)
    max_dd_base = _max_drawdown_pct_from_returns(base_returns)
    max_dd_adjusted = _max_drawdown_pct_from_returns(conservative_returns)
    skew_adjusted = sample_skewness(conservative_returns)
    kurt_adjusted = sample_kurtosis(conservative_returns)

    variance_sr_high = max(variance_sr_sweep(variance_sr_point))

    # Base case: realistic costs, point-estimate K + variance_sr.
    base_p, _ = _dsr_p_value(base_returns, k_estimate.point_estimate, variance_sr_point)
    # Conservative (gating) case: padded costs, highest K, high variance_sr.
    conservative_p, conservative_result = _dsr_p_value(
        conservative_returns, k_estimate.gating_k, variance_sr_high
    )

    # Tier at each operating point, then the resolved final tier (gate on
    # conservative, soften real-but-fragile to Tier C).
    base_tier = classify_tier(base_p, max_dd_base, pf_raw, sharpe_raw, n)
    conservative_tier = classify_tier(
        conservative_p, max_dd_adjusted, pf_adjusted, sharpe_adjusted, n
    )
    final_tier, fragility = resolve_final_tier(base_tier, conservative_tier)

    # K sensitivity sweep (isolate K: conservative series + point variance_sr).
    k_cells: list[KSensitivityCell] = []
    for k in k_estimate.sweep:
        p_k, _ = _dsr_p_value(conservative_returns, k, variance_sr_point)
        tier_k = classify_tier(p_k, max_dd_adjusted, pf_adjusted, sharpe_adjusted, n)
        k_cells.append(KSensitivityCell(k=k, dsr_p_value=p_k, tier=tier_k))

    # variance_sr sensitivity sweep (isolate variance_sr: conservative series +
    # gating K).
    v_cells: list[VarianceSrSensitivityCell] = []
    for v in variance_sr_sweep(variance_sr_point):
        p_v, _ = _dsr_p_value(conservative_returns, k_estimate.gating_k, v)
        tier_v = classify_tier(p_v, max_dd_adjusted, pf_adjusted, sharpe_adjusted, n)
        v_cells.append(
            VarianceSrSensitivityCell(variance_sr=v, dsr_p_value=p_v, tier=tier_v)
        )

    # Verdict is fragile if base/conservative disagree OR the tier flips across
    # the K sweep.
    verdict_is_fragile = fragility or len({c.tier for c in k_cells}) > 1

    # Per-symbol DESCRIPTIVE breakdown (not gating).
    per_symbol = _per_symbol_breakdown(trades, cost_model)
    per_symbol_costs = mean_round_trip_cost_pct_by_symbol(trades, cost_model)

    # Diagnostic: mean booked cost vs mean incremental pad. A near-zero mean
    # booked cost means the historical records lack the commission/slippage
    # fields, so the conservative case has degraded to double-charging
    # (code review 2026-06-05). Surfaced to the operator in the run log.
    mean_booked_cost_pct, mean_incremental_pad_pct = mean_booked_and_incremental_pct(
        trades, cost_model
    )

    hard_floor = build_hard_floor_status(
        conservative_dsr_p_value=conservative_p,
        conservative_max_dd_pct=max_dd_adjusted,
        cost_model_verified=False,  # v0 unverified
        leakage_check="not_run",
    )

    reasoning = _classification_reasoning(
        final_tier, base_tier, conservative_tier, conservative_p, max_dd_adjusted, n
    )

    dsr_z = _z_from_dsr(conservative_result.dsr) if conservative_result else 0.0

    entry = StatisticalValidationEntry(
        run_date=run_date,
        run_id=run_id,
        cost_model_version=cost_model.version,
        n_trades_analyzed=n,
        n_trades_quarantined=n_quarantined,
        pf_raw=_finite(pf_raw),
        pf_adjusted=_finite(pf_adjusted),
        sharpe_raw=sharpe_raw,
        sharpe_adjusted=sharpe_adjusted,
        max_dd_pct_pooled_base=max_dd_base,
        max_dd_pct_pooled_adjusted=max_dd_adjusted,
        skewness=skew_adjusted,
        kurtosis=kurt_adjusted,
        effective_k=k_estimate.point_estimate,
        effective_k_derivation=k_estimate.derivation,
        variance_sr=variance_sr_high,
        dsr_z_score=dsr_z,
        dsr_p_value=conservative_p,
        base_dsr_p_value=base_p,
        conservative_dsr_p_value=conservative_p,
        base_tier=base_tier,
        conservative_tier=conservative_tier,
        fragility=fragility,
        dsr_k_sensitivity=k_cells,
        dsr_variance_sr_sensitivity=v_cells,
        gating_k_used=k_estimate.gating_k,
        verdict_is_fragile=verdict_is_fragile,
        per_symbol_breakdown=per_symbol,
        hard_floor_status=hard_floor,
        classified_tier=final_tier,
        classification_reasoning=reasoning,
    )

    return AnalysisResult(
        strategy_id=strategy_id,
        status=status,
        n_trades_analyzed=n,
        n_trades_quarantined=n_quarantined,
        final_tier=final_tier,
        validation_entry=entry,
        per_symbol_round_trip_cost_pct=per_symbol_costs,
        mean_booked_cost_pct=mean_booked_cost_pct,
        mean_incremental_pad_pct=mean_incremental_pad_pct,
    )


def _finite(value: float) -> float:
    """Replace +inf profit factor with a large sentinel for serialization.

    Args:
        value: A profit factor that may be ``float('inf')``.

    Returns:
        ``999.99`` if the value is infinite, otherwise the value unchanged.
    """
    return 999.99 if value == float("inf") else value


def _per_symbol_breakdown(
    trades: list[dict[str, Any]], cost_model: CostModel
) -> list[PerSymbolBreakdown]:
    """Compute DESCRIPTIVE per-symbol metrics (spec Section 5.5; not gating).

    Args:
        trades: Quarantine-filtered trades for one strategy.
        cost_model: The cost model to apply.

    Returns:
        One ``PerSymbolBreakdown`` per symbol, sorted by symbol.
    """
    by_symbol: dict[str, list[float]] = {}
    for trade in trades:
        adjusted = apply_cost_model(trade, cost_model)
        by_symbol.setdefault(str(trade.get("symbol", "UNKNOWN")), []).append(
            adjusted.conservative_return_pct
        )
    costs = mean_round_trip_cost_pct_by_symbol(trades, cost_model)
    out: list[PerSymbolBreakdown] = []
    for symbol in sorted(by_symbol):
        returns = by_symbol[symbol]
        out.append(
            PerSymbolBreakdown(
                symbol=symbol,
                n_trades=len(returns),
                pf=_finite(_profit_factor_from_returns(returns)),
                sharpe=sample_sharpe(returns),
                round_trip_cost_pct=costs.get(symbol, 0.0),
                cost_source=CostComponentSource.ESTIMATED,
            )
        )
    return out


def _classification_reasoning(
    final_tier: Tier,
    base_tier: Tier,
    conservative_tier: Tier,
    conservative_p: float,
    max_dd_adjusted: float,
    n: int,
) -> str:
    """Build a human-readable explanation of the tier verdict.

    Args:
        final_tier: The resolved final tier.
        base_tier: Tier at the base operating point.
        conservative_tier: Tier at the conservative operating point.
        conservative_p: Gating DSR p-value.
        max_dd_adjusted: Gating max drawdown percentage.
        n: Number of trades analyzed.

    Returns:
        A one-paragraph reasoning string.
    """
    parts = [
        f"Gating (conservative) DSR p={conservative_p:.3f}, "
        f"MaxDD={max_dd_adjusted:.2f}%, N={n}.",
        f"Base tier {base_tier.value}; conservative tier {conservative_tier.value}.",
    ]
    if base_tier != conservative_tier:
        if final_tier == Tier.TIER_C and conservative_tier == Tier.TIER_D:
            parts.append(
                "Real-but-fragile: deployable in the base case but collapses "
                "under stacked worst-cases. Held at Tier C for more data, not retired."
            )
        else:
            parts.append("Verdict is fragile across operating points; gated on conservative.")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Database reader (thin; not exercised by unit tests)
# ---------------------------------------------------------------------------
def read_pooled_trades(strategy_id: str) -> list[dict[str, Any]]:
    """Read all trade-log records for a strategy, pooled across its symbols.

    Selects ``PaperTradingSession`` rows whose ``session_id`` begins with
    ``paper_<strategy_id>_`` (the session-id convention is
    ``paper_<label>_<symbol>``), which works for retired strategies whose
    STRATEGY_CONFIG entries were removed. Read-only -- never writes to the DB.

    Args:
        strategy_id: Strategy label (e.g. ``MACD_PB``).

    Returns:
        A flat list of trade dicts pooled across all of the strategy's sessions.
    """
    # Imported lazily so importing this module (e.g. in tests) does not require
    # a live database connection.
    from sqlalchemy import select

    from src.data.database import get_db
    from src.data.models.paper_session import PaperTradingSession

    prefix = f"paper_{strategy_id}_"
    pooled: list[dict[str, Any]] = []
    with get_db() as db:
        stmt = select(PaperTradingSession).where(
            PaperTradingSession.session_id.like(f"{prefix}%")
        )
        sessions = db.execute(stmt).scalars().all()
        for session in sessions:
            pooled.extend(session.trade_log or [])
    logger.info(
        "trades_read",
        strategy_id=strategy_id,
        sessions=len(sessions),
        trades=len(pooled),
    )
    return pooled


# ---------------------------------------------------------------------------
# Biography writer (PRIMARY output; idempotent)
# ---------------------------------------------------------------------------
def _biography_path(strategy_id: str, status: StrategyStatus) -> Path:
    """Return the canonical biography path for a strategy.

    Active strategies live under ``active/``, retired ones under ``retired/``.
    If a file already exists in the other directory, that existing path is
    returned so the run does not create a duplicate.

    Args:
        strategy_id: Strategy label.
        status: Lifecycle status.

    Returns:
        The path the biography should be read from / written to.
    """
    active = BIOGRAPHIES_DIR / "active" / f"{strategy_id}.yaml"
    retired = BIOGRAPHIES_DIR / "retired" / f"{strategy_id}.yaml"
    if active.exists():
        return active
    if retired.exists():
        return retired
    return retired if status == StrategyStatus.RETIRED else active


def load_or_create_biography(
    strategy_id: str, status: StrategyStatus, known_symbols: list[str]
) -> StrategyBiography:
    """Load an existing biography or create a minimal new one.

    Args:
        strategy_id: Strategy label.
        status: Lifecycle status.
        known_symbols: Symbols to seed a new biography with.

    Returns:
        A ``StrategyBiography`` (loaded from YAML, or freshly created).
    """
    path = _biography_path(strategy_id, status)
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return StrategyBiography.model_validate(data)
    return StrategyBiography(
        strategy_id=strategy_id, status=status, symbols=list(known_symbols)
    )


def write_biography(
    biography: StrategyBiography,
    result: AnalysisResult,
    *,
    run_id: str,
    run_date: str,
    cost_model_version: str,
) -> bool:
    """Append this run's results to a biography idempotently and persist it.

    Idempotency (spec Section 9.1): if an entry with this ``run_id`` already
    exists in ``statistical_validation_history``, the write is a no-op so a
    crashed run is safely re-runnable. Records a ``classification_history`` entry
    and a ``decision_log`` placeholder only when the classification actually
    changes.

    Args:
        biography: The biography to update (mutated in place).
        result: The analysis result to record.
        run_id: Idempotency key.
        run_date: ``YYYY-MM-DD`` run date.
        cost_model_version: Cost-model version tag.

    Returns:
        True if the biography was updated and written; False if skipped because
        this ``run_id`` was already recorded.
    """
    if biography.has_validation_run(run_id):
        logger.info("biography_skip_idempotent", strategy_id=biography.strategy_id, run_id=run_id)
        return False

    biography.statistical_validation_history.append(result.validation_entry)

    previous = biography.current_classification
    new_tier_value = result.final_tier.value if hasattr(result.final_tier, "value") else result.final_tier
    classification_changed = previous != new_tier_value

    biography.current_classification = result.final_tier

    if classification_changed and not biography.has_classification_change(run_id):
        biography.classification_history.append(
            ClassificationHistoryEntry(
                date=run_date,
                classification=result.final_tier,
                triggered_by=run_id,
                cost_model_version=cost_model_version,
                dsr_p_value=result.validation_entry.conservative_dsr_p_value,
                notes=(
                    f"Retrospective DSR ({cost_model_version}): "
                    f"{previous} -> {new_tier_value}."
                ),
            )
        )
        biography.decision_log.append(
            f"PENDING-DEC: Retrospective DSR reclassified {biography.strategy_id} "
            f"from {previous} to {new_tier_value} (run {run_id}). File DEC entry "
            f"in BOTH .claude/DECISIONS.md and .agent/DECISIONS.md after operator review."
        )

    path = _biography_path(biography.strategy_id, biography.status)
    path.parent.mkdir(parents=True, exist_ok=True)
    # mode="json" serializes enums and other types to YAML-safe primitives
    # (plain str/int/float/list/dict), so safe_dump can represent them.
    data = biography.model_dump(mode="json")
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, allow_unicode=False),
        encoding="utf-8",
    )
    logger.info(
        "biography_written",
        strategy_id=biography.strategy_id,
        path=str(path),
        tier=new_tier_value,
        classification_changed=classification_changed,
    )
    return True


# ---------------------------------------------------------------------------
# Derived reports
# ---------------------------------------------------------------------------
def _tier_label(tier: Tier | str) -> str:
    """Return the plain string value of a tier (enum or str)."""
    return tier.value if isinstance(tier, Tier) else str(tier)


def render_strategy_markdown(result: AnalysisResult, run_date: str) -> str:
    """Render the per-strategy markdown report (DERIVED; spec Section 3.1).

    Args:
        result: The analysis result.
        run_date: ``YYYY-MM-DD`` run date.

    Returns:
        The markdown document as a string.
    """
    e = result.validation_entry
    status_label = "KEEP_LIVE" if result.status != StrategyStatus.RETIRED else "RETIRED"
    lines: list[str] = [
        f"# Retrospective DSR Analysis: {result.strategy_id}",
        "",
        f"**Date:** {run_date}",
        f"**Cost Model:** {e.cost_model_version} (UNVERIFIED -- incremental-pad over booked costs)",
        f"**Status at Time of Analysis:** {status_label}",
        "",
        "## Summary",
        "",
        f"**Tier Classification:** {_tier_label(result.final_tier)}",
        f"**DSR p-value (gating/conservative):** {e.conservative_dsr_p_value:.3f}",
        f"**DSR p-value (base):** {e.base_dsr_p_value:.3f}",
        f"**Recommended Action:** {action_description(result.final_tier)}",
        f"**Verdict fragile:** {e.verdict_is_fragile}",
        "",
        "## Pooled Metrics (base = recorded; adjusted = conservative incremental-pad)",
        "",
        "| Metric | Base | Conservative (gating) |",
        "|--------|------|-----------------------|",
        f"| N | {e.n_trades_analyzed} | {e.n_trades_analyzed} |",
        f"| Profit Factor | {e.pf_raw:.2f} | {e.pf_adjusted:.2f} |",
        f"| Sharpe (per-trade) | {e.sharpe_raw:.3f} | {e.sharpe_adjusted:.3f} |",
        f"| MaxDD % | {e.max_dd_pct_pooled_base:.2f} | {e.max_dd_pct_pooled_adjusted:.2f} |",
        f"| Tier | {_tier_label(e.base_tier)} | {_tier_label(e.conservative_tier)} |",
        "",
        "## DSR Calculation",
        "",
        f"- Effective K (point estimate): {e.effective_k} (derivation: {e.effective_k_derivation.method}, lower_bound={e.effective_k_derivation.is_lower_bound})",
        f"- Gating K (conservative): {e.gating_k_used}",
        f"- variance_sr (gating): {e.variance_sr:.4f}",
        f"- Sharpe (adjusted): {e.sharpe_adjusted:.3f}",
        f"- Skew: {e.skewness:.3f}  Kurtosis (raw): {e.kurtosis:.3f}",
        f"- DSR z-score: {e.dsr_z_score:.3f}",
        f"- **DSR p-value (gating): {e.conservative_dsr_p_value:.3f}**",
        "",
        "### K sensitivity sweep",
        "",
        "| K | DSR p | Tier |",
        "|---|-------|------|",
    ]
    for cell in e.dsr_k_sensitivity:
        lines.append(f"| {cell.k} | {cell.dsr_p_value:.3f} | {_tier_label(cell.tier)} |")
    lines += [
        "",
        "### variance_sr sensitivity sweep (at gating K)",
        "",
        "| variance_sr | DSR p | Tier |",
        "|-------------|-------|------|",
    ]
    for vcell in e.dsr_variance_sr_sensitivity:
        lines.append(
            f"| {vcell.variance_sr:.4f} | {vcell.dsr_p_value:.3f} | {_tier_label(vcell.tier)} |"
        )
    lines += [
        "",
        "## Per-Symbol Breakdown (DESCRIPTIVE -- not gating)",
        "",
        "| Symbol | N | PF (adj) | Sharpe (adj) | Round-trip cost % | Cost source |",
        "|--------|---|----------|--------------|-------------------|-------------|",
    ]
    for sym in e.per_symbol_breakdown:
        lines.append(
            f"| {sym.symbol} | {sym.n_trades} | {sym.pf:.2f} | {sym.sharpe:.3f} | "
            f"{sym.round_trip_cost_pct:.3f} | {_source_label(sym.cost_source)} |"
        )
    lines += [
        "",
        "## Hard Floor Status",
        "",
        f"- DSR p<0.3 floor: {'PASSED' if e.hard_floor_status.dsr_passed else 'FAILED'}",
        f"- MaxDD<5%: {'PASSED' if e.hard_floor_status.max_dd_passed else 'FAILED'}",
        f"- Cost model verified: {e.hard_floor_status.cost_model_verified}",
        f"- Leakage check: {e.hard_floor_status.leakage_check}",
        "",
        "## Classification Reasoning",
        "",
        e.classification_reasoning,
        "",
        "## Honest Caveats",
        "",
        "- Cost model is UNVERIFIED (v0). Realized slippage could NOT be measured "
        "(no signal/fill prices in the trade logs), so slippage and spread are "
        "ESTIMATED (2x-padded) for every symbol.",
        "- Per the operator decision, costs are applied as an INCREMENTAL pad over "
        "the costs the simulator already booked, to avoid double-counting.",
        "- Pooled DSR concatenates per-symbol trades chronologically; concurrent, "
        "correlated trades are treated as sequential. This is a Sharpe point "
        "estimate, not a true multi-asset equity curve (spec Section 5.5).",
        f"- N={e.n_trades_analyzed}; at small N the DSR has a wide confidence interval.",
        f"- Trades quarantined (PARA-02): {e.n_trades_quarantined}.",
        "",
    ]
    return "\n".join(lines)


def _source_label(source: CostComponentSource | str) -> str:
    """Return the plain string of a cost-component source."""
    return source.value if isinstance(source, CostComponentSource) else str(source)


def render_portfolio_summary(results: list[AnalysisResult], run_date: str) -> str:
    """Render the portfolio summary markdown (DERIVED; spec Section 3.2).

    Args:
        results: All analysis results.
        run_date: ``YYYY-MM-DD`` run date.

    Returns:
        The portfolio summary markdown document.
    """
    keep = [r for r in results if r.status != StrategyStatus.RETIRED]
    retired = [r for r in results if r.status == StrategyStatus.RETIRED]

    def _count(rs: list[AnalysisResult], tier: Tier) -> int:
        return sum(1 for r in rs if r.final_tier == tier)

    lines: list[str] = [
        "# Retrospective DSR Portfolio Summary",
        "",
        f"**Date:** {run_date}",
        f"**Strategies Analyzed:** {len(results)} ({len(keep)} KEEP, {len(retired)} RETIRED)",
        "**Cost Model:** v0_unverified (incremental-pad; 2x on estimated components)",
        "",
        "| Strategy | Status | Tier | DSR p (gate) | DSR p (base) | PF (adj) | Sharpe (adj) | N | Fragile | Action |",
        "|----------|--------|------|--------------|--------------|----------|--------------|---|---------|--------|",
    ]
    for r in sorted(results, key=lambda x: x.validation_entry.conservative_dsr_p_value):
        e = r.validation_entry
        status_label = "KEEP" if r.status != StrategyStatus.RETIRED else "RETIRED"
        lines.append(
            f"| {r.strategy_id} | {status_label} | {_tier_label(r.final_tier)} | "
            f"{e.conservative_dsr_p_value:.3f} | {e.base_dsr_p_value:.3f} | "
            f"{e.pf_adjusted:.2f} | {e.sharpe_adjusted:.3f} | {e.n_trades_analyzed} | "
            f"{e.verdict_is_fragile} | {recommended_action(r.final_tier)} |"
        )

    keep_surviving = sum(
        1 for r in keep if r.validation_entry.conservative_dsr_p_value < 0.3
    )
    lines += [
        "",
        "## Headline Findings",
        "",
        f"- KEEP strategies surviving DSR floor (p<0.3, conservative): {keep_surviving} of {len(keep)}",
        f"- KEEP at Tier A: {_count(keep, Tier.TIER_A)}",
        f"- KEEP at Tier B: {_count(keep, Tier.TIER_B)}",
        f"- KEEP at Tier C: {_count(keep, Tier.TIER_C)}",
        f"- KEEP at Tier D: {_count(keep, Tier.TIER_D)}",
        f"- RETIRED confirmed (Tier C/D): {_count(retired, Tier.TIER_C) + _count(retired, Tier.TIER_D)} of {len(retired)}",
        f"- RETIRED surprises (Tier A/B -- warrant re-examination): {_count(retired, Tier.TIER_A) + _count(retired, Tier.TIER_B)}",
        "",
        "## Decisions Triggered",
        "",
        "Any KEEP strategy whose tier changed has a PENDING-DEC note appended to "
        "its biography decision_log. File the DEC entry in BOTH .claude/DECISIONS.md "
        "and .agent/DECISIONS.md (next id DEC-2026-06-04-013) after operator review, "
        "then verify with `diff`.",
        "",
    ]
    return "\n".join(lines)


def render_json(results: list[AnalysisResult], run_date: str, cost_model_version: str) -> dict[str, Any]:
    """Render the JSON output (DERIVED; spec Section 3.3).

    Args:
        results: All analysis results.
        run_date: ``YYYY-MM-DD`` run date.
        cost_model_version: Cost-model version tag.

    Returns:
        A JSON-serializable dict.
    """
    strategies: dict[str, Any] = {}
    for r in results:
        e = r.validation_entry
        strategies[r.strategy_id] = {
            "tier": _tier_label(r.final_tier),
            "dsr_p_value": e.conservative_dsr_p_value,
            "dsr_p_value_base": e.base_dsr_p_value,
            "raw_pf": e.pf_raw,
            "adjusted_pf": e.pf_adjusted,
            "n": e.n_trades_analyzed,
            "verdict_is_fragile": e.verdict_is_fragile,
            "passes_hard_floor": e.hard_floor_status.dsr_passed and e.hard_floor_status.max_dd_passed,
            "recommended_action": recommended_action(r.final_tier),
        }
    keep = [r for r in results if r.status != StrategyStatus.RETIRED]
    retired = [r for r in results if r.status == StrategyStatus.RETIRED]
    return {
        "run_date": run_date,
        "cost_model_version": cost_model_version,
        "strategies": strategies,
        "portfolio_summary": {
            "keep_surviving_dsr": sum(
                1 for r in keep if r.validation_entry.conservative_dsr_p_value < 0.3
            ),
            "keep_tier_a": sum(1 for r in keep if r.final_tier == Tier.TIER_A),
            "keep_tier_b": sum(1 for r in keep if r.final_tier == Tier.TIER_B),
            "keep_tier_c": sum(1 for r in keep if r.final_tier == Tier.TIER_C),
            "keep_tier_d": sum(1 for r in keep if r.final_tier == Tier.TIER_D),
            "retired_validated_by_dsr": sum(
                1 for r in retired if r.final_tier in (Tier.TIER_C, Tier.TIER_D)
            ),
            "retired_surprises": sum(
                1 for r in retired if r.final_tier in (Tier.TIER_A, Tier.TIER_B)
            ),
        },
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def build_effective_k() -> EffectiveKEstimate:
    """Build the portfolio effective-K estimate from documented counts."""
    return estimate_portfolio_k(
        hypotheses_counted=HYPOTHESES_COUNTED,
        symbols_per_hypothesis_avg=AVG_SYMBOLS_PER_HYPOTHESIS,
        param_combos_recorded=0,
        param_combos_estimated=HYPOTHESES_COUNTED * PARAM_COMBOS_ESTIMATED_PER_HYPOTHESIS,
        notes=K_DERIVATION_NOTES,
    )


def run_retrospective(
    specs: list[StrategySpec],
    *,
    output_dir: Path,
    json_only: bool,
    run_id: str,
    run_date: str,
) -> list[AnalysisResult]:
    """Run the full retrospective across the given strategies.

    Two passes: pass 1 reads trades and computes each strategy's conservative
    Sharpe so the cross-sectional ``variance_sr`` can be estimated from the
    analyzed set; pass 2 computes DSR, classifies, writes biographies, and
    renders derived reports.

    Args:
        specs: Strategy specs to analyze.
        output_dir: Directory for derived reports.
        json_only: If True, skip markdown reports.
        run_id: Idempotency key.
        run_date: ``YYYY-MM-DD`` run date.

    Returns:
        The list of ``AnalysisResult`` for all analyzed strategies.
    """
    cost_model = CostModel.v0_unverified()
    k_estimate = build_effective_k()

    # Pass 1: read trades, compute each strategy's conservative pooled Sharpe.
    pooled_by_strategy: dict[str, list[dict[str, Any]]] = {}
    sharpes: list[float] = []
    for spec in specs:
        raw = read_pooled_trades(spec.strategy_id)
        pooled_by_strategy[spec.strategy_id] = raw
        trades = [t for t in raw if not _is_corrupt_force_close(t)]
        conservative = [
            apply_cost_model(t, cost_model).conservative_return_pct for t in trades
        ]
        sharpes.append(sample_sharpe(conservative))

    variance_sr_point = variance_sr_point_estimate(sharpes)
    logger.info(
        "variance_sr_estimated",
        variance_sr_point=variance_sr_point,
        n_strategies=len(sharpes),
    )

    # Pass 2: analyze, write biographies, collect results.
    results: list[AnalysisResult] = []
    for spec in specs:
        result = analyze_strategy(
            spec.strategy_id,
            spec.status,
            pooled_by_strategy[spec.strategy_id],
            k_estimate=k_estimate,
            variance_sr_point=variance_sr_point,
            cost_model=cost_model,
            run_id=run_id,
            run_date=run_date,
        )
        biography = load_or_create_biography(
            spec.strategy_id, spec.status, spec.known_symbols
        )
        write_biography(
            biography,
            result,
            run_id=run_id,
            run_date=run_date,
            cost_model_version=cost_model.version,
        )
        _print_operator_costs(result)
        results.append(result)

    _write_reports(results, output_dir, run_date, cost_model.version, json_only)
    return results


# Below this mean booked-cost (%), the booked cost is effectively zero, which
# means the historical records lack the commission/slippage fields and the
# conservative case has degraded to double-charging (code review 2026-06-05).
_BOOKED_COST_FLOOR_PCT: float = 0.01


def _print_operator_costs(result: AnalysisResult) -> None:
    """Print per-symbol round-trip cost + booked/incremental diagnostic (spec 5.3).

    Surfaces the mean booked cost and mean incremental pad so the operator can
    catch the schema-evolution failure mode: if mean booked cost is ~0, the
    incremental-pad decision has silently degraded to double-charging and any
    Tier-D verdict must NOT be trusted until investigated.
    """
    logger.info(
        "operator_cost_check",
        strategy_id=result.strategy_id,
        n_trades=result.n_trades_analyzed,
        final_tier=_tier_label(result.final_tier),
        mean_booked_cost_pct=round(result.mean_booked_cost_pct, 4),
        mean_incremental_pad_pct=round(result.mean_incremental_pad_pct, 4),
        per_symbol_round_trip_cost_pct={
            k: round(v, 3) for k, v in result.per_symbol_round_trip_cost_pct.items()
        },
    )
    if (
        result.n_trades_analyzed > 0
        and result.mean_booked_cost_pct < _BOOKED_COST_FLOOR_PCT
    ):
        logger.warning(
            "booked_cost_near_zero",
            strategy_id=result.strategy_id,
            mean_booked_cost_pct=round(result.mean_booked_cost_pct, 4),
            message=(
                "Mean booked cost is ~0: historical records likely lack "
                "commission/slippage fields, so the conservative case is "
                "double-charging costs (rejected option C). Do NOT trust this "
                "strategy's Tier-D verdict until the trade-record schema is "
                "confirmed to carry entry_commission/exit_commission/slippage_cost."
            ),
        )


def _write_reports(
    results: list[AnalysisResult],
    output_dir: Path,
    run_date: str,
    cost_model_version: str,
    json_only: bool,
) -> None:
    """Write the derived markdown + JSON reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if not json_only:
        for result in results:
            md_path = output_dir / f"{result.strategy_id}_{run_date}.md"
            md_path.write_text(render_strategy_markdown(result, run_date), encoding="utf-8")
        summary_path = output_dir / f"PORTFOLIO_SUMMARY_{run_date}.md"
        summary_path.write_text(render_portfolio_summary(results, run_date), encoding="utf-8")
    json_path = output_dir / f"results_{run_date}.json"
    json_path.write_text(
        json.dumps(render_json(results, run_date, cost_model_version), indent=2),
        encoding="utf-8",
    )
    logger.info("reports_written", output_dir=str(output_dir), json_only=json_only)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional argument vector (defaults to ``sys.argv``).

    Returns:
        The parsed namespace.
    """
    parser = argparse.ArgumentParser(description="Retrospective DSR + cost model.")
    parser.add_argument("--strategy", help="Analyze a single strategy by id (label).")
    parser.add_argument("--output-dir", help="Override the derived report directory.")
    parser.add_argument("--json-only", action="store_true", help="Skip markdown reports.")
    parser.add_argument(
        "--skip-dsr-gate",
        action="store_true",
        help="Skip the DSR test-suite pre-flight (TESTING ONLY).",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the retrospective DSR run.

    Args:
        argv: Optional argument vector.

    Returns:
        Process exit code (0 on success).
    """
    args = parse_args(argv)
    setup_logging()

    if not args.skip_dsr_gate:
        assert_dsr_math_verified()

    specs = list(STRATEGY_UNIVERSE)
    if args.strategy:
        specs = [s for s in specs if s.strategy_id == args.strategy]
        if not specs:
            available = ", ".join(s.strategy_id for s in STRATEGY_UNIVERSE)
            raise SystemExit(
                f"Unknown strategy {args.strategy!r}. Available: {available}"
            )

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_id = f"retrospective_dsr_run_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR

    logger.info("retrospective_start", run_id=run_id, n_strategies=len(specs))
    results = run_retrospective(
        specs,
        output_dir=output_dir,
        json_only=args.json_only,
        run_id=run_id,
        run_date=run_date,
    )
    logger.info("retrospective_complete", run_id=run_id, n_results=len(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
