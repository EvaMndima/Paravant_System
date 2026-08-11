# Building PARAVANT with AI Assistance

**Written:** 2026-08-11
**Covers:** 2026-02-08 to 2026-08-11, 114 commits, one human author

This document exists because the alternative was worse. PARAVANT is roughly
120,000 lines written over six months by one person working with AI coding
assistants. Publishing that without saying so would be dishonest, and hiding
it would waste the most transferable thing the project produced: a fairly
precise picture of where AI-assisted development succeeds, where it fails,
and what has to be built to catch the failures.

The repository previously contained 35 `SESSION_*_IMPLEMENTATION_PROMPT.md`
files at its root -- the raw prompts. They were removed in favour of this
document. They remain in git history at tag `pre-cleanup`.

Sections 3 and 4 are the ones worth your time. Section 3 is what worked.
Section 4 is what went wrong, with the specific defects and how long each
survived.

---

## 1. What was built

| Layer | Files | Lines |
|---|---|---|
| `src/` application | 167 `.py` | 49,144 |
| `tests/` | 133 `.py` | 36,363 |
| `frontend/src/` | 89 `.ts`/`.tsx` | 17,128 |
| `scripts/` operational entrypoints | 24 | 11,865 |
| `research/` validation library | 27 `.py` | 5,411 |

A crypto trading system: Binance data ingestion, 19 indicators, 29 signal
generators, a layered risk system, an order state machine, backtest and paper
engines sharing the live code path, a FastAPI surface of 63 endpoints, a React
dashboard, and a statistical research layer whose purpose is to reject the
system's own strategies.

It found no trading edge. All 11 strategies were rejected under Deflated Sharpe
Ratio on 2026-06-05, and two subsequent hypotheses were rejected after that.
That result is documented in `docs/research/` and is treated as the project's
finding rather than its failure.

---

## 2. The working method

Work proceeded in numbered sessions. Each session had a written prompt stating
scope, the decisions it had to honour, and its acceptance criteria; the
assistant implemented against that prompt; a separate verification pass checked
the result against the criteria. The prompts were versioned in the repository
while the work was live.

Three things sat underneath every session and did most of the real work:

**`.claude/DECISIONS.md`** -- 116 dated decision entries across 3,060 lines,
each recording the decision, its context, its rationale, the alternatives
considered and rejected, and its status. Maintained identically in `.agent/` so
that different assistants could not diverge on what had been decided.

**`.claude/rules/`** -- three enforcement files:

- `decision-consistency.md` requires reading the decision log *before*
  implementing, and requires refusing work that contradicts an active decision.
- `zero-technical-debt.md` covers backward compatibility, naming stability,
  behaviour-preserving refactors, one-intent-per-change, and rollback readiness.
- `mvp-scope-control.md` lists locked scope decisions and gives an explicit
  template for rejecting out-of-scope requests.

**The scope lock.** Crypto only, Binance only, spot only, market orders only,
monolith only. Each locked with a review date rather than a vague intention.

The rules exist because an assistant that always agrees is a liability. Their
practical function is to give it grounds to say no -- to a request, and to the
author.

---

## 3. What worked

### 3.1 Written decisions with rejected alternatives

The single highest-value artifact. 69 distinct decision IDs are referenced in
source comments, so the rationale is reachable from the code rather than only
from a document nobody opens.

The part that mattered most was recording *rejected* alternatives. Without it,
the same question gets reopened every few weeks and answered differently
depending on what the assistant last saw. With it, reopening a decision costs
one grep.

### 3.2 Rules that produce refusals

Scope creep is the natural failure mode of a capable assistant and an
enthusiastic author. Encoding the scope lock as a rule file with a rejection
template converted "should we add limit orders?" from a conversation into a
lookup.

### 3.3 Building the thing that grades you

The research layer is the strongest engineering in the repository, and it was
built to reject the project's own output. Deflated Sharpe Ratio, effective-trial
counting, gates fixed before results are seen, a cost model deliberately biased
pessimistic, and a pre-registered date at which the project evaluates whether to
stop.

That machinery was then pointed at six months of the author's own work and
returned: nothing here is real. It was reported rather than re-tuned.

This generalises past trading. An assistant will help you build a thing and will
also help you believe in it. The countermeasure is to build the adversarial
evaluator *first*, while you have no results to protect.

### 3.4 Mechanical verification of what is mechanically verifiable

Where a property could be checked by machine, it held up well: 19 indicators at
88-100% coverage, risk sizing at 100%, an equivalence test proving an O(n)
backtest path returns results identical to the O(n^2) path it replaced.

---

## 4. What went wrong

The failures share a shape: **locally correct code that is globally
disconnected, plus verification that agreed with the code instead of checking
it.**

### 4.1 Verification shaped like the defect

The worst one. `StartupChecklist._check_strategies` called
`StrategyEngine.create_strategy()` with four keyword arguments that do not
exist on its signature, and read three attributes the `Strategy` model does not
have plus one it never had. Every call raised. A bare `except Exception`
reported the result as "Strategy <name> validation failed", so the message
blamed the data.

It survived roughly six months. The reason is the important part: every
orchestrator test passed `MagicMock()` as the strategy engine, and a mock
accepts any call with any arguments. Worse, the fixture in `test_all_checks_pass`
described its strategy using the same non-existent field names the broken code
expected -- and named a template that does not exist. **The test had been
written to match the defect rather than the model, and then asserted that a
check which could never pass in production did pass.**

An assistant asked to write a test for code it just wrote will tend to encode
the same misunderstanding twice. Two artifacts, one belief, and a green tick.

The fix (DEC-2026-08-11-001) validates against `TemplateManager` directly and
writes nothing, with five tests exercising a real `StrategyEngine`. Programming
errors now propagate instead of being reported as check failures
(DEC-2026-08-11-002) -- swallowing them is what made the defect undiagnosable.

### 4.2 Unintegrated completeness

`src/core/orchestrator.py` is 1,853 lines implementing an eight-step startup
sequence, a kill-switch-first main loop, entry-timing coordination, graceful
degradation, and emergency shutdown with position reconciliation. It is
coherent, documented, and 71% covered by tests.

Nothing calls it. `set_orchestrator()` is defined in the API layer and invoked
nowhere, so the module-level handle is permanently `None` and `/system/start`
and `/system/stop` cannot work. The system that actually deploys is
`scripts/run_live_trading.py`, which independently reimplements the loop.

No test failed, because the orchestrator's tests test the orchestrator. Local
coherence is not integration, and a test suite scoped to a module cannot tell
you the module is orphaned. This is recorded rather than quietly deleted; it is
a real duplication and it is unresolved.

### 4.3 Namespace collisions from incremental refactors

`src/core/strategy/regime.py` and `src/core/strategy/regime/` both existed.
CPython resolves packages before same-named modules, so the file had been dead
since the package was created. A later session had migrated its contents into
`regime/manual.py` and correctly re-exported them -- and left the original in
place.

Each session was right about its own scope. Nobody was responsible for the
seam.

### 4.4 Documentation drifting off the system

`README.md` was last modified in the initial commit and then described the
project for six months while the project changed underneath it. It advertised
six strategy templates when 29 generators existed, and never mentioned the
research layer -- the most interesting thing in the repository.

Prose has no test suite. It rots silently in a way code does not.

### 4.5 Build artifacts nobody owned

`.claude/skills` and `.agent/skills` were committed as gitlinks with no
`.gitmodules` file, so any fresh clone produced two empty directories that
`git submodule update --init` could not repair. It never broke a local machine,
so it was never noticed.

### 4.6 An audit that read the signature but not the body

Near the end, an AI audit reviewed the repository and correctly identified the
defect in 4.1. Its recommended fix was to correct the keyword arguments to match
the real signature.

That fix would have made things worse. `create_strategy()` persists -- it calls
`DataStore.save_strategy()` and hardcodes `StrategyStatus.DRAFT`, with no
parameter to opt out. Corrected keyword arguments would have converted a loud
`TypeError` into a silent write of one duplicate strategy row per active
strategy, on every startup, forever.

The audit read the function's signature and not its body. The lesson is narrow
and worth stating precisely: **an AI review is a strong generator of leads and a
weak source of verdicts.** Every finding in that audit was checked against the
source before it was acted on, and this one changed under inspection.

---

## 5. What this suggests

1. **Mocks are where AI-assisted verification goes to die.** A mock accepts any
   call. Where an interface boundary matters, at least one test must cross it
   for real. The single most valuable test added during cleanup constructs a
   real `StrategyEngine`.

2. **Ask what would fail if this module were deleted.** If the answer is "only
   its own tests", it is not integrated. Nothing in a conventional suite asks
   this question.

3. **Write the decision, the alternatives, and why they lost.** Context windows
   end; the log does not. This is cheap and it compounds.

4. **Give the assistant grounds to refuse.** A rule file it must read before
   implementing is the closest available thing to a second opinion.

5. **Build the evaluator before you have results to defend.** The DSR layer
   could return "all of it is noise" because it was designed before there was
   anything to protect.

6. **Treat AI review as leads, not verdicts.** Section 4.6 is one audit finding
   away from a data-corruption bug shipped in the name of fixing a bug.

7. **Documentation needs an owner or it will lie.** Six months of accurate code
   and a stale README is a net-negative repository for a first-time reader.

---

## 6. Disclosure

The code in this repository was written by one person working with AI coding
assistants throughout. The architecture, the scope decisions, the research
methodology, and every judgment call recorded in `DECISIONS.md` are the author's.
The implementation was largely assistant-generated against written specifications
and then reviewed.

This document was itself drafted with assistance, from a repository audit and
from verification performed against the source. Every figure in Section 1 was
measured with commands runnable against this repository. Every defect in
Section 4 was confirmed by reading the code, and the fixes for 4.1, 4.3 and 4.5
are in the commit history of the `cleanup/pre-publication` branch. The
duplication in 4.2 is open.
