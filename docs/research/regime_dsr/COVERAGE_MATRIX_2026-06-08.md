# Regime-Conditional Backtest DSR -- Coverage Matrix

**Date:** 2026-06-08
**Source:** regenerated backtest trades (DEC-2026-06-04-014)
**Nature:** SCREEN, not a deployment gate -- paper/live validation still required (guard #1). DSR is necessary, not sufficient (guard #5).

Cells show the per-regime final tier and N. `[desc]` marks a DESCRIPTIVE cell (N < 20 or insufficient) that does NOT gate (guard #4). A blank cell means the strategy never traded in that regime (coverage gap).

| Strategy | Pooled | BULL | BEAR | CHOP |
|----------|--------|------|------|------|
| DONCHIAN_ATR | TIER_D_REJECT (N=991) | TIER_D_REJECT (N=580) | TIER_D_REJECT (N=233) | TIER_D_REJECT (N=161) |

## Coverage Gaps (non-descriptive Tier A/B by regime)

- **BULL**: NO gating Tier A/B coverage (GAP)
- **BEAR**: NO gating Tier A/B coverage (GAP)
- **CHOP**: NO gating Tier A/B coverage (GAP)

## Fine SubRegime Breakdown (DESCRIPTIVE -- never gating)

The coarse buckets merge trending+choppy within a direction, masking choppy-specific edge. These per-SubRegime cells expose where edge actually concentrates. **PF(adj) and Sharpe(adj) are K-independent**: PF(adj) > 1 with a positive Sharpe is a real (if thin) edge worth paper-trading even when the cell does not gate.

| Strategy | SubRegime | N | PF(adj) | Sharpe(adj) | base DSR p |
|----------|-----------|---|---------|-------------|------------|
| DONCHIAN_ATR | choppy_bear | 97 | 0.42 | -0.407 | 1.000 |
| DONCHIAN_ATR | choppy_bull | 239 | 0.68 | -0.158 | 1.000 |
| DONCHIAN_ATR | high_vol | 99 | 0.90 | -0.045 | 1.000 |
| DONCHIAN_ATR | ranging | 62 | 0.53 | -0.298 | 1.000 |
| DONCHIAN_ATR | trending_bear | 136 | 0.34 | -0.504 | 1.000 |
| DONCHIAN_ATR | trending_bull | 341 | 0.59 | -0.235 | 1.000 |

`*` = PF(adj) > 1 and Sharpe(adj) > 0 (a positive cost-adjusted edge in that SubRegime -- the cells worth paper-trading first).

## Honest Caveats

- This is a backtest SCREEN. Backtest edge degrades live; a pass means the pair is WORTH paper-trading, not that it will be profitable live.
- Costs are v0 unverified (incremental pad over already-net returns).
- Effective K includes the regime-bucket multiplier (guard #2), so per-bucket verdicts are deliberately harder to pass than the pooled one.
