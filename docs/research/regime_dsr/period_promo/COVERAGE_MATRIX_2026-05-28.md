# Regime-Conditional Backtest DSR -- Coverage Matrix

**Date:** 2026-05-28
**Source:** regenerated backtest trades (DEC-2026-06-04-014)
**Nature:** SCREEN, not a deployment gate -- paper/live validation still required (guard #1). DSR is necessary, not sufficient (guard #5).

Cells show the per-regime final tier and N. `[desc]` marks a DESCRIPTIVE cell (N < 20 or insufficient) that does NOT gate (guard #4). A blank cell means the strategy never traded in that regime (coverage gap).

| Strategy | Pooled | BULL | BEAR | CHOP |
|----------|--------|------|------|------|
| MACD_PB | TIER_D_REJECT (N=37) | -- | TIER_D_REJECT (N=35) | INSUFFICIENT_DATA (N=2 [desc]) |
| BTP | TIER_D_REJECT (N=75) | -- | TIER_D_REJECT (N=62) | TIER_D_REJECT (N=13 [desc]) |
| VBB | TIER_D_REJECT (N=35) | -- | TIER_D_REJECT (N=27) | INSUFFICIENT_DATA (N=8 [desc]) |
| SRC | TIER_D_REJECT (N=23) | -- | TIER_D_REJECT (N=21) | INSUFFICIENT_DATA (N=2 [desc]) |
| ICVP | TIER_D_REJECT (N=38) | -- | TIER_D_REJECT (N=30) | INSUFFICIENT_DATA (N=8 [desc]) |

## Coverage Gaps (non-descriptive Tier A/B by regime)

- **BULL**: NO gating Tier A/B coverage (GAP)
- **BEAR**: NO gating Tier A/B coverage (GAP)
- **CHOP**: NO gating Tier A/B coverage (GAP)

## Fine SubRegime Breakdown (DESCRIPTIVE -- never gating)

The coarse buckets merge trending+choppy within a direction, masking choppy-specific edge. These per-SubRegime cells expose where edge actually concentrates. **PF(adj) and Sharpe(adj) are K-independent**: PF(adj) > 1 with a positive Sharpe is a real (if thin) edge worth paper-trading even when the cell does not gate.

| Strategy | SubRegime | N | PF(adj) | Sharpe(adj) | base DSR p |
|----------|-----------|---|---------|-------------|------------|
| MACD_PB | choppy_bear * | 8 | 1.97 | +0.289 | 0.569 |
| MACD_PB | ranging * | 2 | 1.17 | +0.056 | 0.630 |
| MACD_PB | trending_bear | 27 | 0.73 | -0.141 | 0.995 |
| BTP | choppy_bear * | 21 | 1.40 | +0.141 | 0.904 |
| BTP | high_vol * | 3 | 999.99 | +4.412 | 0.023 |
| BTP | ranging | 10 | 0.64 | -0.206 | 0.952 |
| BTP | trending_bear * | 41 | 1.14 | +0.056 | 0.989 |
| VBB | choppy_bear * | 12 | 2.70 | +0.427 | 0.473 |
| VBB | high_vol * | 2 | 1.50 | +0.142 | 0.619 |
| VBB | ranging | 6 | 0.00 | -4.215 | 1.000 |
| VBB | trending_bear * | 15 | 1.19 | +0.072 | 0.915 |
| SRC | choppy_bear | 6 | 0.38 | -0.419 | 0.925 |
| SRC | ranging * | 2 | 999.99 | +3.221 | 0.129 |
| SRC | trending_bear * | 15 | 2.36 | +0.349 | 0.629 |
| ICVP | choppy_bear | 13 | 0.29 | -0.550 | 0.999 |
| ICVP | high_vol * | 6 | 2.13 | +0.351 | 0.525 |
| ICVP | ranging | 2 | 0.59 | -0.183 | 0.720 |
| ICVP | trending_bear * | 17 | 1.08 | +0.032 | 0.894 |

`*` = PF(adj) > 1 and Sharpe(adj) > 0 (a positive cost-adjusted edge in that SubRegime -- the cells worth paper-trading first).

## Honest Caveats

- This is a backtest SCREEN. Backtest edge degrades live; a pass means the pair is WORTH paper-trading, not that it will be profitable live.
- Costs are v0 unverified (incremental pad over already-net returns).
- Effective K includes the regime-bucket multiplier (guard #2), so per-bucket verdicts are deliberately harder to pass than the pooled one.
