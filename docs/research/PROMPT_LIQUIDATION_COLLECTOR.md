# Session Prompt — Build the Forward Liquidation Collector (proprietary-data play)

**Purpose**: Paste the block below into a fresh Claude Code session. This is a
focused BUILD task — justified infrastructure, not speculative tooling. The
liquidation-cascade hypothesis already PASSED the Stage-1 quality gate twice
(H-004 17/21, H-009 18/21) and died ONLY on a data wall (Coinglass paywall;
Hyperliquid S3 needs AWS). This session builds the one data source that is free
and reachable: a forward collector that accrues our OWN liquidation history over
time. It is the "edge is in the data others don't have" move, at $0.

**Written 2026-06-11.** Repo on `master`, dual-file DECISIONS in sync.

---

## COPY EVERYTHING BELOW THIS LINE INTO THE NEW SESSION

---

I'm continuing PARAVANT, a personal autonomous crypto trading system. The research
layer's forward hypothesis loop has run ~10 trials and produced a strong
meta-finding: every PUBLIC signal computable from price/flow on liquid majors at
1H is already arbitraged (0 promotions, all DSR-rejected). The two highest-mechanism
ideas were both LIQUIDATION strategies (H-004, H-009) — they passed the Stage-1
quality gate but died on DATA WALLS (Coinglass is paywalled; Hyperliquid history
needs AWS S3). The strategic conclusion: edge lives in data others don't have, and
the one reachable path is to COLLECT OUR OWN liquidation history forward.

**Your job this session: build a forward liquidation collector.** This IS a build
task and it is justified (a gate-passing hypothesis is blocked only by data —
DEC-2026-06-04-018 data-channel-on-pass discipline). Build the MINIMAL durable
collector, not a broad "liquidation platform."

## Required reading (in this order)

1. `docs/research/NEGATIVE_SPACE_MAP.md` — the meta-finding + the liquidation
   data-wall entries (H-004, H-009).
2. `research/data/funding_rates.py` — the CAUSAL data-channel pattern to mirror
   (fetch + cache + as-of accessor, leakage-guarded by construction).
3. `research/hypotheses/ledger.yaml` — the H-004 / H-009 pre-registrations (the
   mechanism + the cascade-threshold thinking already done).
4. `.claude/CLAUDE.md` + `.claude/rules/decision-consistency.md` — project rules +
   dual-file DECISIONS sync. `.claude/DECISIONS.md` footer for the next DEC ID.
5. `docs/research/RESEARCH_LAYER_PRD.md` Section 5 (one-way dependency) + Section
   8.2 (cost realism context).

## What to build (minimal, durable, causal)

- **Source: Binance USDT-M futures liquidation WebSocket** — the free, public,
  no-auth `!forceOrder@arr` aggregated stream (and/or per-symbol `<sym>@forceOrder`).
  Binance perps are the largest liquidation venue, so this is the best free signal.
  (Bybit/Hyperliquid can be added later; start with Binance.)
- **Persist every liquidation event** durably: timestamp (UTC, ms), symbol, side
  (the side being liquidated), price, quantity, notional. Append-only.
- **Store**: a dedicated, namespaced store — parquet files under
  `research/data/liquidations/` OR a `research_liquidations` table. Do NOT write to
  the live `trade_log` / production tables. Read-only discipline on existing Neon
  data is unchanged.
- **Causal by construction**: because you only ever record past events as they
  arrive, lookahead is structurally impossible — but still expose an as-of accessor
  `liquidations_in_window(t0, t1)` that returns only events with `ts <= now`,
  mirroring `funding_rates.rate_at`.
- **Reliability**: auto-reconnect with backoff on WS disconnect; de-duplicate
  events; flush to durable store frequently (a crash must lose minimal data).
- **A thin runner**: `scripts/run_liquidation_collector.py` (or similar) that runs
  continuously. It is a DATA process only — it must NEVER place orders, and it does
  not touch `LIVE_TRADING_ENABLED` (stays OFF).
- **Tests**: WS message parsing, dedup, the causal accessor (never returns a
  future event), reconnect logic (mockable). Target >=80% coverage on new code.

## Critical operational note (surface to the operator, do not silently decide)

A forward collector must run on an ALWAYS-ON, NON-geo-blocked host. Two facts:
- The collector connects to Binance market-data WebSocket. If run from a
  geo-restricted region it may be rejected (same root cause as DEC-2026-06-04-003 /
  the paper-trading geo-block). 
- Railway's region is currently the geo-block problem. So the collector likely
  CANNOT just run on the current Railway service as-is.

Surface the host options to the operator: (a) run locally on an always-on machine;
(b) a cheap non-blocked VPS; (c) Railway once the region is fixed. Do NOT enable
live trading to make it run. The collector starts the data clock; where it runs is
an operator decision.

## What this does and does NOT unlock (set expectations)

- It accrues data FORWARD, so the liquidation hypothesis CANNOT be screened today.
  Liquidation cascades large enough to trade are RARE — reaching testable N (>=30
  in HIGH_VOL) will take WEEKS to MONTHS of accrual. The collector's job is to start
  the clock, not to produce a verdict now.
- When enough history accrues, the liquidation generator gets implemented and run
  through `regime_dsr` like any other hypothesis (Stage-1 already passed; it
  re-enters at the data/implement step). The LONG flush (buy forced-selling) is the
  spot-deployable path; the SHORT squeeze-fade is research-only per the spot lock
  (DEC-2026-05-28-001).

## Rules you MUST follow

- One-way dependency: `src/` never imports `research/`. The collector lives in
  `research/` + `scripts/`; `src/` is untouched.
- Dual-file DECISIONS sync (`.claude/` AND `.agent/`, verify `diff` empty). File a
  DEC for the new liquidation data channel + collector process (next ID from
  footer).
- Zero-tech-debt: full type hints, Google docstrings, timezone-aware UTC datetimes,
  structured logging via `src/utils/logging.get_logger()`, no emojis/unicode in
  code.
- Do NOT enable live trading. Do NOT modify Neon trade data. Do NOT touch the
  Railway region. Do NOT over-build — minimal collector only.

## How to start

1. Read the required docs + confirm the Binance `forceOrder` stream shape.
2. State the minimal design (source, schema, store, accessor, runner) and surface
   the host/always-on decision to the operator BEFORE building.
3. Use TodoWrite. Build channel + accessor + runner + tests; file the DEC; commit
   (research-scoped). Then report: data is accruing; the liquidation screen opens
   when N is sufficient (weeks-months).

## END COPY

---

**Note for Eva**: This is the one move that builds a proprietary, compounding data
asset at $0 — the genuinely professional edge-source available to retail. It will
NOT produce a tradeable verdict for weeks (cascades are rare; N accrues slowly), so
treat it as planting a tree. The one thing you must decide: WHERE it runs
continuously (local always-on machine, cheap VPS, or Railway post-region-fix), since
the current Railway region is geo-blocked from Binance.
