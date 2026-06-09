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
| Derivatives-flow / funding-as-trend-confirm (H-003) | **DEAD** | WEAK | WEAK | WEAK | noise (p=0.92) |

**Headline:** TRENDING_BULL remains UNCOVERED and is now a HARD gap. Three distinct
mechanism vehicles have been tried there and none clears the DSR floor:
pullback-in-trend (WEAK; BTP/MACD_PB), price breakout-continuation (DEAD; H-002,
N=341), and funding-as-trend-confirmation (DEAD; H-003, N=132). The two
front-runner instincts -- price momentum, then derivatives flow -- are both
exhausted as trend-CONTINUATION signals. A validated trending_bull strategy, if
one exists, will need a mechanism class NOT yet tried here (e.g. a contrarian /
flow-EXTREME signal, or cross-asset/breadth structure) with a concrete
counterparty. Do NOT re-source another trend-continuation variant for this cell.

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
| H-2026-06-003 funding-confirmed trend (`funding_confirmed_trend`, liquid-major 1H spot) | 2026-06-09 | TIER_D in every gating regime; target trending_bull PF-adj 0.53 / Sharpe -0.292 at N=132, DSR p=1.0. Funding gate added no edge over the trend vehicle (pre-registered fail mode fired); lone PF>1 cell (ranging, p=0.92) is thin wrong-regime noise (CMF pattern). | **FUNDAMENTAL** |

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

- **Funding at EXTREMES as a CONTRARIAN signal (not a confirmer).** H-003 showed
  funding does NOT confirm trend continuation. A DIFFERENT mechanism: extreme
  positive funding marks over-leveraged longs prone to cascade-liquidation, so a
  FADE / stand-aside at funding extremes is a contrarian thesis with a concrete
  counterparty (forced liquidations). This is a NEW hypothesis (different
  direction + mechanism + likely a high_vol/reversal regime target), NOT a revisit
  of H-003; it needs its own pre-registration, and any live SHORT execution is
  gated by the market-type lock (DEC-2026-05-28-001, spot-long-only live). The
  funding data channel built for H-003 (`research/data/funding_rates.py`) is reused.

---

## Calibration observations (expected vs actual)

| Hypothesis | Stage-1 score | expected PF | actual PF (trending_bull) | delta |
|---|---|---|---|---|
| H-2026-06-002 breakout | 14/21 | 1.30 | 0.59 | -0.71 |
| H-2026-06-003 funding | 18/21 | 1.40 | 0.53 | -0.87 |

Both over-optimistic; the HIGHER Stage-1 score (H-003) did WORSE in-regime. The
scorecard measures REASONING quality (mechanism, crowding, parsimony), NOT
backtest edge -- a strong mechanism story is a YELLOW flag, not green, until DSR
rules (DEC-2026-06-04-018 anti-rationalization). Early read across N=2: do not
treat the scorecard total as a predictor of edge; the DSR p<0.3 floor is the only
arbiter. (Keep accumulating these rows; the calibration framework, PRD 13.2, reads
this signal over time.)

---

## How to use this map when sourcing

1. Prefer UNEXPLORED cells -- but TRENDING_BULL no longer has an untested
   front-runner mechanism (price-momentum and funding-flow are both DEAD there),
   so sourcing for that cell needs a NEW mechanism class (contrarian/flow-extreme,
   breadth/cross-asset), not another continuation variant.
2. Treat DEAD cells as closed for that exact form; only reopen via a FIXABLE
   seedbed with a sharper mechanism.
3. A new idea that pattern-matches a DEAD cell must state why it differs, or it
   fails the Stage-1 "not a known-dead pattern" hard gate.
