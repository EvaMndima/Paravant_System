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
| Derivatives-flow / funding-EXTREME contrarian fade (H-005 thin-N -> H-006 at real N, short) | **DEAD** (0.38) | **DEAD** (0.30) | **DEAD** (0.35) | **DEAD** (0.96<1) | **DEAD** (0.11); target high_vol **DEAD** (PF 0.945, N=28, p=0.96) |
| Institutional spot-flow / ETF net-inflow demand (H-007, long BTC/ETH) | **DEAD** (0.44, N=87) | **DEAD** (0.56) | **DEAD** (0.38) | **DEAD** (0.13) | **DEAD** (0.32); high_vol 0.94 thin N=17 |
| Cross-sectional relative-strength momentum (H-008, long top-k) | **DEAD** (0.88, N=121) | **DEAD** (0.43) | **DEAD** (0.40) | **DEAD** (0.30) | **DEAD** (0.52); high_vol **DEAD** (0.26) |
| Cross-venue friction / Coinbase premium (H-010, long BTC) | **DEAD** (0.35, N=75) | **DEAD** (0.37) | **DEAD** (0.53) | **DEAD** (0.31) | **DEAD** (0.45); high_vol PF 1.06 N=23 p=0.92 = NOISE |
| Cross-asset BTC->alt lead-lag (H-011, long lagging mid-cap) | **DEAD** (0.44, N=255) | **DEAD** (0.28) | **DEAD** (0.27) | **DEAD** (0.29) | **DEAD** (0.12); INVERTED (negative selection) |

**Headline:** TRENDING_BULL remains UNCOVERED and is now a HARD gap. SEVEN distinct
mechanism vehicles have been tried there and none clears the DSR floor:
pullback-in-trend (WEAK; BTP/MACD_PB), price breakout-continuation (DEAD; H-002,
N=341), funding-as-trend-confirmation (DEAD; H-003, N=132), institutional
spot-ETF-flow demand (DEAD; H-007, PF 0.44 N=87), cross-sectional
relative-strength momentum (DEAD; H-008, PF 0.88 N=121), cross-venue Coinbase
premium (DEAD; H-010, PF 0.35 N=75), and cross-asset BTC->alt lead-lag (DEAD;
H-011, PF 0.44 N=255). Price momentum, derivatives flow, institutional spot flow,
cross-sectional structure, cross-venue friction, AND cross-asset diffusion are all
exhausted here. A validated trending_bull strategy, if one exists, will need a
mechanism class NOT yet tried (breadth/participation, basis/term-structure) OR a
NON-PUBLIC signal not yet accessible (the liquidation lens) with a concrete
counterparty. Do NOT re-source continuation, funding, ETF-flow, single-factor
momentum, cross-venue premium, or lead-lag here.

**Headline 3 (non-public/less-arbitraged angle did NOT escape the death, 2026-06-10).**
Sourced specifically against the crowding meta-finding, the three survivors fared
no better: H-010 (cross-venue friction) and H-011 (cross-asset diffusion) both DEAD
FUNDAMENTAL at large N (H-011 INVERTED -- the lagging alt keeps lagging, negative
selection confirming H-008 from the other side); H-009 (the genuinely non-public
on-chain liquidation lens, the strongest candidate) could NOT be screened -- BLOCKED
on data ACCESSIBILITY (HL has no market-wide liquidation REST; deep history needs an
AWS S3 requester-pays archive unavailable here). KEY PATTERN: every signal that is
PUBLIC and computable from price/flow on liquid venues is arbitraged; the one
genuinely non-public signal hit a data wall, not a reasoning wall. The edge, if it
exists, lives exactly where the data is hardest to get (H-004 + H-009, both
liquidation, both data-blocked).

**Headline 2 (funding family CLOSED, 0-for-3).** Perp funding has now been tested
as a signal in BOTH directions at large N and carries NO exploitable timing edge:
as a trend CONFIRMER (H-003, long, DEAD at N=132) and as an EXTREME CONTRARIAN
fade (H-006, short, DEAD at N=132 across every regime incl. the target high_vol
PF 0.945). H-005 was the thin-N false start (N=4); H-006's percentile+window fix
delivered the real verdict. Do NOT source another funding-as-signal hypothesis on
liquid majors at 1H -- the gate adds nothing over the price vehicle in either
direction. The over-leveraged-perp COUNTERPARTY is not dead as a target; only the
FUNDING LENS on it is. The DIRECT liquidation lens (H-004, data-blocked) is a
different signal and remains open for >=$25k capital.

---

## Rejection log

### Stage 1 -- reasoning gate (cost: minutes, no DSR trial)

| Idea | Date | Reason | Tag |
|---|---|---|---|
| Buy-the-dip trend pullback (trending_bull) | 2026-06-08 | Duplicate of active BTP (`bull_trend_pullback`) and retired MACD_PB pullback family; no stated differentiator. Failed the "not a known-dead/duplicate pattern" hard gate. | DUPLICATE |
| Mid-cap alt breakout-continuation (thin-arb universe) | 2026-06-10 | Passes hard gates (the "thinner arb on alts" differentiator is stated) but scores 12/21, BELOW the 14 threshold: low diversity (1/3) + crypto-fit (1/3) -- a rehash of momentum/breakout that is DOUBLY dead on majors (H-002 + H-008), and mid-cap spreads make it likely cost-dead (VPT lesson). Not worth a trial over H-011 (the sharper thin-universe play). | BELOW_THRESHOLD |
| Stablecoin-supply macro-liquidity (long majors on supply expansion) | 2026-06-10 | Fails the MECHANISM hard gate: a macro-liquidity TIDE, not a counterparty who keeps losing (stablecoin minting funds DeFi/alts/yield, not specifically BTC). Also known-dead-adjacent to H-007 (structural-inflow-leads-price, same reverse-causality shape). | NO_COUNTERPARTY |

### Stage 3 -- DSR evidence gate (cost: one trial / K)

| Hypothesis | Date | Result | Tag |
|---|---|---|---|
| H-2026-06-002 breakout-continuation (`donchian_atr`, liquid-major 1H spot) | 2026-06-08 | TIER_D in every regime; target trending_bull PF-adj 0.59 / Sharpe -0.235 at N=341 (large sample), DSR p=1.0. Crowding + cost fail modes fired as pre-registered (inverse-crowding scored 1/3 at Stage 1). | **FUNDAMENTAL** |
| H-2026-06-003 funding-confirmed trend (`funding_confirmed_trend`, liquid-major 1H spot) | 2026-06-09 | TIER_D in every gating regime; target trending_bull PF-adj 0.53 / Sharpe -0.292 at N=132, DSR p=1.0. Funding gate added no edge over the trend vehicle (pre-registered fail mode fired); lone PF>1 cell (ranging, p=0.92) is thin wrong-regime noise (CMF pattern). | **FUNDAMENTAL** |
| H-2026-06-005 funding-extreme contrarian SHORT (`funding_extreme_contrarian`, liquid-major 1H futures) | 2026-06-09 | INSUFFICIENT_DATA in every bucket; pooled N=4 (high_vol N=1). The thin-N fail mode fired hard: the same-bar conjunction of funding>0.05%/8h AND fast-EMA cross-down AND close>EMA(100) is near-empty. Mechanism UNADJUDICATED (not an edge rejection). Distinct from H-002/H-003 (those died FUNDAMENTAL at large N). Corrected by H-006. | **FIXABLE** (thin-N feasibility miss) |
| H-2026-06-006 funding-extreme contrarian v2 (`funding_extreme_contrarian_v2`, percentile gate + windowed break, liquid-major 1H futures) | 2026-06-09 | The H-005 fix WORKED on feasibility (pooled N 4 -> 132; high_vol N=28), but at real N the funding gate added NO edge: PF-adj < 1 in EVERY bucket (high_vol 0.945, trending_bear 0.956, chop 0.66, bear 0.57, trending_bull 0.38, ranging 0.11), all DSR p 0.84-1.0. EDGE rejection, not feasibility. Closes the funding family (0-for-3 with H-003). | **FUNDAMENTAL** |
| H-2026-06-007 spot-ETF net-flow demand (`etf_flow_demand`, long BTC/ETH after large inflows, 1H-gated-on-daily-flow) | 2026-06-10 | Feasibility GOOD (N=232 pooled), but PF-adj < 1 in EVERY bucket (trending_bull 0.44 N=87, bull 0.48, chop 0.68, bear 0.21), all DSR p 0.91-1.0. Reverse-causality fail mode FIRED: inflows LAG price, so "long after inflow" buys the move that already happened. (Honest confounder: ATR(14h) trailing stop is tight for a daily-drift thesis -> a daily-scaled-exit variant is a distinct low-priority seedbed; 0.44 is too decisive to blame the exit.) | **FUNDAMENTAL** |
| H-2026-06-008 cross-sectional momentum (`cross_sectional_momentum`, long top-k of 4-symbol universe, 1H daily-rebalance) | 2026-06-10 | Feasibility GOOD (N=457 pooled), but PF-adj < 1 in EVERY bucket (trending_bull 0.88 N=121 least-bad, bull 0.67, bear 0.34, chop 0.31), all DSR p ~1.0. Crowding fail mode FIRED (the crowding=1/3 Stage-1 flag; the H-002 death in a new vehicle). Secondary: top-quartile of 4 symbols = top 1 (weak dispersion); a 10-30 alt universe is a distinct low-priority seedbed. | **FUNDAMENTAL** |
| H-2026-06-010 Coinbase premium (`coinbase_premium`, long BTC on elevated cross-venue premium, 1H) | 2026-06-10 | Feasibility GOOD (N=261), but PF-adj < 1 in every gating bucket (trending_bull 0.35 N=75, bull 0.36, bear 0.37), all DSR p ~1.0. Reverse-causality fail mode FIRED (the H-007 killer): premium widens AFTER price. The lone PF>1 cell (high_vol 1.06, N=23, p=0.92) is the ONLY positive-Sharpe cell in the program but is thin descriptive NOISE (~92% luck), not a discovery (H-003 pattern). | **FUNDAMENTAL** |
| H-2026-06-011 BTC->alt lead-lag (`btc_lead_lag`, long lagging mid-cap after a BTC thrust, 1H) | 2026-06-10 | WORST of the program: PF-adj 0.27-0.44 in EVERY bucket at N=918 (6 alts; trending_bull 0.44 N=255), all DSR p ~1.0. INVERTED -- buying the alt lagging BTC = buying relative losers that keep lagging (negative selection; H-008 confirmed from the other side). "Lead-lag = beta not alpha" fail mode fired, and worse. Thin-arb universe did NOT rescue it. | **FUNDAMENTAL** |

### Pre-registered but DATA-BLOCKED (cost: minutes; no DSR trial, not a rejection)

| Hypothesis | Date | Reason | Tag |
|---|---|---|---|
| H-2026-06-004 liquidation-cascade reversion (buy the long-liquidation flush, HIGH_VOL) | 2026-06-09 | Stage-1 quality gate PASSED (17/21); build BLOCKED at the data channel. No FREE causal historical liquidation source exists (Binance `allForceOrders` deprecated; `forceOrders` 90-day/user-private; websocket real-time-throttled). Coinglass liquidation-history is adequate but PAID ($29/mo, no free tier) -> deferred per DEC-2026-06-04-005 (paid alt-data gated to >=$25k capital). Operator deferred 2026-06-09. Pre-registration frozen in `ledger.yaml`; unblocks at >=$25k capital or an explicit key approval. NOT a price-proxy candidate (removing the exogenous liquidation signal = the already-DEAD H-002 price action). | DEFERRED (paywall) |
| H-2026-06-009 Hyperliquid liquidation-cascade reversion (long the flush, HIGH_VOL) | 2026-06-10 | Stage-1 PASS (18/21, the strongest of its batch); build BLOCKED on data ACCESSIBILITY (verified before building). HL `/info` has NO market-wide liquidation type (probes -> 422); `candleSnapshot` caps at 5000 bars (~208d); deep history is the Hydromancer S3 requester-pays archive, needing AWS creds this env lacks. FREE-of-fee but inaccessible here. Unblocks via AWS creds for the S3 archive, OR forward-collect via WS, OR >=$25k for a paid source. NOT a price-proxy candidate. | DEFERRED (accessibility) |

### Non-public / less-arbitraged batch RESOLVED (2026-06-10)

Sourced against the crowding meta-finding; built + screened where data allowed.
- **H-2026-06-010** Coinbase premium (cross-venue friction) -> **DEAD FUNDAMENTAL** (reverse causality; see Stage-3 table).
- **H-2026-06-011** BTC->alt lead-lag (thin-arb diffusion) -> **DEAD FUNDAMENTAL / INVERTED** (see Stage-3 table).
- **H-2026-06-009** HL liquidation reversion (the strongest, most non-public) -> **DATA-BLOCKED** (accessibility; see DATA-BLOCKED table).

Reusable infra built this batch (for future hypotheses): `research/data/coinbase_prices.py`
(Coinbase cross-venue price channel), `research/data/btc_reference.py` (BTC thrust
reference), `research/data/etf_flows.py`, `research/data/xs_rank.py`.

Recommended screen order: H-009 (strongest mechanism + most non-public) -> H-011
-> H-010. Two sourced ideas died at Stage 1 (see the rejection log above).

### New mechanism classes SCREENED 2026-06-10 (both built + run)

H-007 (institutional spot-flow) and H-008 (cross-sectional) were built (ETF-flow
Farside channel; cross-symbol rank panel) and screened -- BOTH FUNDAMENTAL at large
N (see the Stage-3 table above). Both pre-registered fail modes fired: ETF inflows
LAG price (reverse causality), cross-sectional momentum is crowded. Each carries a
distinct low-priority FIXABLE seedbed (ETF: daily-scaled exit; XS: wider alt
universe), neither auto-pursued. The infra they justified (etf_flows.py, xs_rank.py)
is reusable for any future ETF-flow or cross-sectional hypothesis.

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

- **Funding at EXTREMES as a CONTRARIAN signal -- CLOSED (no longer a seedbed).**
  H-005 (thin-N, N=4) was corrected by H-006 (per-symbol funding percentile +
  windowed downside-break), which fixed feasibility (pooled N=132) and then died
  FUNDAMENTAL at real N: PF < 1 in every bucket, the funding gate added no edge.
  Together with H-003 (funding confirmer, DEAD) the funding-signal family is
  0-for-3 and CLOSED. Do NOT spend a 4th funding trial on liquid majors at 1H.
  (The over-leveraged-perp counterparty is reachable only via the DIRECT
  liquidation lens below, a different signal -- not funding.)

- **Liquidation-cascade reversion (LONG flush) -- DATA-BLOCKED, deferred (H-2026-06-004).**
  Stage-1 PASS (17/21) but no FREE causal historical liquidation data exists; the
  paid source (Coinglass) is gated by DEC-2026-06-04-005 (>=$25k capital). The
  funding-extreme contrarian above is the FREE-data lens on the SAME counterparty
  (over-leveraged perps) -- pursue that until capital unlocks the liquidation lens.

---

## Calibration observations (expected vs actual)

| Hypothesis | Stage-1 score | expected PF | actual PF (trending_bull) | delta |
|---|---|---|---|---|
| H-2026-06-002 breakout | 14/21 | 1.30 | 0.59 | -0.71 |
| H-2026-06-003 funding | 18/21 | 1.40 | 0.53 | -0.87 |
| H-2026-06-005 funding-contrarian | 18/21 | 1.30 | n/a (N=4, INSUFFICIENT_DATA) | feasibility miss, not edge |
| H-2026-06-006 funding-contrarian v2 | 18/21 | 1.30 | 0.945 (high_vol, N=28) | -0.355 (edge rejection at real N) |
| H-2026-06-007 ETF-flow | 16/21 | 1.30 | 0.44 (N=87) | -0.86 |
| H-2026-06-008 cross-sectional momentum | 15/21 | 1.25 | 0.88 (N=121) | -0.37 |
| H-2026-06-010 Coinbase premium | 16/21 | 1.25 | 0.35 (N=75) | -0.90 |
| H-2026-06-011 BTC->alt lead-lag | 16/21 | 1.25 | 0.44 (N=255) | -0.81 |

All over-optimistic on edge. The pattern across EIGHT screened trials is now
unambiguous: **every hypothesis that PASSED Stage 1 (scores 14-18) was REJECTED at
DSR** -- funding scored 18/21 THREE TIMES (H-003/H-005/H-006), and higher Stage-1
scores have NOT done better (H-008 scored lowest at 15 and was the LEAST-bad at
0.88; the 16-18 scorers landed 0.35-0.53). The scorecard measures REASONING quality
(mechanism, crowding, parsimony), NOT backtest edge -- a strong mechanism story is
a YELLOW flag, not green, until DSR rules (DEC-2026-06-04-018 anti-rationalization).
Do not treat the scorecard total as a predictor of edge; the DSR p<0.3 floor is the
only arbiter. The recurring KILLER across all eight is CROWDING/efficiency: every
PUBLIC signal computable from price/flow on liquid venues (breakouts, funding, ETF
flows, cross-sectional momentum, cross-venue premium, lead-lag) is arbitraged.
Sourcing explicitly for non-public/less-arbitraged angles (H-010/H-011) did NOT
escape it; the one genuinely non-public signal (H-009 on-chain liquidations) hit a
DATA-ACCESSIBILITY wall, not a reasoning wall. NET: the open edge, if any, lives
where the data is hardest to get (the liquidation lens, H-004 + H-009 -- both
data-blocked) or in a mechanism class not yet tried (breadth/participation,
basis/term-structure). (Keep accumulating these rows; the calibration framework,
PRD 13.2, reads this signal over time.)

**Feasibility-gate calibration (NEW, from H-005).** H-005 also scored 18 but never
reached a PF row -- it died at N=4 (INSUFFICIENT_DATA). Its Stage-1
`sample_size_feasibility` hard gate was scored "PASS (conditional)" by reasoning
about each trigger condition's MARGINAL frequency. The lesson: estimate N for the
CONJUNCTION (logical AND) of rare triggers, not the marginals -- three individually
plausible conditions ANDed on the same bar can be near-empty. Apply this to the
feasibility hard gate going forward; it is a distinct failure axis from the
edge-calibration rows above (a hypothesis can have a fine mechanism AND be
untestable as specified).

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
