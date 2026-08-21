# Session prompt — LLM hypothesis evaluation build

Copy everything below the line into a new chat session in this repository.

---

I am building an LLM hypothesis-generation and evaluation module in the
PARAVANT repository. Work through it **phase by phase**, and stop for my
approval at the end of each phase.

## Read these first, in this order

1. `docs/research/LLM_HYPOTHESIS_EVAL_SPEC.md` — the pre-registered spec for
   this work. It fixes what is measured and what counts as success. Do not
   change its criteria without telling me explicitly that you are doing so and
   why; the whole point of pre-registration is that criteria are not adjusted
   after seeing results.
2. `.claude/CLAUDE.md` and `.claude/rules/` — project rules. These are
   mandatory, not advisory.
3. `docs/research/RESEARCH_PROTOCOL.md` — the research method this work must
   respect.
4. `docs/RESEARCH_FINDINGS.md` — what this project has already established, and
   the correction it had to make.
5. `docs/AI_ASSISTED_DEVELOPMENT.md` sections 4, 5 and 6 — the fifteen failure modes
   found in this repository. Do not reproduce them.

## Repository state

Everything is green and must stay that way.

```
1,899 tests passing, 37 skipped, 0 failing
ruff       0 findings across src, research, scripts, tests
mypy       0 findings across src/ and research/features/
eslint     0 errors (80 documented warnings)
CI         9 jobs, all required, all green
```

Verify with:

```bash
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe -m ruff check src/ research/ scripts/ tests/
.venv/Scripts/python.exe -m mypy src/ research/features/
python scripts/doc_stats.py
```

Dependencies are pinned exactly in `requirements.txt` and
`requirements-dev.txt`. If you add one, pin it, and read the comment at the top
of those files explaining why.

## Hard constraints

- **`src/` must never import `research/`.** One-way dependency,
  DEC-2026-06-04-001. All new code goes under `research/llm/`.
- **No emoji or non-ASCII in code.** A check-mark in a print statement made the
  documented quickstart exit 1 on Windows; there is a CI job guarding the
  quickstart now, and DEC-2026-08-13-007 records the rule.
- **Every decision gets filed** in BOTH `.claude/DECISIONS.md` and
  `.agent/DECISIONS.md`, verified byte-identical with `diff`. Next id is in the
  metadata block near the end of the file.
- **CI must stay green.** Run the checks above before every commit. Do not push
  a red build.
- **Nothing touches live trading.** The kill switch stays off. This module never
  places an order.

## What I expect to find, so you are not surprised by it

The likely result is null: the LLM will produce hypotheses that score well on
the Stage-1 rubric while being no more novel and no better at predicting
outcome than the human baseline of r = +0.146.

**That is the expected finding and it is worth publishing.** Do not tune prompts
or swap models to obtain a more flattering number. If a result looks positive,
treat it as a suspected defect first — check for leakage, check trial
accounting, check that the baseline is fair.

The deliverable is the evaluation harness and an honest result, not a
particular direction of result.

## Working method

For each phase:

1. Tell me what you are about to build and why, briefly.
2. Read the existing code you are integrating with **before** writing anything.
   This repository has a documented history of defects caused by assuming an
   interface rather than reading it, including a function called with four
   keyword arguments that did not exist and a test written to match the defect
   rather than the specification.
3. Build it, with tests.
4. Run the full verification set above.
5. Commit with a message that explains the reasoning, not just the change.
6. Stop and report. Wait for my approval before the next phase.

Be critical. If something in the spec is wrong or will not work, say so rather
than building it. If you find a defect in existing code, tell me before working
around it.

## Start with Phase 1

`research/llm/client.py` — a provider-agnostic chat client with:

- Response caching keyed on `hash(prompt + model + params)`, so a warm re-run
  makes zero network calls and reproduces results exactly
- Token and cost accounting per call
- Retries with backoff, and a **failure taxonomy** that counts schema
  violations, refusals, truncations and timeouts separately rather than
  retrying them away silently
- Structured output enforced against a Pydantic schema
- Prompt content-hashing, recorded with every response

Before writing it, ask me which provider and model to target, and check whether
an API key is available in the environment. Do not commit a key, and do not
print one.

Tests must run with **no network access** — the client's cache and failure paths
should be exercised against a stub, in keeping with `tests/conftest.py`, which
already strips credentials and skips network tests unless
`PARAVANT_RUN_NETWORK_TESTS=1`.
