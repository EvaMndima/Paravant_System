# Regime-Conditional Backtest DSR -- Coverage Matrix

**Date:** 2026-06-06
**Source:** regenerated backtest trades (DEC-2026-06-04-014)
**Nature:** SCREEN, not a deployment gate -- paper/live validation still required (guard #1). DSR is necessary, not sufficient (guard #5).

Cells show the per-regime final tier and N. `[desc]` marks a DESCRIPTIVE cell (N < 20 or insufficient) that does NOT gate (guard #4). A blank cell means the strategy never traded in that regime (coverage gap).

| Strategy | Pooled | BULL | BEAR | CHOP |
|----------|--------|------|------|------|
| BTF | TIER_D_REJECT (N=997) | TIER_D_REJECT (N=411) | TIER_D_REJECT (N=375) | TIER_D_REJECT (N=201) |

## Coverage Gaps (non-descriptive Tier A/B by regime)

- **BULL**: NO gating Tier A/B coverage (GAP)
- **BEAR**: NO gating Tier A/B coverage (GAP)
- **CHOP**: NO gating Tier A/B coverage (GAP)

## Honest Caveats

- This is a backtest SCREEN. Backtest edge degrades live; a pass means the pair is WORTH paper-trading, not that it will be profitable live.
- Costs are v0 unverified (incremental pad over already-net returns).
- Effective K includes the regime-bucket multiplier (guard #2), so per-bucket verdicts are deliberately harder to pass than the pooled one.
