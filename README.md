# PARAVANT

**An autonomous crypto trading system, and a validation layer built to prove
its own strategies don't work.**

It worked, and the most instructive thing it did was catch an error in its own
reporting.

After four months and 29 signal generators, **no strategy in this repository has
a validated edge.** Eight subjects were rejected outright at a sample size where
the verdict carries information. Ten more were initially reported as rejected —
until the system's own guard established that they had never had enough data to
reject at all, and reclassified them as *unmeasurable*.

The difference between "proven worthless" and "never actually measured" is the
whole discipline. Getting it wrong in the safe direction, then catching it, is
the result this repository exists to report. The trading engine is the
supporting cast.

---

## Why this might be interesting

Most trading repositories show you a backtest that made money. This one shows
you the machinery that determines whether a backtest that made money *means*
anything, applied adversarially to its author's own work until it returned `no`.

The core question the research layer answers is:

> Did this result come from signal, or from running enough experiments that
> something had to look good?

That is the multiple-comparisons problem. It is why a strategy with a Sharpe of
2.0 discovered on the 200th configuration is worth less than one discovered on
the 2nd — and it is structurally the same problem that makes benchmark numbers
hard to trust anywhere results are searched for rather than predicted: model
evaluation, A/B testing, hyperparameter search, LLM benchmarks.

The defenses implemented here are the standard ones for that class of problem:

| Failure mode | Defense implemented |
|---|---|
| Many experiments, best one reported | Deflated Sharpe Ratio + effective-trial counting |
| Gates moved to fit the result | Thresholds pre-registered before results are seen |
| Test set used for selection | Strict train/holdout separation, holdout looked at once |
| Small-sample illusion | Minimum-evidence gate, `INSUFFICIENT_DATA` distinct from `REJECT` |
| Confounding | Regime-conditional attribution across 8 market states |
| Optimistic cost assumptions | Versioned cost model, deliberately pessimistic |
| Negative results discarded | Negative-space map treats "no edge here" as a finding |

A written protocol (`docs/research/RESEARCH_PROTOCOL.md`) forbids moving a gate
to make a strategy pass, and a pre-registered date — 2026-12-01 — fixes when the
project evaluates whether to stop, against criteria written in advance.

---

## The result

Eight subjects were rejected at a sample size where a Deflated Sharpe verdict
carries information — one strategy from recorded trades, and seven forward
hypotheses screened against backtest:

| Subject | Mechanism | Regime | N | PF | DSR p |
|---|---|---|---|---|---|
| BTF | Multi-timeframe bear trend | — | 25 | 0.54 | 1.000 |
| H-2026-06-002 | Price breakout continuation | TRENDING_BULL | 341 | 0.59 | 1.000 |
| H-2026-06-011 | BTC lead-lag diffusion into alts | TRENDING_BULL | 255 | 0.44 | 1.000 |
| H-2026-06-003 | Perp funding confirmation | TRENDING_BULL | 132 | 0.53 | 1.000 |
| H-2026-06-008 | Cross-sectional relative strength | TRENDING_BULL | 121 | 0.88 | 1.000 |
| H-2026-06-007 | Spot-ETF net-flow demand | TRENDING_BULL | 87 | 0.44 | 1.000 |
| H-2026-06-010 | Coinbase premium | TRENDING_BULL | 75 | 0.35 | 1.000 |
| H-2026-06-006 | Funding-extreme contrarian | HIGH_VOL | 28 | 0.94 | 0.960 |

N is the count in the regime the hypothesis made a claim about; pooled samples
across all regimes run to 974. **Every profit factor is below 1.0** — these are
not marginal edges lost to multiple-comparisons correction, they lose money
before the correction is applied. The `FUNDAMENTAL` tag means the mechanism
failed, not the implementation.

One hypothesis returned `INSUFFICIENT_DATA` at N=4 rather than a rejection —
the guard in the next section working as intended. One was killed at the quality
gate as a structural duplicate before it consumed a trial. Two more are blocked
not on budget but on **causality**: no free historical liquidation series exists
that respects point-in-time correctness, so rather than backfill from a source
that would leak information unavailable at decision time, a forward collector
was built and those hypotheses wait months for N to accrue.

### The part worth reading

The 2026-06-05 retrospective originally reported **all eleven** strategies as
`TIER_D_REJECT`. That report was wrong, and the project's own tooling is what
established it.

Ten of the eleven had between **0 and 4 recorded trades**. The paper-trading
process had been down behind a regional exchange block, so the trade records the
analysis read were nearly empty. A Deflated Sharpe p-value of 1.000 computed on
zero trades is not a finding — it is a null input producing a degenerate output,
and it was being printed next to the word "reject".

The fix was a floor (`MIN_N_FOR_CLASSIFICATION = 10`) checked *before* any
threshold, returning a distinct `INSUFFICIENT_DATA` verdict. From
[`research/promotion/classifier.py`](research/promotion/classifier.py):

> A genuinely edge-less strategy with enough trades still earns `TIER_D`; only
> data *scarcity* yields `INSUFFICIENT_DATA`. The 2026-06-05 run's N=0..4
> strategies were wrongly shown as `TIER_D_REJECT`; this guard prevents that
> "no data" -> "proven noise" misread.

Re-running the stored 2026-06-05 results through the corrected classifier:

```
                        as published    corrected
TIER_D_REJECT                    11            1
INSUFFICIENT_DATA                 0           10
```

This is the oldest error in applied statistics — treating absence of evidence as
evidence of absence — and it is the exact failure the whole research layer was
built to prevent, committed by that research layer, caught by it, and left in
the repository with the superseded report still in place and marked.

**None of this changes the bottom line: zero validated strategies.** It changes
how much of that is *demonstrated* versus merely *unmeasured*, which is a
distinction worth being precise about.

### What was concluded

**TRENDING_BULL is a hard gap, probed from six independent directions.** The six
hypotheses targeting it are not variants of one idea — they are price momentum,
derivatives positioning, ETF flows, cross-sectional ranking, cross-venue premium,
and inter-asset lead-lag. Four of the six use data other than price. All six were
rejected, every one tagged `FUNDAMENTAL` (the mechanism failed, not the code).
The recorded consequence: the next hypothesis for that regime must come from
outside those six classes.

**Funding-based mechanisms are 0-for-3.** All three scored 18/21 at the quality
gate. All three failed.

**The quality scorecard does not predict outcome.** Across the seven screened
hypotheses its score correlates with realised profit factor at Pearson
**r = +0.146**, and the lower-scoring half performed *better* (mean PF 0.73 vs
0.54). Recorded rather than explained away — with the caveat it deserves: n=7
and every outcome is a failure, so this is evidence that it does not predict
*degree of failure*, not proof that it is useless.

Full write-up: **[docs/RESEARCH_FINDINGS.md](docs/RESEARCH_FINDINGS.md)**

---

## Architecture

Three processes from one image: a read/query API, a paper-trading loop, and a
live loop behind a default-off kill switch. Paper and live share the entire code
path and diverge only at the execution interface, which is what makes paper
results usable as a promotion gate.

```mermaid
flowchart TD
    A[Binance REST] --> B[MarketDataFetcher]
    B --> C[OHLCVSeries, cached]
    C --> D[IndicatorFactory, cached]
    D --> E[SignalGenerator]
    E --> F{RegimeRouter<br/>allowed in this regime?}
    F -->|no| Z[No trade]
    F -->|yes| G{RiskController}
    G --> H[kill switch, checked first<br/>daily / weekly loss<br/>max drawdown<br/>open positions<br/>concentration<br/>position size<br/>portfolio correlation<br/>5 circuit breakers]
    H -->|rejected| Y[Logged + alerted]
    H -->|approved| I[PositionSizer]
    I --> J[OrderManager<br/>state machine]
    J --> K[ExecutionInterface]
    K --> L[BinanceExecution]
    K --> M[PaperExecution]
    L --> N[PositionTracker]
    M --> N
    N --> O[(DataStore)]
    O --> P[ExecutionQuality<br/>slippage, fill rate]
    O --> Q[Telegram alerts]
```

The research layer sits alongside and may import from `src/`, but `src/` may
never import from `research/`. That one-way boundary means research experiments
cannot change live behaviour, and the research tree could be deleted without
breaking the trading system.

```mermaid
flowchart LR
    H[Hypothesis<br/>written economic rationale] --> Q{Quality gate<br/>scored /21}
    Q -->|fail| X[Killed, no trial consumed]
    Q -->|pass| T[Train<br/>design freely]
    T --> O[Holdout<br/>looked at ONCE]
    O --> D{Deflated Sharpe<br/>p < 0.3 floor}
    D -->|fail| R[Tier D, retired<br/>+ post-mortem]
    D -->|pass| S[Simulated paper]
    S --> L[Live paper]
    L --> G{READY_FOR_LIVE<br/>N>=30, PF>=1.35<br/>Sharpe>=1.0, DD<=5%}
    G -->|fail| R
    G -->|pass| M[Micro-live, $50-100]
    M --> V[Live, scaled]
```

Every strategy that reaches `Tier D` gets a generated post-mortem with a tagged
failure pattern, and every strategy carries an append-only biography. Retirement
is a completed process, not a deletion.

Deeper detail: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** ·
**[docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)**

---

## What is in here

| Layer | Files | Lines | Notes |
|---|---|---|---|
| `src/` application | 167 `.py` | 49,144 | API, risk, execution, indicators, strategies |
| `tests/` | 133 `.py` | 36,550 | 1,870 passing, 37 skipped, 0 failing |
| `frontend/src/` | 89 `.ts`/`.tsx` | 17,128 | React 19 dashboard — see caveat below |
| `scripts/` | 24 | 11,853 | Live loop, paper loop, sweeps, reporting |
| `research/` | 27 `.py` | 5,440 | DSR, effective-K, cost model, biographies |

Highlights:

- **Risk layer** — 8 pre-trade checks, 5 circuit breakers with state that
  survives restart, kill switch, dead man's switch, time/event/volatility
  filters. Position sizing at 100% coverage, checks at 99%.
- **Live capital model** — per-strategy capital slicing, a concurrency cap, an
  85% capital reserve, and a minimum-notional guard that calls `sys.exit(1)`
  rather than rounding an order up to the exchange minimum.
- **Promotion gate** — a strategy cannot go live until its pooled paper record
  is classified `READY_FOR_LIVE`. Fails *open* on a database error so a restart
  is not blocked; fails *closed* on a clear non-ready verdict.
- **19 indicators**, each independently tested at 88-100% coverage.
- **29 signal generators**, of which 0 are validated. That ratio is the point.
- **120 dated architectural decisions** with rationale and rejected
  alternatives, referenced by 69 distinct IDs from source comments.

---

## Quickstart

```bash
git clone <this repo> && cd Paravant_System

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
cp .env.example .env            # placeholders are fine for a read-only run

python scripts/init_db.py
uvicorn src.api.main:app --reload
```

Then open <http://localhost:8000/docs> for the interactive API.

Live trading additionally requires `LIVE_TRADING_ENABLED` to be set explicitly.
It ships commented out in `.env.example`, so a fresh clone cannot place an order
by accident (DEC-2026-05-27-001).

Frontend:

```bash
cd frontend && npm install && npm run dev
```

Research tooling:

```bash
python scripts/retrospective_dsr.py --help    # the DSR analysis
python scripts/validation_report.py --help    # daily operator report
```

---

## What this is not

Stated plainly, because a reviewer will find all of it anyway.

- **Not a profitable trading system.** No strategy here passes its own
  validation gates. If it had an edge, this README would be a different
  document and probably would not exist.
- **Not authenticated.** All 63 API endpoints are open, including 21 that mutate
  state. Do not expose it to a network you do not control. See
  [SECURITY.md](SECURITY.md).
- **The dashboard is a prototype.** 17,000 lines of React that make three real
  network calls. Every other page renders static seed data and the simulated
  ticker is labelled as such in code. It is honest in the source and it is not
  finished.
- **Not machine learning.** There is no model here. This is systems engineering
  and quantitative research methodology. The overlap with AI engineering is the
  evaluation discipline, not the algorithms.
- **Not fully clean.** 9 tests fail on `master`, 32 network-dependent
  integration tests error rather than skip without exchange credentials, and
  static analysis reports outstanding errors against a config that claims strict
  typing. All of it is enumerated in
  [docs/PRODUCTION_READINESS_ASSESSMENT.md](docs/PRODUCTION_READINESS_ASSESSMENT.md),
  which was written to be uncomfortable rather than flattering.
- **Not built alone in the conventional sense.** It was built by one person
  working with AI coding assistants throughout. What that was actually like,
  including six specific defects it produced and how long each survived, is in
  [docs/AI_ASSISTED_DEVELOPMENT.md](docs/AI_ASSISTED_DEVELOPMENT.md).

---

## Documentation

**Start here**

- [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) — complete briefing; readable without opening a source file
- [docs/research/RESEARCH_PROTOCOL.md](docs/research/RESEARCH_PROTOCOL.md) — the method, and what it forbids
- [docs/AI_ASSISTED_DEVELOPMENT.md](docs/AI_ASSISTED_DEVELOPMENT.md) — what AI-assisted development actually broke

**The result**

- [docs/research/retrospective/](docs/research/retrospective/) — per-strategy DSR post-mortems
- [docs/research/NEGATIVE_SPACE_MAP.md](docs/research/NEGATIVE_SPACE_MAP.md) — where edge is proven absent
- [docs/research/RESEARCH_FIXLIST.md](docs/research/RESEARCH_FIXLIST.md) — the research layer's own known defects, six still open

**Engineering**

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/API_CONTRACT.md](docs/API_CONTRACT.md) · [docs/INDICATOR_SPECIFICATION.md](docs/INDICATOR_SPECIFICATION.md)
- [.claude/DECISIONS.md](.claude/DECISIONS.md) — 120 decisions with rationale and rejected alternatives
- [docs/operations/](docs/operations/) — kill-switch runbook, scheduled jobs
- [docs/PRODUCTION_READINESS_ASSESSMENT.md](docs/PRODUCTION_READINESS_ASSESSMENT.md) — measured gaps and the plan

---

## Development

```bash
pytest                                        # full suite
pytest -m unit                                # fast path
pytest --cov=src --cov=research --cov-report=term

ruff check src/ research/ scripts/
mypy src/
black src/ tests/
```

---

## License

MIT, with a financial-software risk notice. See [LICENSE](LICENSE).

This software can place real orders and lose real money. It is published as an
engineering artifact, not as investment advice, and it comes with no warranty.
