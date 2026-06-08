# Regime-Conditional Backtest DSR -- Coverage Matrix

**Date:** 2026-06-07
**Source:** regenerated backtest trades (DEC-2026-06-04-014)
**Nature:** SCREEN, not a deployment gate -- paper/live validation still required (guard #1). DSR is necessary, not sufficient (guard #5).

Cells show the per-regime final tier and N. `[desc]` marks a DESCRIPTIVE cell (N < 20 or insufficient) that does NOT gate (guard #4). A blank cell means the strategy never traded in that regime (coverage gap).

| Strategy | Pooled | BULL | BEAR | CHOP |
|----------|--------|------|------|------|
| MACD_PB | TIER_D_REJECT (N=113) | TIER_D_REJECT (N=64) | TIER_D_REJECT (N=35) | TIER_D_REJECT (N=13 [desc]) |
| BTP | TIER_D_REJECT (N=409) | TIER_D_REJECT (N=242) | TIER_D_REJECT (N=99) | TIER_D_REJECT (N=65) |
| VBB | TIER_D_REJECT (N=153) | TIER_D_REJECT (N=89) | TIER_D_REJECT (N=40) | TIER_D_REJECT (N=22) |
| SRC | TIER_D_REJECT (N=132) | TIER_D_REJECT (N=70) | TIER_D_REJECT (N=39) | TIER_D_REJECT (N=22) |
| ICVP | TIER_D_REJECT (N=149) | TIER_D_REJECT (N=85) | TIER_D_REJECT (N=35) | TIER_D_REJECT (N=26) |

## Coverage Gaps (non-descriptive Tier A/B by regime)

- **BULL**: NO gating Tier A/B coverage (GAP)
- **BEAR**: NO gating Tier A/B coverage (GAP)
- **CHOP**: NO gating Tier A/B coverage (GAP)

## Fine SubRegime Breakdown (DESCRIPTIVE -- never gating)

The coarse buckets merge trending+choppy within a direction, masking choppy-specific edge. These per-SubRegime cells expose where edge actually concentrates. **PF(adj) and Sharpe(adj) are K-independent**: PF(adj) > 1 with a positive Sharpe is a real (if thin) edge worth paper-trading even when the cell does not gate.

| Strategy | SubRegime | N | PF(adj) | Sharpe(adj) | base DSR p |
|----------|-----------|---|---------|-------------|------------|
| MACD_PB | choppy_bear | 14 | 0.76 | -0.122 | 0.909 |
| MACD_PB | choppy_bull | 29 | 0.84 | -0.082 | 0.976 |
| MACD_PB | high_vol | 3 | 0.00 | -2.646 | 0.977 |
| MACD_PB | ranging | 10 | 0.85 | -0.074 | 0.848 |
| MACD_PB | trending_bear | 21 | 0.97 | -0.012 | 0.898 |
| MACD_PB | trending_bull | 35 | 0.68 | -0.178 | 0.996 |
| BTP | choppy_bear | 33 | 0.81 | -0.092 | 0.980 |
| BTP | choppy_bull | 97 | 0.58 | -0.241 | 1.000 |
| BTP | high_vol | 19 | 0.50 | -0.284 | 0.989 |
| BTP | ranging * | 46 | 1.22 | +0.086 | 0.897 |
| BTP | trending_bear | 66 | 0.88 | -0.057 | 0.997 |
| BTP | trending_bull | 145 | 0.77 | -0.116 | 1.000 |
| VBB | choppy_bear * | 18 | 1.38 | +0.140 | 0.736 |
| VBB | choppy_bull * | 42 | 1.20 | +0.078 | 0.936 |
| VBB | high_vol * | 5 | 1.08 | +0.032 | 0.720 |
| VBB | ranging | 17 | 0.23 | -0.685 | 0.994 |
| VBB | trending_bear | 22 | 0.69 | -0.157 | 0.972 |
| VBB | trending_bull | 47 | 0.39 | -0.439 | 1.000 |
| SRC | choppy_bear | 11 | 0.38 | -0.446 | 0.964 |
| SRC | choppy_bull * | 32 | 1.06 | +0.026 | 0.949 |
| SRC | high_vol * | 9 | 1.30 | +0.115 | 0.720 |
| SRC | ranging * | 13 | 1.47 | +0.169 | 0.669 |
| SRC | trending_bear | 28 | 0.89 | -0.047 | 0.966 |
| SRC | trending_bull | 38 | 0.37 | -0.456 | 1.000 |
| ICVP | choppy_bear | 17 | 0.40 | -0.393 | 0.995 |
| ICVP | choppy_bull * | 38 | 1.01 | +0.003 | 0.937 |
| ICVP | high_vol | 15 | 0.42 | -0.382 | 0.994 |
| ICVP | ranging | 11 | 0.83 | -0.077 | 0.829 |
| ICVP | trending_bear | 18 | 0.96 | -0.017 | 0.853 |
| ICVP | trending_bull | 47 | 0.85 | -0.072 | 0.991 |

`*` = PF(adj) > 1 and Sharpe(adj) > 0 (a positive cost-adjusted edge in that SubRegime -- the cells worth paper-trading first).

## Honest Caveats

- This is a backtest SCREEN. Backtest edge degrades live; a pass means the pair is WORTH paper-trading, not that it will be profitable live.
- Costs are v0 unverified (incremental pad over already-net returns).
- Effective K includes the regime-bucket multiplier (guard #2), so per-bucket verdicts are deliberately harder to pass than the pooled one.
