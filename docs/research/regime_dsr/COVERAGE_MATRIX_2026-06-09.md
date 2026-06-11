# Regime-Conditional Backtest DSR -- Coverage Matrix

**Date:** 2026-06-09
**Source:** regenerated backtest trades (DEC-2026-06-04-014)
**Nature:** SCREEN, not a deployment gate -- paper/live validation still required (guard #1). DSR is necessary, not sufficient (guard #5).

Cells show the per-regime final tier and N. `[desc]` marks a DESCRIPTIVE cell (N < 20 or insufficient) that does NOT gate (guard #4). A blank cell means the strategy never traded in that regime (coverage gap).

| Strategy | Pooled | BULL | BEAR | CHOP |
|----------|--------|------|------|------|
| FUNDING_CONTRARIAN_V2 | TIER_D_REJECT (N=133) | TIER_D_REJECT (N=64) | TIER_D_REJECT (N=26) | TIER_D_REJECT (N=42) |

## Coverage Gaps (non-descriptive Tier A/B by regime)

- **BULL**: NO gating Tier A/B coverage (GAP)
- **BEAR**: NO gating Tier A/B coverage (GAP)
- **CHOP**: NO gating Tier A/B coverage (GAP)

## Fine SubRegime Breakdown (DESCRIPTIVE -- never gating)

The coarse buckets merge trending+choppy within a direction, masking choppy-specific edge. These per-SubRegime cells expose where edge actually concentrates. **PF(adj) and Sharpe(adj) are K-independent**: PF(adj) > 1 with a positive Sharpe is a real (if thin) edge worth paper-trading even when the cell does not gate.

| Strategy | SubRegime | N | PF(adj) | Sharpe(adj) | base DSR p |
|----------|-----------|---|---------|-------------|------------|
| FUNDING_CONTRARIAN_V2 | choppy_bear | 15 | 0.35 | -0.518 | 0.992 |
| FUNDING_CONTRARIAN_V2 | choppy_bull | 21 | 0.30 | -0.571 | 0.998 |
| FUNDING_CONTRARIAN_V2 | high_vol | 28 | 0.95 | -0.026 | 0.960 |
| FUNDING_CONTRARIAN_V2 | ranging | 14 | 0.11 | -1.163 | 0.986 |
| FUNDING_CONTRARIAN_V2 | trending_bear | 11 | 0.96 | -0.019 | 0.839 |
| FUNDING_CONTRARIAN_V2 | trending_bull | 43 | 0.38 | -0.465 | 1.000 |

`*` = PF(adj) > 1 and Sharpe(adj) > 0 (a positive cost-adjusted edge in that SubRegime -- the cells worth paper-trading first).

## Honest Caveats

- This is a backtest SCREEN. Backtest edge degrades live; a pass means the pair is WORTH paper-trading, not that it will be profitable live.
- Costs are v0 unverified (incremental pad over already-net returns).
- Effective K includes the regime-bucket multiplier (guard #2), so per-bucket verdicts are deliberately harder to pass than the pooled one.
