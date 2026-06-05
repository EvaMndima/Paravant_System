"""Per-symbol conservative cost model for the retrospective DSR (spec Section 5).

This module answers one question per trade: "after honest, conservative trading
costs, what is the per-trade return?" It is deliberately conservative (v0
unverified) so that a strategy surviving it is more likely to carry real edge.

DATA REALITY (confirmed during 2026-06-05 reconnaissance, differs from the
spec's first-draft assumptions):

- The canonical trade source is ``PaperTradingSession.trade_log`` (a JSON array
  of ``TradeRecord`` dicts), NOT a ``paper_trades`` SQL table.
- There is NO ``signal_price`` or ``fill_price`` field. ``entry_price`` and
  ``exit_price`` ARE the post-slippage fill prices. So spec Section 5.1's
  "compute realized slippage from signal vs fill" is NOT achievable from this
  data; slippage is necessarily an ESTIMATED (padded) component for every
  symbol. This is recorded as a caveat in every biography.
- The recorded ``return_pct`` / ``realized_pnl`` are ALREADY net of the
  simulator's commission and (for paper) slippage. Re-subtracting a full cost
  model would double-charge.

COST APPLICATION DECISION (operator Eva, 2026-06-05): "Incremental pad only."
The recorded net return is the realistic BASE case (it already embeds measured /
real costs). The CONSERVATIVE case subtracts only the EXCESS of the v0
conservative cost model over what the simulator already booked, floored at zero.
This avoids any double-count while still stress-testing each strategy against a
harsher cost assumption. Concretely, per trade::

    booked_cost_pct        = (entry_commission + exit_commission + slippage_cost)
                             / entry_notional * 100
    conservative_cost_pct  = leg-aware round-trip of (padded spread + fee +
                             padded slippage)
    incremental_pad_pct    = max(0, conservative_cost_pct - booked_cost_pct)
    base_return_pct        = recorded return_pct                  (unchanged)
    conservative_return_pct = recorded return_pct - incremental_pad_pct

SINGLE-PAD CONSERVATISM (spec Section 5.2): the 2x pad is applied ONLY to
components that remain ESTIMATED (spread and slippage here, since neither is
measurable from this data). The taker fee is known exactly and is NEVER padded.
We never stack a 95th-percentile measured value AND a 2x pad on the same
quantity.

NOTIONAL BASE PER LEG (spec Section 5.5-pre): the entry-leg cost is charged on
entry notional, the exit-leg cost on EXIT notional. In return-percentage space
this means the exit-leg cost is scaled by ``exit_price / entry_price`` (the
notional ratio), so a large winner's exit-leg cost is not silently understated.

Research-only module: ``src/`` must never import from here (PRD Section 5.2).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from research.biographies.schema import CostComponentSource
from src.utils.logging import get_logger

logger = get_logger(__name__)


# v0 default cost model parameters (spec Section 2.3). 2x conservative pad on
# ESTIMATED components only.
DEFAULT_SPREAD_PCT_BY_SYMBOL: dict[str, float] = {
    "BTCUSDT": 0.02,
    "ETHUSDT": 0.04,
    "BNBUSDT": 0.05,
    "SOLUSDT": 0.08,
    "AVAXUSDT": 0.10,
    "DOGEUSDT": 0.15,
    "XRPUSDT": 0.08,
    "DOTUSDT": 0.10,
}
FALLBACK_SPREAD_PCT: float = 0.20  # extra-conservative default for unlisted symbols
BINANCE_TAKER_FEE_PCT: float = 0.10  # worst case (0.075 with BNB); never padded
SLIPPAGE_PCT_DEFAULT: float = 0.05  # per-side; padded because it is unmeasurable here
ESTIMATE_PAD: float = 2.0  # 2x conservative multiplier on ESTIMATED components


@dataclass(frozen=True)
class CostModel:
    """Per-symbol cost model parameters (spec Section 5).

    Attributes:
        version: Cost-model version tag written into the biography audit trail.
        default_spread_pct_by_symbol: Per-symbol assumed half-spread reference
            (full spread; halved per side in the round-trip formula).
        fallback_spread_pct: Spread assumed for symbols not in the table.
        taker_fee_pct: Binance taker fee, known exactly, never padded.
        slippage_pct_default: Per-side slippage assumption (ESTIMATED, padded).
        estimate_pad: Multiplier applied ONLY to ESTIMATED components.
        measured_spreads_pct: Per-symbol measured (p95) spreads; empty in v0
            because no order-book history is available. Present so the same code
            path serves the v1_verified upgrade (spec Section 5.4).
        measured_slippage_pct: Per-symbol measured slippage; empty in v0 because
            no signal/fill prices exist in the trade logs.
    """

    version: str
    default_spread_pct_by_symbol: dict[str, float]
    fallback_spread_pct: float
    taker_fee_pct: float
    slippage_pct_default: float
    estimate_pad: float
    measured_spreads_pct: dict[str, float] = field(default_factory=dict)
    measured_slippage_pct: dict[str, float] = field(default_factory=dict)

    @classmethod
    def v0_unverified(cls) -> CostModel:
        """Construct the v0 (unverified, 2x conservative) cost model.

        Returns:
            A ``CostModel`` with the spec Section 2.3 defaults and no measured
            components (everything spread/slippage is ESTIMATED and padded).
        """
        return cls(
            version="v0_unverified",
            default_spread_pct_by_symbol=dict(DEFAULT_SPREAD_PCT_BY_SYMBOL),
            fallback_spread_pct=FALLBACK_SPREAD_PCT,
            taker_fee_pct=BINANCE_TAKER_FEE_PCT,
            slippage_pct_default=SLIPPAGE_PCT_DEFAULT,
            estimate_pad=ESTIMATE_PAD,
        )


@dataclass(frozen=True)
class CostBreakdown:
    """Transparent per-trade cost breakdown for operator sanity-checking.

    Attributes:
        symbol: Trading pair.
        spread_pct_used: Full spread (%) used for this trade (post-pad if estimated).
        spread_source: Whether the spread was MEASURED or ESTIMATED.
        slippage_pct_used: Per-side slippage (%) used (post-pad if estimated).
        slippage_source: Whether the slippage was MEASURED or ESTIMATED.
        fee_pct: Taker fee (%) per side.
        cost_per_side_pct: spread/2 + fee + slippage for one side.
        exit_leg_scale: exit_price / entry_price (the notional ratio).
        conservative_round_trip_cost_pct: Leg-aware round-trip cost as a % of
            entry notional (entry leg + exit leg scaled by ``exit_leg_scale``).
        booked_cost_pct: Cost already embedded in the recorded return (%).
        incremental_pad_pct: max(0, conservative - booked), the extra cost the
            conservative case charges beyond what the simulator already booked.
    """

    symbol: str
    spread_pct_used: float
    spread_source: CostComponentSource
    slippage_pct_used: float
    slippage_source: CostComponentSource
    fee_pct: float
    cost_per_side_pct: float
    exit_leg_scale: float
    conservative_round_trip_cost_pct: float
    booked_cost_pct: float
    incremental_pad_pct: float


@dataclass(frozen=True)
class AdjustedReturn:
    """Result of applying the cost model to one trade.

    Attributes:
        base_return_pct: The recorded (already net of in-sim costs) per-trade
            return. This is the BASE case (spec Section 6.5).
        conservative_return_pct: ``base_return_pct - incremental_pad_pct``. This
            is the CONSERVATIVE case the hard floor gates on.
        breakdown: The full cost breakdown for audit / operator sanity-check.
    """

    base_return_pct: float
    conservative_return_pct: float
    breakdown: CostBreakdown


def _entry_notional(trade: dict[str, object]) -> float:
    """Return entry notional (entry_price * quantity), or 0.0 if unavailable."""
    entry_price = float(trade.get("entry_price", 0.0) or 0.0)
    quantity = float(trade.get("quantity", 0.0) or 0.0)
    return entry_price * quantity


def booked_cost_pct(trade: dict[str, object]) -> float:
    """Cost already embedded in the recorded return, as a % of entry notional.

    The recorded ``return_pct`` is net of the simulator's costs. To avoid
    double-counting (operator decision 2026-06-05), the conservative case
    subtracts only the EXCESS over this booked cost. The booked cost is the sum
    of the recorded entry/exit commissions plus the recorded slippage cost
    (present on paper records; absent on live records, where real slippage is
    embedded in the fill prices and is treated as 0 additional booked cost).

    Args:
        trade: One serialized ``TradeRecord`` dict.

    Returns:
        Booked round-trip cost as a percentage of entry notional. Returns 0.0
        when the entry notional is non-positive (cannot form a percentage).
    """
    notional = _entry_notional(trade)
    if notional <= 0.0:
        return 0.0
    entry_commission = float(trade.get("entry_commission", 0.0) or 0.0)
    exit_commission = float(trade.get("exit_commission", 0.0) or 0.0)
    slippage_cost = float(trade.get("slippage_cost", 0.0) or 0.0)
    booked = entry_commission + exit_commission + slippage_cost
    return booked / notional * 100.0


def compute_cost_breakdown(trade: dict[str, object], cost_model: CostModel) -> CostBreakdown:
    """Compute the conservative, leg-aware cost breakdown for one trade.

    Applies the single-pad rule (only ESTIMATED components get the 2x pad) and
    the per-leg notional rule (exit leg scaled by ``exit_price / entry_price``).

    Args:
        trade: One serialized ``TradeRecord`` dict.
        cost_model: The cost model to apply.

    Returns:
        A fully populated ``CostBreakdown``.
    """
    symbol = str(trade.get("symbol", "UNKNOWN"))

    # Spread: measured (p95, no pad) if available; else default x pad.
    if symbol in cost_model.measured_spreads_pct:
        spread_pct = cost_model.measured_spreads_pct[symbol]
        spread_source = CostComponentSource.MEASURED
    else:
        base_spread = cost_model.default_spread_pct_by_symbol.get(
            symbol, cost_model.fallback_spread_pct
        )
        spread_pct = base_spread * cost_model.estimate_pad
        spread_source = CostComponentSource.ESTIMATED

    # Slippage: measured (no pad) if available; else default x pad. In v0 there
    # is never measured slippage (no signal/fill prices), so this is always the
    # ESTIMATED branch -- recorded for audit honesty.
    if symbol in cost_model.measured_slippage_pct:
        slippage_pct = cost_model.measured_slippage_pct[symbol]
        slippage_source = CostComponentSource.MEASURED
    else:
        slippage_pct = cost_model.slippage_pct_default * cost_model.estimate_pad
        slippage_source = CostComponentSource.ESTIMATED

    fee_pct = cost_model.taker_fee_pct  # known exactly, never padded

    # Cross half the spread per side; fee + slippage charged per side.
    cost_per_side_pct = spread_pct / 2.0 + fee_pct + slippage_pct

    # Per-leg notional: exit leg scaled by exit/entry price ratio (spec 5.5-pre).
    entry_price = float(trade.get("entry_price", 0.0) or 0.0)
    exit_price = float(trade.get("exit_price", 0.0) or 0.0)
    if entry_price > 0.0 and exit_price > 0.0:
        exit_leg_scale = exit_price / entry_price
    else:
        exit_leg_scale = 1.0  # degenerate; charge symmetric round trip

    conservative_round_trip_cost_pct = cost_per_side_pct * (1.0 + exit_leg_scale)

    booked = booked_cost_pct(trade)
    incremental = max(0.0, conservative_round_trip_cost_pct - booked)

    return CostBreakdown(
        symbol=symbol,
        spread_pct_used=spread_pct,
        spread_source=spread_source,
        slippage_pct_used=slippage_pct,
        slippage_source=slippage_source,
        fee_pct=fee_pct,
        cost_per_side_pct=cost_per_side_pct,
        exit_leg_scale=exit_leg_scale,
        conservative_round_trip_cost_pct=conservative_round_trip_cost_pct,
        booked_cost_pct=booked,
        incremental_pad_pct=incremental,
    )


def apply_cost_model(trade: dict[str, object], cost_model: CostModel) -> AdjustedReturn:
    """Apply the incremental-pad cost model to one trade.

    Args:
        trade: One serialized ``TradeRecord`` dict with at least ``return_pct``,
            ``entry_price``, ``exit_price``, ``quantity``, ``symbol``.
        cost_model: The cost model to apply.

    Returns:
        An ``AdjustedReturn`` with the base (recorded) and conservative
        (recorded minus incremental pad) per-trade returns plus the breakdown.
    """
    recorded_return_pct = float(trade.get("return_pct", 0.0) or 0.0)
    breakdown = compute_cost_breakdown(trade, cost_model)
    conservative_return_pct = recorded_return_pct - breakdown.incremental_pad_pct
    return AdjustedReturn(
        base_return_pct=recorded_return_pct,
        conservative_return_pct=conservative_return_pct,
        breakdown=breakdown,
    )


def mean_round_trip_cost_pct_by_symbol(
    trades: list[dict[str, object]], cost_model: CostModel
) -> dict[str, float]:
    """Average conservative round-trip cost (%) per symbol, for operator review.

    The spec (Section 5.3) requires the runner to PRINT the per-symbol
    round-trip cost so the operator can sanity-check it before trusting any
    verdict. This computes those averages.

    Args:
        trades: All (quarantine-filtered) trades for a strategy.
        cost_model: The cost model to apply.

    Returns:
        Mapping of symbol -> mean conservative round-trip cost percentage.
    """
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for trade in trades:
        breakdown = compute_cost_breakdown(trade, cost_model)
        symbol = breakdown.symbol
        totals[symbol] = totals.get(symbol, 0.0) + breakdown.conservative_round_trip_cost_pct
        counts[symbol] = counts.get(symbol, 0) + 1
    return {sym: totals[sym] / counts[sym] for sym in totals if counts[sym] > 0}
