# LLM Hypothesis Generation — Pre-Registered Evaluation Spec

**Status:** PRE-REGISTERED. Written before any generation run.
**Registered:** 2026-08-13
**Decision:** DEC-2026-08-13-003 (to be filed on approval)

This document fixes what will be measured, what counts as success, and what
counts as failure, **before** any LLM output is produced. It exists for the same
reason `RESEARCH_PROTOCOL.md` exists: a criterion chosen after seeing results is
not a criterion.

---

## 1. The question

**Can a large language model generate trading hypotheses that are better than
the ones a human produced — and does the project's own quality rubric detect
the difference?**

The second half is the load-bearing part. This is an evaluation of the
*evaluator* as much as of the model.

### 1.1 Why this is worth running

The human-generated record already suggests the rubric does not work.

Across the seven screened hypotheses in `research/hypotheses/ledger.yaml`, the
Stage-1 quality score correlates with realised profit factor at **Pearson
r = +0.146**, and the lower-scoring half performed *better* (mean PF 0.73 vs
0.54). H-2026-06-003 scored 18/21 and returned PF 0.53; H-2026-06-002 scored
14/21 and returned PF 0.59.

If a rubric barely predicts outcome for human hypotheses, the interesting
question is what it does when pointed at a generator that is *optimised for
producing text that satisfies rubrics*. That is a direct, concrete instance of
Goodhart's law, measurable on a real gate.

### 1.2 What this is NOT

Stated plainly, because scope creep here would waste the effort:

- **Not an attempt to find a profitable strategy.** Eleven strategies and eleven
  forward hypotheses have been rejected. The prior that an LLM proposing further
  indicator combinations finds edge is very close to zero. Any result claiming
  otherwise should be treated as a bug until proven otherwise.
- **Not machine learning.** Nothing is trained. This is LLM application
  engineering and evaluation infrastructure.
- **Not an autonomous research agent.** The human gate is preserved at every
  stage. The model proposes; it does not decide.

---

## 2. Power, stated before the fact

The binding constraint on this study is sample size, and pretending otherwise
would repeat the exact error corrected in `RESEARCH_FINDINGS.md` section 3.

| Measurement | Achievable n | Power | Status |
|---|---|---|---|
| Novelty / duplicate rate | 100+ | High | **Confirmatory** |
| Hard-gate pass rate | 100+ | High | **Confirmatory** |
| Score distribution vs human | 100 LLM vs 11 human | Moderate | **Confirmatory** |
| Mechanism-class diversity | 100+ | High | **Confirmatory** |
| LLM-as-judge vs human scores | 11 | Low | **Exploratory** |
| Score-to-outcome correlation | ~5-10 | Very low | **Exploratory only** |

**The outcome-correlation comparison is underpowered and is pre-registered as
exploratory.** A correlation estimated at n < 30 carries a confidence interval
wide enough to contain almost anything. It will be reported with its interval
and will not be described as evidence for or against, in either direction.

The confirmatory claims are the ones that need no backtest, and that is
deliberate: they are the questions this study can actually answer.

---

## 3. Hypotheses and pre-registered criteria

### H1 — Novelty (confirmatory)

> An LLM asked for novel trading hypotheses will predominantly propose mechanism
> classes already recorded as exhausted.

`docs/research/NEGATIVE_SPACE_MAP.md` records six mechanism classes rejected for
TRENDING_BULL at N between 75 and 341. `src/core/strategy/similarity.py` detects
structural duplicates of existing strategies.

- **Measured:** share of generated hypotheses that are (a) structural duplicates
  of an existing or retired strategy, or (b) a mechanism class already in the
  negative-space map for the same regime.
- **Pre-registered threshold:** H1 is **supported** if the combined rate exceeds
  50%. It is **rejected** if below 25%.
- Between 25% and 50% is reported as inconclusive, not spun either way.

### H2 — Rubric gaming (confirmatory)

> LLM-generated hypotheses will score at least as well as human-generated ones
> on the Stage-1 rubric.

- **Measured:** distribution of Stage-1 totals (0-21), LLM vs the 11 human
  hypotheses on record. Mann-Whitney U, reported with effect size.
- **Pre-registered threshold:** H2 is **supported** if the LLM median is greater
  than or equal to the human median.
- If H2 is supported *and* H1 is supported, the joint finding is the headline:
  **the rubric rewards articulacy that novelty analysis contradicts.**

### H3 — LLM as judge (exploratory)

> An LLM scoring the 11 existing hypotheses will agree with the recorded human
> scores.

- **Measured:** Spearman correlation and mean absolute deviation between LLM and
  recorded human Stage-1 totals, on hypotheses whose outcomes are withheld from
  the prompt.
- **n = 11. Exploratory. Reported with interval, no threshold.**

### H4 — Outcome prediction (exploratory)

> LLM scores predict realised profit factor better than human scores do
> (baseline r = +0.146, n = 7).

- **n <= 10. Exploratory. Reported with interval, no threshold.**

---

## 4. Baselines

A generator with no baseline is a demo. Three are required:

1. **Human baseline.** The 11 hypotheses in `ledger.yaml`, with recorded scores
   and, for seven, outcomes.
2. **Random baseline.** Hypotheses assembled by sampling uniformly from the
   available indicator, regime and data-channel vocabulary, with a template
   rationale. This establishes what the rubric scores when there is provably no
   reasoning behind the text — the single most important comparison in the
   study.
3. **Ablated-LLM baseline.** The same model with the economic-reasoning
   requirement stripped from the prompt. Isolates how much of any score
   advantage comes from reasoning versus from fluency.

If the random baseline scores comparably to the LLM, the rubric is measuring
surface form. That result would be worth more than a positive one.

---

## 5. What gets built

All under `research/llm/`, respecting the one-way dependency: `research/` may
import `src/`, never the reverse (DEC-2026-06-04-001).

```
research/llm/
  client.py        provider-agnostic chat client: caching, cost accounting,
                   retries, timeout, structured-output enforcement
  schema.py        Pydantic models for a generated hypothesis, matching the
                   ledger.yaml shape so output is directly comparable
  prompts/         versioned prompt templates, content-hashed
  generate.py      generation runs, seeded and replayable
  judge.py         LLM-as-judge scoring against the Stage-1 rubric
  novelty.py       duplicate and negative-space detection
  baselines.py     random and ablated generators
  evaluate.py      the harness: metrics, tests, intervals, report
scripts/
  llm_hypothesis_eval.py    runner
docs/research/
  LLM_HYPOTHESIS_FINDINGS.md    the write-up, written last
```

### 5.1 Non-negotiable engineering properties

These are what make it an artifact rather than a script:

- **Deterministic replay.** Every API response cached by
  `hash(prompt + model + params)`. A re-run with the cache warm makes zero
  network calls and reproduces the report byte-for-byte. Without this, no result
  in the study is checkable.
- **Cost accounting.** Tokens and dollars recorded per call, per phase, per
  accepted hypothesis. Reported in the findings.
- **Prompt versioning.** Prompts are content-hashed and the hash is recorded
  with every output. A changed prompt is a different experiment.
- **Structured output with a failure taxonomy.** Schema violations, refusals,
  truncations and timeouts counted separately, not silently retried away. The
  failure profile is itself a finding.
- **Trial accounting.** Every generated hypothesis that reaches a backtest
  counts toward effective-K (`research/validation/effective_k.py`). An LLM that
  proposes 100 ideas has consumed 100 trials, and the DSR correction must know
  that. **This is the point at which the existing statistical machinery does
  real work on LLM output, and it is the core technical contribution.**

---

## 6. Phases

Each phase produces something of standalone value. Stopping after any of them
leaves a coherent artifact.

| Phase | Deliverable | Days | Standalone value |
|---|---|---|---|
| 0 | This spec, filed as a decision | 0.5 | Pre-registration on record |
| 1 | `client.py` + caching + cost + failure taxonomy + tests | 2-3 | A reusable, tested LLM client |
| 2 | `schema.py`, `generate.py`, `novelty.py`; H1 measured | 3 | The novelty finding, no backtests needed |
| 3 | `judge.py`, `baselines.py`, `evaluate.py`; H2, H3 measured | 3 | The rubric-gaming finding |
| 4 | Optional: backtest a small set; H4 measured | 2-4 | Exploratory only |
| 5 | `LLM_HYPOTHESIS_FINDINGS.md`, README section | 1 | The write-up |

**Realistic total: 10-14 working days.** Not one week. Phases 1-3 carry the
portfolio value; phase 4 is optional and low-power by construction.

---

## 7. Cost and prerequisites

- An API key for one provider. Budget **USD 20-50** for the full study; caching
  means repeated runs cost nothing.
- No GPU, no training, no new infrastructure.
- Model choice is recorded, not tuned for the result. Switching models to obtain
  a better number would be the same error as moving a gate.

---

## 8. How this can fail, and what happens then

| Failure | Response |
|---|---|
| LLM output does not validate against the schema | Counted in the failure taxonomy and reported. A high rate is a finding about structured-output reliability, not a blocker. |
| Novelty detection is too permissive or too strict | Calibrate against the 11 known hypotheses **before** running generation, and record the calibration. |
| Results are null across the board | This is the expected outcome and is reported as the result. The harness is the artifact. |
| Scope drifts toward "an agent that trades" | Out of scope, and blocked by the live kill switch and the promotion gate regardless. Nothing here touches live capital. |
| An LLM hypothesis appears to show edge | Treated as a suspected defect first. It would need to survive DSR with LLM trials counted in K, plus a leakage audit through `research/features/`, before being described as anything. |

---

## 9. What a reader should be able to conclude

If this is done properly, someone reading the repository can verify:

- An LLM was integrated with caching, cost control, structured outputs and an
  explicit failure taxonomy.
- Its output was evaluated against **three** baselines including a random one.
- The evaluation criteria were fixed in advance, in this file, and the git
  history shows this file predates the results.
- Statistical power was stated before the fact, and underpowered comparisons
  were labelled exploratory rather than reported as findings.
- The result was published whichever way it came out.

That set of properties is the deliverable. The direction of the result is not.
