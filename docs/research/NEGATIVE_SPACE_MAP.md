# Negative-Space Map -- Mechanism x Regime Coverage

**Status:** BY-HAND coverage map (DEC-2026-06-04-018; tooling deferred).
**Purpose:** Direct sourcing at the UNEXPLORED complement. Every rejection is
data: a dead cell tells us where NOT to look; a FIXABLE near-miss is a seedbed
for a corrected hypothesis; an unexplored cell is where the next trial should go.
**Owner:** Eva (operator) + Claude. Updated each loop iteration.

This is a NEGATIVE-SPACE MAP, not a generator. Failures steer HUMAN mechanism
choice; they NEVER feed an algorithm that emits new strategy specs
(DEC-2026-06-04-006 / -018, the auto-discovery non-goal).

---

## Coverage grid (mechanism family x regime)

Legend: `DEAD` = no net edge, FUNDAMENTAL; `WEAK` = tested, decayed / below floor;
`THIN` = INSUFFICIENT_DATA (no verdict); `UNEXPLORED` = not yet tested;
`--` = not applicable / not designed for that regime.

| Mechanism family | trending_bull | choppy_bull | choppy_bear | trending_bear | ranging |
|---|---|---|---|---|---|
| Pullback-in-trend (BTP active, MACD_PB retired) | WEAK | WEAK | WEAK (decayed) | -- | -- |
| Breakout-continuation, price-only (donchian_atr H-002) | **DEAD** | WEAK | WEAK | DEAD | WEAK |
| Volatility/squeeze breakout (VRB retired) | THIN (BTC-only) | -- | -- | -- | -- |
| Classic-TA mean-reversion (RSI_BB retired) | DEAD | -- | DEAD | DEAD | DEAD |
| Momentum/short-side (CMF, BTF, HATP retired) | -- | -- | DEAD/overfit | DEAD/overfit | -- |
| Volume-price momentum (VPT retired) | -- | -- | -- | -- | break-even (cost-dead) |
| **Derivatives-flow / funding (H-003)** | **UNEXPLORED** | UNEXPLORED | -- | -- | -- |

**Headline:** TRENDING_BULL remains UNCOVERED. The two price-only mechanisms most
people reach for first -- pullback-in-trend and breakout-continuation -- are now
exhausted there (WEAK and DEAD respectively, both on large samples). The next
genuinely untested mechanism for the gap is the derivatives-flow one (funding),
which is exactly why H-2026-06-003 is the higher-value remaining survivor.

---

## Rejection log

### Stage 1 -- reasoning gate (cost: minutes, no DSR trial)

| Idea | Date | Reason | Tag |
|---|---|---|---|
| Buy-the-dip trend pullback (trending_bull) | 2026-06-08 | Duplicate of active BTP (`bull_trend_pullback`) and retired MACD_PB pullback family; no stated differentiator. Failed the "not a known-dead/duplicate pattern" hard gate. | DUPLICATE |

### Stage 3 -- DSR evidence gate (cost: one trial / K)

| Hypothesis | Date | Result | Tag |
|---|---|---|---|
| H-2026-06-002 breakout-continuation (`donchian_atr`, liquid-major 1H spot) | 2026-06-08 | TIER_D in every regime; target trending_bull PF-adj 0.59 / Sharpe -0.235 at N=341 (large sample), DSR p=1.0. Crowding + cost fail modes fired as pre-registered (inverse-crowding scored 1/3 at Stage 1). | **FUNDAMENTAL** |

---

## FIXABLE seedbeds (distinct NEW hypotheses, not revisits)

These are NOT instructions to re-run a dead spec. Each would be a fresh
pre-registered hypothesis with its own mechanism statement, and only worth a DSR
trial if the new mechanism is genuinely sharper.

- **Breakout-continuation on a less-arbitraged universe.** The crowding mechanism
  predicts any residual breakout edge lives where arbitrage capital is thinner --
  mid-cap alts rather than BTC/ETH/BNB/SOL, and/or higher timeframes (4H/1D, less
  HFT competition). Requires a concrete "why alts/HTF differ" mechanism before
  spending a trial. LOW priority given how decisively negative the liquid-major
  result was (PF 0.59 in the target regime, not a near-miss).

---

## How to use this map when sourcing

1. Prefer UNEXPLORED cells in the uncovered regime (currently: funding/flow in
   trending_bull -- H-003).
2. Treat DEAD cells as closed for that exact form; only reopen via a FIXABLE
   seedbed with a sharper mechanism.
3. A new idea that pattern-matches a DEAD cell must state why it differs, or it
   fails the Stage-1 "not a known-dead pattern" hard gate.
