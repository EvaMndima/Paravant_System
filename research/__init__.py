"""PARAVANT Research Layer.

A research-grade extension to the trading system. Governed by
`docs/research/RESEARCH_LAYER_PRD.md` v2.0 (DEC-2026-06-04-001).

DEPENDENCY RULE (DEC-2026-06-04-001): `src/` does NOT import from
`research/`. `research/` may import from `src/` freely. Strategies graduate
from `research/generators/` to `src/core/strategy/generators/` by moving the
file via `scripts/promote_to_production.py` (DEC-2026-06-04-004).
"""
