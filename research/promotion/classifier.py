"""Tier A/B/C/D classification + non-negotiable hard floors (PRD Section 9).

Classification is MECHANICAL: objective criteria, no manual override
(DEC-2026-06-04-008). This module encodes the tier table (PRD Section 9.1) and
the base-vs-conservative resolution (spec Section 6.5).

THE GATE: the final classified tier is the CONSERVATIVE case (padded costs,
highest defensible K, high variance_sr). A strategy only earns a deployable tier
if it survives the worst-case assumptions.

THE ONE SOFTENING (reconciling spec 6.3 and 6.5): a strategy with real BASE-case
edge (Tier A or B at the realistic operating point) that collapses to Tier D
ONLY under stacked worst-case assumptions is "real-but-fragile". It is classified
Tier C (NEEDS_WORK -- gather more data) rather than Tier D (REJECT -- retire),
because the evidence says "works but does not yet clear the strict gate", which
is exactly the case the Tier system was built to hold without an override path.
A strategy that is Tier D in BOTH cases has genuinely no edge and is safe to
retire.

Research-only module: ``src/`` must never import from here (PRD Section 5.2).
"""
from __future__ import annotations

from research.biographies.schema import HardFloorStatus, Tier

# Tier soft-threshold table (PRD Section 9.1 / 9.3 / 9.4).
TIER_A_DSR_P_MAX: float = 0.20
TIER_A_PF_MIN: float = 1.35
TIER_A_SHARPE_MIN: float = 1.0
TIER_A_N_MIN: int = 30
TIER_A_MAX_DD_MAX: float = 5.0

TIER_B_DSR_P_MAX: float = 0.30
TIER_B_PF_MIN: float = 1.25
TIER_B_SHARPE_MIN: float = 0.8
TIER_B_N_MIN: int = 20
TIER_B_MAX_DD_MAX: float = 5.0

# Hard floors (PRD Section 9.2).
DSR_P_HARD_FLOOR: float = 0.30  # p >= this cannot be Tier A or B at any allocation
TIER_D_DSR_P: float = 0.50  # p >= this is statistical noise -> reject
TIER_D_MAX_DD: float = 10.0  # MaxDD >= this is unacceptable risk -> reject

# Minimum N below which DSR's skew/kurtosis moments are not meaningful, so the
# verdict is not computable as evidence at all. Below this a strategy or regime
# bucket is reported INSUFFICIENT_DATA -- DESCRIPTIVE, not a reject
# (DEC-2026-06-04-014). This is distinct from the Tier B N>=20 DEPLOYMENT floor:
# 10 is the floor for the verdict being meaningful; 20 is the floor for
# deploying. A genuinely edge-less strategy with enough trades still earns
# TIER_D; only data SCARCITY yields INSUFFICIENT_DATA. The 2026-06-05 Neon run's
# N=0..4 strategies were wrongly shown as TIER_D_REJECT; this guard prevents that
# "no data" -> "proven noise" misread.
MIN_N_FOR_CLASSIFICATION: int = 10


def classify_tier(
    dsr_p_value: float,
    max_dd_pct: float,
    pf: float,
    sharpe: float,
    n_trades: int,
) -> Tier:
    """Mechanically classify one operating point into a Tier (PRD Section 9.1).

    No override. Order matters: reject conditions are checked first, then Tier A
    (strictest), then Tier B, then Tier C as the residual for anything that
    clears the Tier-D reject conditions but misses A/B.

    Args:
        dsr_p_value: Deflated Sharpe p-value (LOW is good); the gating field.
        max_dd_pct: Max drawdown as a percentage (recomputed on the pooled,
            cost-adjusted series -- spec Section 9.1).
        pf: Profit factor for this operating point.
        sharpe: Per-trade Sharpe for this operating point.
        n_trades: Number of trades analyzed (same across cases).

    Returns:
        The ``Tier`` for this operating point. ``INSUFFICIENT_DATA`` when
        ``n_trades`` is below ``MIN_N_FOR_CLASSIFICATION`` (no meaningful verdict
        possible -- distinct from a reject).
    """
    # Insufficient data: below this N the DSR moments are not meaningful, so the
    # verdict is not computable as evidence. Report it as such -- NOT as a reject
    # (DEC-2026-06-04-014). Checked FIRST so a degenerate DSR p-value (e.g. p=1.0
    # at N=0) can never masquerade as TIER_D.
    if n_trades < MIN_N_FOR_CLASSIFICATION:
        return Tier.INSUFFICIENT_DATA

    # Tier D (reject): statistical noise or unacceptable risk.
    if dsr_p_value >= TIER_D_DSR_P or max_dd_pct >= TIER_D_MAX_DD:
        return Tier.TIER_D

    # Tier A (full ready): all strict thresholds + DSR p<0.2 + MaxDD<5%.
    if (
        dsr_p_value < TIER_A_DSR_P_MAX
        and max_dd_pct < TIER_A_MAX_DD_MAX
        and pf >= TIER_A_PF_MIN
        and sharpe >= TIER_A_SHARPE_MIN
        and n_trades >= TIER_A_N_MIN
    ):
        return Tier.TIER_A

    # Tier B (provisional ready): relaxed thresholds + DSR p<0.3 + MaxDD<5%.
    if (
        dsr_p_value < TIER_B_DSR_P_MAX
        and max_dd_pct < TIER_B_MAX_DD_MAX
        and pf >= TIER_B_PF_MIN
        and sharpe >= TIER_B_SHARPE_MIN
        and n_trades >= TIER_B_N_MIN
    ):
        return Tier.TIER_B

    # Tier C (needs work): clears the reject conditions but misses A/B.
    return Tier.TIER_C


def resolve_final_tier(base_tier: Tier, conservative_tier: Tier) -> tuple[Tier, bool]:
    """Resolve the final tier from the base and conservative operating points.

    Gates on the conservative case (spec Section 6.5) with one softening: a
    real-but-fragile strategy (deployable in the base case, Tier D only under
    stacked worst-cases) is held at Tier C for more data rather than retired.

    Args:
        base_tier: Tier at the realistic (measured costs, point-estimate K +
            variance_sr) operating point.
        conservative_tier: Tier at the worst-case (padded costs, highest K, high
            variance_sr) operating point.

    Returns:
        A tuple ``(final_tier, fragility)`` where ``fragility`` is
        ``base_tier != conservative_tier``.
    """
    fragility = base_tier != conservative_tier
    final_tier = conservative_tier

    base_is_deployable = base_tier in (Tier.TIER_A, Tier.TIER_B)
    if fragility and base_is_deployable and conservative_tier == Tier.TIER_D:
        # Real-but-fragile: edge is real at the realistic operating point but
        # collapses under stacked worst-cases. Needs more data, not retirement.
        final_tier = Tier.TIER_C

    return final_tier, fragility


def build_hard_floor_status(
    conservative_dsr_p_value: float,
    conservative_max_dd_pct: float,
    cost_model_verified: bool,
    leakage_check: str = "not_run",
) -> HardFloorStatus:
    """Record the non-negotiable hard-floor pass/fail (PRD Section 9.2).

    These are DEPLOYMENT floors. In a retrospective with the v0 unverified cost
    model, ``cost_model_verified`` is False and ``leakage_check`` is "not_run":
    both are recorded as audit facts that block live deployment, but they do not
    by themselves change the retrospective tier (which answers "what tier would
    this be"). This matches the spec Section 3.0 example (Tier A recorded with
    ``cost_model_verified: false``).

    Args:
        conservative_dsr_p_value: Gating-case DSR p-value.
        conservative_max_dd_pct: Gating-case max drawdown percentage.
        cost_model_verified: Whether the cost model is verified (False for v0).
        leakage_check: Leakage-check status string (default "not_run").

    Returns:
        A populated ``HardFloorStatus``.
    """
    return HardFloorStatus(
        dsr_passed=conservative_dsr_p_value < DSR_P_HARD_FLOOR,
        max_dd_passed=conservative_max_dd_pct < TIER_A_MAX_DD_MAX,
        cost_model_verified=cost_model_verified,
        leakage_check=leakage_check,
    )


def recommended_action(tier: Tier) -> str:
    """Map a final tier to the operator-facing recommended action.

    Args:
        tier: The final classified tier.

    Returns:
        A short machine-friendly action token (also used in the JSON output).
    """
    return {
        Tier.TIER_A: "continue_full",
        Tier.TIER_B: "continue_half",
        Tier.TIER_C: "halt_needs_work",
        Tier.TIER_D: "retire",
        Tier.BELOW_FLOOR: "halt_needs_work",
        Tier.INSUFFICIENT_DATA: "gather_more_data",
    }[tier]


def action_description(tier: Tier) -> str:
    """Human-readable recommended action for markdown reports (PRD Section 9).

    Args:
        tier: The final classified tier.

    Returns:
        A human-readable recommendation sentence.
    """
    return {
        Tier.TIER_A: "Continue at 100% of per-strategy slice (Tier A FULL_READY).",
        Tier.TIER_B: "Continue at 50% of per-strategy slice (Tier B PROVISIONAL_READY).",
        Tier.TIER_C: "Halt and re-evaluate -- gather more data or re-optimize (Tier C).",
        Tier.TIER_D: "Retire -- no statistically distinguishable edge (Tier D REJECT).",
        Tier.BELOW_FLOOR: "Halt -- below the deployment floor.",
        Tier.INSUFFICIENT_DATA: (
            "Insufficient data -- N below the minimum for a meaningful DSR. "
            "Gather more trades; NOT a reject."
        ),
    }[tier]
