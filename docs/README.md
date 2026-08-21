# Documentation

Start with the three under **Orientation**. Everything else is reference.

## Orientation

| Document | What it is |
|---|---|
| [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Complete briefing on the system. Readable end to end without opening a source file. |
| [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md) | What the research actually established, what was withdrawn, and why. The project's headline result. |
| [AI_ASSISTED_DEVELOPMENT.md](AI_ASSISTED_DEVELOPMENT.md) | How this was built with AI assistance, the fifteen specific defects that produced, and the moves that found them. |

## Engineering

| Document | What it is |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | The system as built, including where it diverged from its own design. |
| [API_CONTRACT.md](API_CONTRACT.md) | The 63-endpoint HTTP surface. |
| [INDICATOR_SPECIFICATION.md](INDICATOR_SPECIFICATION.md) | The 19 indicator implementations. |
| [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) | Detailed local setup beyond the README quickstart. |
| [TRADING_SYSTEM_PRD.md](TRADING_SYSTEM_PRD.md) | The original product requirements. Historical, and the source of the locked scope. |
| [PRODUCTION_READINESS_ASSESSMENT.md](PRODUCTION_READINESS_ASSESSMENT.md) | Measured gaps and the plan to close them. Written to be uncomfortable. |

## Research

The intellectually distinctive part of the project. Its purpose is to reject
this system's own strategies.

| Document | What it is |
|---|---|
| [research/RESEARCH_PROTOCOL.md](research/RESEARCH_PROTOCOL.md) | The method, and what it forbids. Read before the results. |
| [research/HYPOTHESIS_QUALITY_GATE.md](research/HYPOTHESIS_QUALITY_GATE.md) | The Stage-1 scorecard every hypothesis must pass. |
| [research/NEGATIVE_SPACE_MAP.md](research/NEGATIVE_SPACE_MAP.md) | Where edge has been proven absent. Treated as a first-class result. |
| [research/RESEARCH_FIXLIST.md](research/RESEARCH_FIXLIST.md) | The research layer's own known defects. Six still open. |
| [research/RESEARCH_LAYER_PRD.md](research/RESEARCH_LAYER_PRD.md) | The research layer's build plan. |
| [research/RETROSPECTIVE_DSR_SPEC.md](research/RETROSPECTIVE_DSR_SPEC.md) | Specification for the retrospective Deflated Sharpe run. |
| [research/PORTFOLIO_LAYER_DESIGN.md](research/PORTFOLIO_LAYER_DESIGN.md) | Deferred design for correlation-aware allocation. |
| [research/retrospective/](research/retrospective/) | Per-strategy DSR post-mortems. Several carry SUPERSEDED banners; the errors are kept, labelled. |
| [research/regime_dsr/](research/regime_dsr/) | Regime coverage matrices from the screening runs. |

## Operations

| Document | What it is |
|---|---|
| [operations/kill_switch_runbook.md](operations/kill_switch_runbook.md) | How to halt trading. |
| [operations/RAILWAY_CRONS.md](operations/RAILWAY_CRONS.md) | Scheduled jobs, including the daily validation report. |

## Review

| Document | What it is |
|---|---|
| [audit/AUDIT.md](audit/AUDIT.md) | Read-only pre-publication audit. |
| [audit/ROADMAP.md](audit/ROADMAP.md) | The roadmap that audit produced. |

## Design

| Document | What it is |
|---|---|
| [design/DESIGN_GUIDE.md](design/DESIGN_GUIDE.md) | Design tokens, palettes and component conventions. |
| [design/references/](design/references/) | Vendored UI prototypes the production frontend was built from. |

## Archive

[archive/](archive/) holds superseded build plans, completed phase trackers, and
AI session prompts. They describe finished work and are kept for history rather
than reference. See [archive/README.md](archive/README.md).

## Decision log

Not under `docs/`. 135 dated architectural decisions with rationale and rejected
alternatives live in [`.claude/DECISIONS.md`](../.claude/DECISIONS.md),
maintained byte-identically in `.agent/DECISIONS.md`.
