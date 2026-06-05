"""Pydantic models for the strategy biography (PRD Appendix A).

The biography YAML is the CANONICAL record of a strategy's full lifecycle and
the PRIMARY output of ``scripts/retrospective_dsr.py``. Markdown and JSON reports
are DERIVED views that can be regenerated from these models at any time
(DEC-2026-06-04 data-architecture clarification; spec Section 3).

Design choices:

- ``extra="allow"`` on the top-level model. The full Appendix A schema is broad
  (hypothesis/parameter/optimization/backtest/paper/live histories, correlation,
  post-mortem). The retrospective OWNS only a few sections (classification +
  statistical validation). Allowing extra fields lets hand-authored sections
  round-trip untouched through a load/modify/save cycle, so the retrospective
  never silently drops data it does not model.

- Calendar dates (proposal dates, run dates) are plain ``str`` in ``YYYY-MM-DD``
  form. They are calendar days, not instants, so a timezone-aware ``datetime``
  would be misleading. Machine run identifiers carry a full UTC ISO timestamp
  generated with ``datetime.now(timezone.utc)`` per the project timezone rule.

- Mutable defaults use ``default_factory`` (never a shared list/dict instance),
  matching the project zero-technical-debt rule.

Research-only module: ``src/`` must never import from here (PRD Section 5.2).
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrategyStatus(str, Enum):
    """Lifecycle status of a strategy (PRD Appendix A ``status`` field)."""

    ACTIVE_RESEARCH = "ACTIVE_RESEARCH"
    ACTIVE_PAPER = "ACTIVE_PAPER"
    ACTIVE_LIVE = "ACTIVE_LIVE"
    RETIRED = "RETIRED"


class Tier(str, Enum):
    """Tier classification (PRD Section 9.1 / DEC-2026-06-04-008).

    The four canonical tiers plus ``BELOW_FLOOR``, a sweep-cell sentinel used in
    the multi-K / multi-variance sensitivity tables when a particular (K,
    variance_sr) combination pushes the DSR p-value past the deployment floor.
    ``BELOW_FLOOR`` is never a final ``current_classification`` -- the final
    verdict is always one of the four tiers (the conservative case gates it).
    """

    TIER_A = "TIER_A_FULL_READY"
    TIER_B = "TIER_B_PROVISIONAL_READY"
    TIER_C = "TIER_C_NEEDS_WORK"
    TIER_D = "TIER_D_REJECT"
    BELOW_FLOOR = "BELOW_FLOOR"


class CostComponentSource(str, Enum):
    """Whether a cost component was MEASURED from data or ESTIMATED (padded).

    Drives the single-pad conservatism rule (spec Section 5.2): only ESTIMATED
    components receive the 2x conservative multiplier; MEASURED components are
    used as-is so conservatism is never stacked twice on one quantity.
    """

    MEASURED = "measured"
    ESTIMATED = "estimated"


class HardFloorStatus(BaseModel):
    """Pass/fail of each non-negotiable hard floor (PRD Section 9.2)."""

    model_config = ConfigDict(extra="allow")

    dsr_passed: bool
    max_dd_passed: bool
    cost_model_verified: bool
    leakage_check: str = "not_run"


class KSensitivityCell(BaseModel):
    """DSR verdict at one effective-K value (spec Section 6.3)."""

    model_config = ConfigDict(extra="allow")

    k: int
    dsr_p_value: float
    tier: Tier


class VarianceSrSensitivityCell(BaseModel):
    """DSR verdict at one ``variance_sr`` value (spec Section 6.4)."""

    model_config = ConfigDict(extra="allow")

    variance_sr: float
    dsr_p_value: float
    tier: Tier


class PerSymbolBreakdown(BaseModel):
    """DESCRIPTIVE per-symbol metrics (spec Section 5.5).

    These are shown in reports to spot a strategy carried by one symbol. They
    are NOT gating numbers and carry no Tier weight -- DSR is computed once on
    the pooled series, never per-symbol.
    """

    model_config = ConfigDict(extra="allow")

    symbol: str
    n_trades: int
    pf: float
    sharpe: float
    round_trip_cost_pct: float
    cost_source: CostComponentSource


class EffectiveKDerivation(BaseModel):
    """How the effective-K point estimate was reached (spec Section 6.2).

    Makes K auditable: a future reader can see how the number was derived and
    challenge it rather than trusting an opaque hardcoded guess.
    """

    model_config = ConfigDict(extra="allow")

    method: str
    hypotheses_counted: int = 0
    symbols_per_hypothesis_avg: float = 0.0
    param_combos_recorded: int = 0
    param_combos_estimated: int = 0
    effective_k_point_estimate: int
    is_lower_bound: bool = True
    notes: str = ""


class StatisticalValidationEntry(BaseModel):
    """One retrospective DSR run's full result for a strategy (spec Section 3.0).

    Appended to ``statistical_validation_history``. Keyed on ``run_id`` for
    idempotent re-runs (spec Section 9.1): a re-run with the same ``run_id`` is
    a no-op append, so a crash midway through the 11 strategies is safely
    re-runnable.

    The base/conservative split (spec Section 6.5) is the core of the result:
    ``base_*`` is the realistic read (measured costs, point-estimate K and
    variance_sr); ``conservative_*`` is the worst-case read (padded costs, high
    K and variance_sr). The GATE uses the conservative tier; the report SHOWS
    both. ``fragility`` is ``base_tier != conservative_tier``.
    """

    model_config = ConfigDict(extra="allow")

    run_date: str
    run_id: str
    cost_model_version: str

    # Sample + pooled metrics (recomputed on the pooled, cost-adjusted,
    # quarantine-filtered per-trade series -- NOT carried from legacy backtests).
    n_trades_analyzed: int
    n_trades_quarantined: int = 0
    pf_raw: float
    pf_adjusted: float
    sharpe_raw: float
    sharpe_adjusted: float
    max_dd_pct_pooled_base: float
    max_dd_pct_pooled_adjusted: float
    skewness: float
    kurtosis: float

    # Effective K + variance_sr (both swept; see sensitivity tables below).
    effective_k: int
    effective_k_derivation: EffectiveKDerivation
    variance_sr: float

    # DSR at the gating (conservative) operating point.
    dsr_z_score: float
    dsr_p_value: float

    # Base vs conservative cases (spec Section 6.5).
    base_dsr_p_value: float
    conservative_dsr_p_value: float
    base_tier: Tier
    conservative_tier: Tier
    fragility: bool

    # Sensitivity sweeps (spec Sections 6.3, 6.4).
    dsr_k_sensitivity: list[KSensitivityCell] = Field(default_factory=list)
    dsr_variance_sr_sensitivity: list[VarianceSrSensitivityCell] = Field(
        default_factory=list
    )
    gating_k_used: int
    verdict_is_fragile: bool

    # Per-symbol descriptive breakdown (not gating).
    per_symbol_breakdown: list[PerSymbolBreakdown] = Field(default_factory=list)

    # Hard floors + final classification.
    hard_floor_status: HardFloorStatus
    classified_tier: Tier
    classification_reasoning: str

    # Reserved for Phase R1 (not computed retrospectively).
    pbo_score: float | None = None


class ClassificationHistoryEntry(BaseModel):
    """One entry in ``classification_history`` (PRD Appendix A).

    Appended (never overwritten) on each tier change. Keyed on ``triggered_by``
    (the ``run_id`` for retrospective runs) for idempotent re-runs.
    """

    model_config = ConfigDict(extra="allow")

    date: str
    classification: Tier
    triggered_by: str
    cost_model_version: str | None = None
    dsr_p_value: float | None = None
    notes: str = ""


class StrategyBiography(BaseModel):
    """Top-level strategy biography (PRD Appendix A).

    Only the classification + statistical-validation sections are owned and
    written by the retrospective DSR run. All other sections (hypothesis,
    parameter, optimization, backtest, paper, live, decay, decision_log,
    correlation, post_mortem) are preserved verbatim via ``extra="allow"`` so a
    load/modify/save cycle never drops hand-authored institutional memory.
    """

    model_config = ConfigDict(extra="allow", use_enum_values=True)

    strategy_id: str
    status: StrategyStatus
    symbols: list[str] = Field(default_factory=list)
    current_classification: Tier | None = None

    classification_history: list[ClassificationHistoryEntry] = Field(
        default_factory=list
    )
    statistical_validation_history: list[StatisticalValidationEntry] = Field(
        default_factory=list
    )
    decision_log: list[Any] = Field(default_factory=list)

    # Sections the retrospective does not own but must round-trip untouched.
    hypothesis_history: list[Any] = Field(default_factory=list)
    parameter_history: list[Any] = Field(default_factory=list)
    optimization_history: list[Any] = Field(default_factory=list)
    backtest_history: list[Any] = Field(default_factory=list)
    paper_trading_history: list[Any] = Field(default_factory=list)
    live_deployment_history: list[Any] = Field(default_factory=list)
    decay_events: list[Any] = Field(default_factory=list)
    reoptimization_history: list[Any] = Field(default_factory=list)
    correlation_with_portfolio: dict[str, float] = Field(default_factory=dict)
    post_mortem: Any | None = None

    def has_validation_run(self, run_id: str) -> bool:
        """Return True if a validation entry with ``run_id`` already exists.

        Used for the idempotent-write guard (spec Section 9.1): the orchestrator
        skips the append if the run already recorded a result for this strategy.

        Args:
            run_id: The retrospective run identifier to check for.

        Returns:
            True if an entry with this ``run_id`` is already present.
        """
        return any(e.run_id == run_id for e in self.statistical_validation_history)

    def has_classification_change(self, run_id: str) -> bool:
        """Return True if ``classification_history`` already has this ``run_id``.

        Args:
            run_id: The retrospective run identifier (used as ``triggered_by``).

        Returns:
            True if a classification entry triggered by this run is present.
        """
        return any(e.triggered_by == run_id for e in self.classification_history)
