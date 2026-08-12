# Archive

Documents describing work that is finished. Kept for history, not for
reference. Nothing here is maintained, and some of it is contradicted by the
current system.

Read [`docs/`](../README.md) instead.

## What is in here

| Directory | Contents |
|---|---|
| `build-plans/` | The MVP task index, seven per-phase implementation plans, a PRD gap analysis, a database seed-data spec, and completed-task summaries. The phases they describe are complete. |
| `design-plans/` | The frontend rebuild plan and its nine design phases, from the 2026-03 rebuild after a Tailwind v4 dark-mode failure. |
| `session-prompts/` | AI session prompts. Same category as the 35 `SESSION_*` files removed from the repository root -- build scaffolding, not documentation. Four are kept as a sample of the working method; the rest are recoverable from history at tag `pre-cleanup`. |
| `ARCHITECTURE_2026-02-08_original_design.md` | The pre-implementation architecture document, never updated. Kept because the gap between it and the built system is informative -- see section 10 of the current [ARCHITECTURE.md](../ARCHITECTURE.md). |
| `READING_QUEUE.md` | A research reading list. |

## Why keep them at all

Two reasons.

The build plans record what was intended before it was built, which is what
makes the divergence section of the current architecture document checkable
rather than a claim.

The session prompts are the honest record of an AI-assisted workflow. Deleting
them entirely would have been the tidier choice and a less truthful one. The
curated account is [AI_ASSISTED_DEVELOPMENT.md](../AI_ASSISTED_DEVELOPMENT.md).

## A caution

Paths inside these documents point at locations from before the archive move,
and several reference files that no longer exist. They were not rewritten:
editing a historical record to make its links resolve would misrepresent what
it said at the time.

The decision log (`.claude/DECISIONS.md`) likewise still cites the original
paths of documents moved here. Those citations are accurate as of the date each
decision was made, which is the point of a decision log.
