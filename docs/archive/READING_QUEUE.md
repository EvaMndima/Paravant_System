# Reading Queue — Tiered Sourcing for the Forward Hypothesis Loop

**Date:** 2026-06-09
**Related:** DEC-2026-06-04-018 (quality gate), DEC-2026-06-04-020 (validation
methodology), `docs/research/NEGATIVE_SPACE_MAP.md`, PRD Appendix E.

---

## How to use this queue (read once — it changes everything)

**Sourcing does NOT inflate K. Only TESTING (a DSR trial) inflates K.** So read as
widely as you want from this queue; the cost is only your time. A source's job is
to surface a MECHANISM CANDIDATE — it still must clear the Stage-1 reasoning
scorecard (named counterparty, not crowded, feasible N, not a known-dead pattern)
before it ever earns a DSR trial. The queue feeds the GATE, not the backtest.

**Three rules for reading anything here:**
1. **Read for MECHANISM, not for signals.** "RSI<30 buys" is a signal (crowded,
   probably dead). "Forced liquidations create temporary dislocations that
   over-leveraged traders are structurally compelled to sell into" is a mechanism.
   You want the second kind.
2. **Public = crowded = arbitraged.** The more popular/simple/copy-pasteable a
   source's ideas are, the LOWER their surviving edge. Famous patterns are
   negative signals. This is why the tiers below are weighted toward DATA you have
   to turn into a signal yourself, not pre-packaged strategies.
3. **Does the edge survive at OUR holding period (15m-4H/1D)?** Microstructure /
   sub-minute edges are an HFT/co-location game retail cannot win (DEC-006). Funding
   (hours), liquidation cascades (minutes-hours), on-chain flows (hours-days) all
   survive at our horizon. Order-book imbalance does not — skip it.

Current sourcing priority: a DIFFERENT MECHANISM CLASS (trending_bull continuation
is a documented HARD GAP), or a different uncovered regime (RANGING, HIGH_VOL).
Tier 1 is where uncrowded crypto-native mechanisms most likely live.

---

## TIER 1 — Crypto-native DATA (highest signal; prioritize)

These require you to turn raw data into a signal — which is exactly why their edges
are less crowded (most people read the summaries, not the data).

| Source | Mine it for | Notes |
|---|---|---|
| **Coinglass** (liquidation maps + data directory) | Liquidation cascades, OI, funding, long/short ratios | **Top priority for the liquidation hypothesis.** Free tier has aggregated liquidation data. The named-counterparty mechanism (forced sellers) lives here. |
| **CryptoQuant** (+ Quicktakes) | Exchange in/out-flows, miner positioning, stablecoin flows, SOPR | Quicktakes = analyst mechanism sketches. Free blog usable; paid API deferred to >=$25k (DEC-005). |
| **Glassnode Insights** | On-chain accumulation/distribution, NUPL, SOPR, realized cap | Free Insights blog; paid Studio deferred to >=$25k. Mechanism-rich. |
| **Coinglass Quicktakes / data** | Funding extremes, OI divergence | Reuses the funding channel already built. |
| **Dune Analytics** (crypto dashboards) | DEX flow, whale wallets, protocol-specific flow | Free; query-driven, so genuinely uncrowded. Higher effort = higher edge. |
| **Token Terminal** | Protocol revenue/fundamentals (fee flows, P/S) | Fundamentals-as-signal; longer horizon, lower frequency (watch the N feasibility gate). |
| **DeFiLlama** | TVL flows, stablecoin supply, yield migration | Free; structural flow signals. |

## TIER 2 — Institutional / academic research (curated, lower-noise)

| Source | Mine it for | Notes |
|---|---|---|
| **SSRN** (q-fin) | Mechanism grounding, OOS-tested factors | Sort by downloads; crypto-filter. Best for "is there a published reason this works." |
| **The Block Pro Research** | Market-structure reports | Curated; paid. Good context, fewer direct edges. |
| **Delphi Digital** | Deep crypto research | Paid; thesis-level, occasionally mechanism-level. |
| **QuantNet Community** | Quant career/method discussion | Method > strategy ideas. |
| **Bankless** | Narrative/macro context | LOW for edges — narrative, not mechanism. Context only. |

## TIER 3 — Code repos (mine for MECHANICS, never for edges)

Public strategy code is the MOST crowded alpha on earth — anything with surviving
edge would not be public. Use these to learn implementation patterns, indicator
code, and execution mechanics — NOT to copy strategies.

| Source | Mine it for | Notes |
|---|---|---|
| **Freqtrade** (GitHub + strategy repo) | Indicator/execution mechanics, backtest patterns | Treat every published strategy as a known-dead pattern unless proven otherwise. |
| **QuantConnect** (crypto + Alpha Streams) | Engine patterns, data handling | Alpha Streams = others' (crowded) signals; mechanics only. |
| **NautilusTrader** | Execution architecture, event-driven design | Engineering reference, not an idea source. |

## TIER 4 — Forums (low signal, high noise; last resort)

Occasional gems buried in retail TA. Use for METHOD questions, not strategy ideas.

| Source | Notes |
|---|---|
| **Quant / Quantitative Finance StackExchange** | Good for *method* questions (how to compute X correctly); not idea sourcing. |
| **Wilmott Forums** | Old-school quant; mostly equities/rates; rare crypto relevance. |
| **EliteTrader** | Mostly retail; very low signal density. |
| **Quora** | Near-zero. Skip unless a specific expert answer is linked. |

---

## The "elite source" myth (honest note)

There is no secret website the pros read that you don't. The genuinely
under-exploited edge in crypto is in **Tier-1 raw data that requires work to turn
into a signal** — because most participants consume the *narrative* (Tier 2
summaries, crypto Twitter) rather than building signals from the *data* (Dune
queries, Glassnode metrics, Coinglass liquidation data). The "elite" move is not a
better feed; it is reading Tier-1 data and asking *what structural, repeated flow
does this reveal, and who is forced to be on the losing side of it* — which is
exactly the mechanism-first discipline the Stage-1 scorecard enforces. The edge is
in the work, not the source.
