# PARAVANT — Publication Roadmap

**Companion to [AUDIT.md](AUDIT.md).** Every item cites the files it touches.

**Priority key**
- **P0** — blocks publication. Do not push public until these are done.
- **P1** — do before linking the repo in an application.
- **P2** — polish; improves the repo but no reviewer will fault you for its absence.

**"Why it matters" is written from the reviewer's seat.** Items marked *internal quality only*
improve the codebase but will not change a hiring decision — do them for yourself, later.

**Total: P0 ≈ 9 h · P1 ≈ 26 h · P2 ≈ 40 h+**

---

## Bucket A — Before the repo goes public

*Target: ~9 hours. This bucket is about not actively misrepresenting the work.*

### A1. Correct the false technology claims — P0 — 1.5 h

**Files:** [docs/ARCHITECTURE.md:660-700](../ARCHITECTURE.md#L660),
[docs/research/RESEARCH_LAYER_PRD.md:285](../research/RESEARCH_LAYER_PRD.md#L285) and
[:327](../research/RESEARCH_LAYER_PRD.md#L327), [:383](../research/RESEARCH_LAYER_PRD.md#L383),
[:473](../research/RESEARCH_LAYER_PRD.md#L473), [requirements-research.txt:22](../../requirements-research.txt#L22)

**Action:**
1. In the ARCHITECTURE stack table, replace `Backtesting | VectorBT` with
   `Backtesting | Custom vectorized engine (pandas/numpy) — src/core/strategy/backtest/`.
2. Replace `Broker SDK | CCXT, python-binance | Multi-exchange support` with
   `Broker SDK | python-binance | Binance only (DEC-2026-01-15-002)`.
3. Delete `vectorbt>=0.25.0` and `ccxt>=4.1.0` from the version block at line 691.
4. In `RESEARCH_LAYER_PRD.md`, mark `research/optimization/bayesian.py` as **PLANNED — not
   implemented** in all four locations, or cut the references.
5. Move `optuna`, `arch`, `jupyter`, `seaborn`, `plotly` in `requirements-research.txt` under
   an explicit `# --- PLANNED (not yet imported by any module) ---` header.

**Why it matters:** a reviewer who checks one stack claim and finds it false discounts
everything else in the repo, including the parts that are true and good. This is the cheapest
credibility purchase available.

---

### A2. Fix the "21 agents" claim everywhere it appears — P0 — 1 h

**Files:** your CV and application materials (outside this repo); plus
[src/core/strategy/generators/\_\_init\_\_.py:1-33](../../src/core/strategy/generators/__init__.py#L1)
(docstring says 24, there are 29); [README.md:11](../../README.md#L11) (says 6).

**Action:** stop describing this as a multi-agent system unless you build an agent
abstraction. Replace with the accurate and still-strong framing:

> 29 pluggable signal-generation strategies behind a common `SignalGenerator` ABC, dispatched
> at runtime by a regime-aware router with fail-closed activation gating.

Then update the generator `__init__.py` docstring to list all 29 (it currently documents 24 —
the five crypto-native generators added later are missing) and fix the README's "6 templates".

**Why it matters:** [AUDIT.md §7.5](AUDIT.md) — the only "agents" a grep finds are four
hardcoded strings in a React mock at
[docs/design/references/components/pages/NotificationsPage.tsx:49](../design/references/components/pages/NotificationsPage.tsx#L49).
A specific numeric claim invites verification. This one fails it.

---

### A3. Clear the root directory — P0 — 1.5 h

**Files:** 35 tracked `SESSION_*.md` / `PHASE_*.md` (1.05 MB); 17 tracked loose `.py`
(3,895 LOC): `test_backtest*.py`, `test_debug.py`, `test_network.py`, `test_system.py`,
`run_final.py`, `run_donchian_test.py`, `run_round2_refinements.py`, `run_regime_search.py`,
`run_strategy_comparison.py`, `run_all_db_strategies.py`, `run_backtest_shared.py`,
`create_strategy_variations.py`, `create_strategy_variations_correct.py`,
`create_regime_optimized_strategies.py`, `backtest_optimization_guide.py`

**Action:**
```
git rm -r --cached SESSION_*.md PHASE_*.md      # or: git mv to docs/archive/build-log/
git rm            test_*.py run_*.py create_*.py backtest_optimization_guide.py
```
Then add to `.gitignore`. If any loose script is still genuinely used, move it into `scripts/`
with a docstring; do not leave it at root. Also delete or `.gitignore` the empty tracked
`docs/validation/` directory.

**Why it matters:** [AUDIT.md §10](AUDIT.md) items 1 and 2. This is the first thing a reviewer
sees and the strongest available signal that the work was prompt-driven and never tidied.
`create_strategy_variations.py` sitting next to `create_strategy_variations_correct.py` is a
one-line indictment. Highest impact-per-hour item in the entire roadmap.

---

### A4. Add LICENSE and a risk disclaimer — P0 — 0.5 h

**Files:** new `LICENSE` (root); [README.md:139-150](../../README.md#L139)

**Action:** add an actual MIT `LICENSE` file — [README.md:150](../../README.md#L150) claims MIT
but no file exists, so GitHub will display "no license" and the code is technically
all-rights-reserved. Add a disclaimer block near the top of the README:

> **Disclaimer.** This software places real orders against a live cryptocurrency exchange and
> can lose money. It is published as an engineering work sample, is provided without warranty
> of any kind, and is not financial advice. Use at your own risk.

**Why it matters:** legal exposure is real for public trading software, and a missing license
means nobody can legally reuse it. Reviewers also read a disclaimer as domain maturity — it
says you understand what the software does.

---

### A5. Make `pytest` green on a clean clone — P0 — 3 h

**Files:** [pyproject.toml:70-77](../../pyproject.toml#L70) (`addopts`);
[tests/conftest.py](../../tests/conftest.py); [src/core/config/settings.py:52](../../src/core/config/settings.py#L52);
[tests/unit/core/config/test_config.py](../../tests/unit/core/config/test_config.py);
[tests/unit/test_generators_comprehensive.py](../../tests/unit/test_generators_comprehensive.py)

**Action, in order:**
1. **Stop the network calls.** Add `-m "not binance and not integration"` to `addopts` in
   `pyproject.toml`, and register an `integration` marker. This removes all 32 errors — they
   are `SSLCertVerificationError` against `testnet.binance.vision` from
   `tests/integration/test_binance_client.py` and `test_symbol_refresh.py`. Document
   `pytest -m integration` separately in the README.
2. **Isolate settings from the developer `.env`.** In `tests/conftest.py`, add an
   `autouse=True` fixture that points `Settings.model_config["env_file"]` at a temp path or
   monkeypatches the relevant env vars. Fixes the 3 `test_config.py` failures caused by
   [settings.py:52](../../src/core/config/settings.py#L52) reading your real `.env`.
3. **Fix the stale count assertions.** `assert 14 == 7` in
   `TestTemplates::test_template_manager_loads_all_templates` and
   `TestConfigLoader::test_config_loader_loads_all_sources` — assert against
   `len(list(Path("config/templates").glob("*.yaml")))` rather than a literal, so it cannot
   rot again.
4. **Investigate the two real regressions.**
   `TestDonchianAtr::test_missing_parameter_raises` and
   `TestRsiBbMeanReversion::test_missing_parameter_raises` both report
   `DID NOT RAISE SignalGenerationError` — those generators stopped validating required
   parameters. Fix the code, not the test. Also reconcile
   `RsiBbMeanReversion.min_bars_required` (test expects 50, code returns 210).
5. `tests/research/test_liquidations.py::test_collector_flush_writes_and_clears` — diagnose
   and fix or mark `xfail` with a reason.

**Why it matters:** [AUDIT.md §10](AUDIT.md) item 3. Any reviewer who takes the repo seriously
runs the tests. `9 failed, 32 errors` converts a 1,884-test suite from your strongest asset
into evidence that the tests were generated and never re-read. Item 4 is a live behavioural
regression, so this is not cosmetic.

---

### A6. Fix the undeclared `requests` dependency — P0 — 0.25 h

**Files:** [requirements.txt](../../requirements.txt) or
[requirements-research.txt](../../requirements-research.txt)

**Action:** add `requests>=2.31`. It is imported by
[research/data/coinbase_prices.py](../../research/data/coinbase_prices.py),
[research/data/etf_flows.py](../../research/data/etf_flows.py),
[research/data/funding_rates.py](../../research/data/funding_rates.py), and
[scripts/regime_dsr.py](../../scripts/regime_dsr.py), and installs today only as a transitive
dependency of `python-binance`.

**Why it matters:** a reviewer following your install instructions and hitting `ModuleNotFoundError`
on a dependency you did not declare is a specific, memorable failure.

---

### A7. Label the frontend as a prototype, or remove the fabricated data — P0 — 0.5 h

**Files:** [frontend/src/components/dashboard/EmergencyPanel.tsx:21-26](../../frontend/src/components/dashboard/EmergencyPanel.tsx#L21);
[frontend/src/hooks/useRealtimeSimulation.ts](../../frontend/src/hooks/useRealtimeSimulation.ts);
plus 10 other files using `Math.random()`; new `frontend/README.md`

**Action:** the fastest honest fix is a `frontend/README.md` stating plainly that the UI is a
design prototype with simulated data, and that only three hooks
(`useBacktestResults`, `usePaperSessions`, `useRegimeState`) are wired to the live API. Better:
change the hardcoded `NVDA / TSLA / AMD / SPY` positions in `EmergencyPanel.tsx` to crypto
symbols, since equities contradict locked decision `DEC-2026-01-15-001`.

**Why it matters:** [AUDIT.md §10](AUDIT.md) item 7. Fabricated positions with a $22,522.50
P&L, in asset classes the project explicitly excludes, read either as sloppiness or as padding.
Both are bad, and a one-paragraph README removes the ambiguity entirely.

---

### A8. Decide on the 25 MB of design assets — P0 — 0.25 h

**Files:** [docs/design/pdf/](../design/pdf/) (15.5 MB `themes.pdf` alone),
[docs/design/screenshots/](../design/screenshots/) (32 PNGs)

**Action:** `git rm --cached` the PDFs at minimum. Keep 2–3 representative screenshots if you
want to show the UI; move the rest out of the repo.

**Why it matters:** a slow clone is friction, and "this trading system is mostly design PDFs"
is a strange thing for a reviewer's `du -sh` to say. Low effort, non-trivial payoff.

---

## Bucket B — Before you link it in an application

*Target: ~26 hours. This bucket is about a reviewer being able to see the good work.*

### B1. Rewrite the README as the actual front door — P1 — 4 h

**Files:** [README.md](../../README.md) (last commit: 2026-02-08, "Initial commit")

**Action:** full rewrite. Structure:
1. **One paragraph** — what it is, that it trades real capital on Binance spot, that it is
   deployed and running.
2. **A diagram** (see B2) immediately after.
3. **The numbers** — 66,557 LOC, 1,884 tests, 71% coverage, 29 generators, 102 commits. Put
   them where they cannot be missed.
4. **Quickstart that starts the real system**: `python -m scripts.run_all`, with
   `LIVE_TRADING_ENABLED` defaulting off. Keep the `uvicorn` command but label it "dashboard
   API (optional)".
5. **A "what makes this interesting" section** pointing at the three things a reviewer should
   read: the fail-closed live-trading supervisor ([scripts/run_all.py](../../scripts/run_all.py)),
   the Deflated Sharpe capital gate ([research/validation/deflated_sharpe.py](../../research/validation/deflated_sharpe.py)),
   and the decision log (`.claude/DECISIONS.md`).
6. **Known limitations** — say plainly that `src/core/orchestrator.py` is legacy, that the UI
   is a prototype, and that live execution is spot-only by design.
7. Fix the stale counts (6 → 29) and remove "walk-forward" from the NOT-included list at
   [README.md:132](../../README.md#L132) — you implemented it in
   [scripts/sweep_tp_wfo.py](../../scripts/sweep_tp_wfo.py).

**Why it matters:** this is 80% of a 5-to-15-minute review. Right now it describes a February
MVP and never mentions the regime router, the promotion pipeline, or the research layer — the
work that actually distinguishes you.

---

### B2. Draw the architecture diagram and the lifecycle trace — P1 — 4 h

**Files:** new `docs/ARCHITECTURE_CURRENT.md` (leave the old one, marked historical); embed in
README

**Action:** two Mermaid diagrams, in the repo, rendered by GitHub:
1. **Component diagram** — `run_all` supervisor → (`run_paper_trading`, `run_live_trading`)
   processes; each → `MarketDataFetcher` → `SignalGeneratorFactory` → generators →
   `SubRegimeDetector` / `RegimeRouter` → `BinanceExecutionAdapter` → `DataStore`; the FastAPI
   app as a separate read-side over the same DB.
2. **Lifecycle sequence** — the pipeline you describe in your own summary: signal generation →
   confirmation → backtest/sweep → paper trading → promotion gate (`READY_FOR_LIVE`: N≥30,
   PF≥1.35, Sharpe≥1.0, MaxDD≤5%) → live tier activation → monitoring/Telegram → demotion.

Annotate each node with its file path.

**Why it matters:** [AUDIT.md §6.2](AUDIT.md). The pipeline exists but is currently
reconstructible only by reading a 2,111-line script. A reviewer will not do that. One diagram
converts "I cannot tell what this does" into "this person designs systems." There is currently
**no diagram anywhere in the repo.**

---

### B3. Resolve the two-orchestration problem — P1 — 4 h

**Files:** [src/core/orchestrator.py](../../src/core/orchestrator.py) (1,800 lines, 575 stmts,
71% covered, never instantiated); [tests/unit/test_orchestrator.py](../../tests/unit/test_orchestrator.py);
[src/api/routes/system.py:116,157,223](../../src/api/routes/system.py#L116);
[src/core/monitoring/](../../src/core/monitoring/)

**Action — pick one, do not leave it ambiguous:**
- **Option 1 (recommended, ~2 h):** delete `orchestrator.py`, its test file, the dead
  `set_orchestrator` / `_orchestrator` branch in `system.py`, and `src/core/monitoring/`
  (imported only by the orchestrator). Note the removal in `DECISIONS.md` per your own Rule 12.1.
  Your coverage will drop slightly and your credibility will rise a lot.
- **Option 2 (~4 h):** wire it in — fix the mypy errors at
  [orchestrator.py:464-469](../../src/core/orchestrator.py#L464) (four nonexistent kwargs, four
  nonexistent attributes) and actually pass it to `init_system_routes` at
  [src/api/main.py:308](../../src/api/main.py#L308).
- **Option 3 (0.5 h, weakest):** rename to `orchestrator_legacy.py` with a header docstring
  explaining it is superseded by `scripts/run_live_trading.py`.

**Why it matters:** [AUDIT.md §10](AUDIT.md) item 4. A 1,800-line module named *orchestrator*
that is thoroughly tested and never called is the clearest available evidence of
generate-test-never-integrate. Deleting it is a stronger signal than keeping it.

---

### B4. Delete the unimportable `regime.py` — P1 — 0.5 h

**Files:** [src/core/strategy/regime.py](../../src/core/strategy/regime.py) (0% coverage,
62/62 statements missed)

**Action:** delete it. It is shadowed by the `regime/` package — Python resolves
`src.core.strategy.regime` to `regime/__init__.py`, so no import can ever reach it. Its
docstring is byte-identical to [src/core/strategy/regime/manual.py](../../src/core/strategy/regime/manual.py).
Also delete the 1-byte empty package [src/domain/](../../src/domain/) and the 34-byte
[src/core/account/](../../src/core/account/).

**Why it matters:** a module/package name collision is a thing an experienced reviewer notices
immediately and reads as "nobody has looked at this directory in months." Cheap to fix.

---

### B5. Add CI that runs the tests — P1 — 2 h

**Files:** new `.github/workflows/ci.yml`

**Action:** matrix on Python 3.11/3.12; `pip install -r requirements.txt -r requirements-dev.txt`;
run `ruff check src/`, `mypy src/`, `pytest -m "not binance and not integration" --cov=src
--cov-fail-under=65`. Add the badge to the README. Do this **after A5 and B6**, so it is green
on the first push.

**Why it matters:** a green CI badge is the single highest-signal-per-pixel element on a GitHub
page. It converts "he says there are 1,884 tests" into "1,884 tests passed 4 minutes ago." Its
absence on a repo pitched as a work sample reads as a deliberate omission.

---

### B6. Clear the lint and type errors — P1 — 5 h

**Files:** repo-wide; concentrated in `tests/` (214 of 290 ruff errors)

**Action:**
1. `ruff check --fix src/ tests/ scripts/ research/` — clears 194 of 290 automatically
   (mostly `F401` unused imports ×176).
2. Hand-fix the remainder: 27 `F821` undefined names (all in
   [tests/unit/test_risk_controller.py](../../tests/unit/test_risk_controller.py) — add
   `from typing import Any` and import `RiskController` at module level), 19 `E712` `== True`
   comparisons, 29 `F841` unused variables.
3. **mypy: fix the four real bugs first**, not the annotations —
   [orchestrator.py:464-469](../../src/core/orchestrator.py#L464) (moot if you take B3 option 1),
   [paper/engine.py:664](../../src/core/strategy/paper/engine.py#L664) (iterating a
   non-iterable `OHLCVSeries`), and
   [rsi_divergence_reversal.py:184,224](../../src/core/strategy/generators/rsi_divergence_reversal.py#L184)
   (`str` assigned to `float`).
4. The remaining ~20 mypy errors are one root cause: `TradingSignal.indicators` is typed
   `dict[str, float]` but seven generators pass strings. Widen the type to
   `dict[str, float | str]` in one place and they all clear.

**Why it matters:** README publishes `ruff check src/ tests/` and `mypy src/` as project
commands. Both fail. A reviewer who runs a command from your own README and gets 290 errors
concludes the quality tooling is decorative. Note that step 3 finds genuine bugs — this is not
purely cosmetic.

---

### B7. Write the configuration reference — P1 — 2 h

**Files:** new `docs/CONFIGURATION.md`; sources are
[scripts/run_live_trading.py](../../scripts/run_live_trading.py),
[src/core/config/settings.py](../../src/core/config/settings.py),
[railway.toml](../../railway.toml), [.env.example](../../.env.example)

**Action:** one table covering every env var with type, default, and effect. Must include the
live-trading controls currently documented only in `DECISIONS.md` prose and inline code:
`LIVE_TRADING_ENABLED` (default off), `LIVE_CAPITAL_USDT`, `PER_STRATEGY_ALLOCATION_PCT`
(0.20), `MAX_STRATEGIES_LIVE_CONCURRENT` (4), `CAPITAL_RESERVE_FRACTION` (0.85),
`POSITION_SIZE_FRACTION` (0.25). Include the `LIVE_CAPITAL >= $100` constraint and the reason
(Binance $5 minimum notional), because that reasoning is exactly the kind of thing that
impresses.

**Why it matters:** it demonstrates you understand your own operational envelope, and it is the
doc that makes the system look *operated* rather than *written*.

---

### B8. Surface the research layer — P1 — 2.5 h

**Files:** new `docs/research/README.md`; link from the main README; reference
[.claude/DECISIONS.md](../../.claude/DECISIONS.md)

**Action:** a short index of what is in `docs/research/` and why it is unusual — pre-registered
hypotheses, regime-conditional Deflated Sharpe screening, honest `REJECTED (FUNDAMENTAL)`
verdicts on your own strategies, strategy post-mortems, the 6-strategy retirement in
`DEC-2026-05-28-002`. Include the finding that spot long-only beat futures long-short for your
strategies, and that you therefore did **not** build live futures execution.

**Why it matters:** this is your strongest differentiator and it is currently invisible.
Killing six of your own strategies on statistical evidence and documenting why is a rarer
signal than any amount of clean code. Right now nothing in the README points at it.

---

### B9. Pin dependencies and reconcile the manifests — P1 — 1.5 h

**Files:** [requirements.txt](../../requirements.txt), [pyproject.toml:11-42](../../pyproject.toml#L11),
[requirements-dev.txt](../../requirements-dev.txt), new `requirements.lock`

**Action:** make `pyproject.toml` authoritative and generate a lockfile
(`pip freeze > requirements.lock` at minimum; `uv pip compile` if you want to look current).
Reconcile the disagreements: `python-telegram-bot` is in `pyproject.toml` only and is never
imported; `psutil` / `psycopg2-binary` / `aiohttp` are in `requirements.txt` only. Remove or
comment the five declared-but-unimported packages (`httpx`, `tenacity`, `aiosqlite`,
`psycopg2-binary`, `python-telegram-bot`).

**Why it matters:** *mostly internal quality only*, but three manifests that disagree is
visible in 30 seconds and reads as carelessness about reproducibility — a specific concern for
anything that touches money.

---

### B10. Add retry logic to broker calls — P1 — 2 h

**Files:** [src/brokers/binance/client.py](../../src/brokers/binance/client.py) (13% coverage);
`tenacity` is already a declared dependency with zero imports

**Action:** wrap the network methods in `@retry` with exponential backoff and jitter, excluding
non-retryable errors (auth failures, and the geo-block path that
[src/utils/geo_block.py](../../src/utils/geo_block.py) already handles correctly). Add unit
tests with a mocked transport — this also lifts that 13% coverage figure on the riskiest module
in the repo.

**Why it matters:** your own MVP rules cite "retry logic with exponential backoff" for Binance
failures as an in-scope requirement, and `tenacity` is installed for it. A reviewer who checks
how you handle exchange flakiness — and for a trading system, they will — finds nothing there.
This is the one functional gap in Bucket B.

---

## Bucket C — Optional

*None of these change a hiring decision. Do them because you want to.*

| # | Item | Files | Effort | Note |
| --- | --- | --- | --- | --- |
| C1 | Split `run_live_trading.py` (2,111 lines) into a package: tier activation, capital model, promotion gating, order submission, regime matching | [scripts/run_live_trading.py](../../scripts/run_live_trading.py) | 12 h | *Internal quality only* — but it is the file a reviewer opens to judge you, so there is some external value |
| C2 | Reconcile the live path with `src/core/risk/controller.py` so there is one risk implementation | [scripts/run_live_trading.py:968](../../scripts/run_live_trading.py#L968), [src/core/risk/controller.py](../../src/core/risk/controller.py) | 8 h | *Internal quality only* once B2's diagram explains the split honestly — but this is the deepest architectural debt in the repo |
| C3 | Test `src/core/event_bus.py` (0% coverage, 75 stmts) | [src/core/event_bus.py](../../src/core/event_bus.py) | 3 h | It is named in `DEC-2026-01-15-005` as core architecture and has no tests |
| C4 | Add template YAMLs for the 15 generators that lack them, or drop the YAML layer for generators that do not use it | [config/templates/](../../config/templates/) | 4 h | Removes the split-brain config model |
| C5 | API route tests — 9 of 14 route modules at 0% unit coverage | [src/api/routes/](../../src/api/routes/) | 6 h | Integration tests partly cover these; the gap is smaller than it looks |
| C6 | Fix the swallowed exception | [src/core/strategy/paper/engine.py:469](../../src/core/strategy/paper/engine.py#L469) | 0.5 h | One `except Exception: pass` in 66k lines |
| C7 | Commit or discard the 71 uncommitted working-tree files | working tree | 1 h | A dirty tree at publication time is untidy but invisible after push |
| C8 | Trim `.dockerignore` to exclude `docs/` from the image | [.dockerignore](../../.dockerignore) | 0.25 h | 25 MB of design PDFs currently ship in the container |
| C9 | Decide whether to publish the 267 KB `DECISIONS.md` | [.claude/DECISIONS.md](../../.claude/DECISIONS.md) | 0.5 h | Recommendation: **publish it.** It is the best evidence of judgement in the repo. Just make the choice deliberately |

---

## The shortest path — 10 focused hours

If you do nothing else, do these in this order. This sequence captures most of the credibility
gain and every P0.

| # | Task | Time | Cumulative | What it buys |
| --- | --- | --- | --- | --- |
| 1 | **A3** — clear 35 `SESSION_*` files + 17 loose root scripts | 1.5 h | 1.5 h | Removes the #1 and #2 tab-closers. Nothing else matters if a reviewer stops at `ls`. |
| 2 | **A1 + A2** — correct vectorbt / CCXT / Optuna / agent claims | 2.5 h | 4.0 h | Removes the risk that a single verified-false claim discredits the whole repo. Protects your CV. |
| 3 | **A5** — make `pytest` green (markers, settings isolation, 6 stale assertions, 2 real regressions) | 3.0 h | 7.0 h | Converts 1,884 tests from a liability into your strongest asset. Finds real bugs on the way. |
| 4 | **A4 + A6 + A7 + A8** — LICENSE, disclaimer, `requests`, frontend label, drop 25 MB of PDFs | 1.5 h | 8.5 h | Closes every remaining P0. The repo is now publishable. |
| 5 | **B1 (compressed) + B2** — README rewrite with real numbers and one Mermaid diagram | 1.5 h | 10.0 h | Turns "I cannot tell what this does" into "this person designs systems." |

**At 10 hours you have:** a clean root, honest claims, a green test suite, a license and
disclaimer, and a README with a diagram and real numbers. That is publishable and linkable.

**The next 4 hours, if you find them,** should go to **B5 (CI, 2 h)** and **B3 option 1
(delete the dead orchestrator, 2 h)** — a green badge plus the removal of the clearest
"generated but never integrated" artifact in the repo.

**Explicitly deferred:** B10 (broker retries) is the only functional gap in the plan, and B6
(lint/mypy) contains three genuine bugs. Neither blocks publication, but do not let them slide
past your first application.
