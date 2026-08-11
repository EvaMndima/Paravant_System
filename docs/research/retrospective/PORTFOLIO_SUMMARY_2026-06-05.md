# Retrospective DSR Portfolio Summary

**Date:** 2026-06-05
**Strategies Analyzed:** 11 (5 KEEP, 6 RETIRED)
**Cost Model:** v0_unverified (incremental-pad; 2x on estimated components)

| Strategy | Status | Tier | DSR p (gate) | DSR p (base) | PF (adj) | Sharpe (adj) | N | Fragile | Action |
|----------|--------|------|--------------|--------------|----------|--------------|---|---------|--------|
| MACD_PB | KEEP | TIER_D_REJECT | 0.999 | 0.996 | 0.00 | -2.385 | 2 | False | retire |
| RSI_BB | RETIRED | TIER_D_REJECT | 1.000 | 0.998 | 2.94 | 0.324 | 3 | False | retire |
| CMF | RETIRED | TIER_D_REJECT | 1.000 | 1.000 | 0.67 | -0.170 | 4 | False | retire |
| ICVP | KEEP | TIER_D_REJECT | 1.000 | 1.000 | 0.37 | -0.391 | 4 | False | retire |
| BTP | KEEP | TIER_D_REJECT | 1.000 | 1.000 | 0.00 | 0.000 | 0 | False | retire |
| VBB | KEEP | TIER_D_REJECT | 1.000 | 1.000 | 0.00 | 0.000 | 0 | False | retire |
| SRC | KEEP | TIER_D_REJECT | 1.000 | 1.000 | 0.00 | 0.000 | 0 | False | retire |
| BTF | RETIRED | TIER_D_REJECT | 1.000 | 1.000 | 0.54 | -0.253 | 25 | False | retire |
| HATP | RETIRED | TIER_D_REJECT | 1.000 | 1.000 | 0.00 | 0.000 | 0 | False | retire |
| VRB | RETIRED | TIER_D_REJECT | 1.000 | 1.000 | 0.00 | 0.000 | 0 | False | retire |
| VPT | RETIRED | TIER_D_REJECT | 1.000 | 1.000 | 0.00 | 0.000 | 0 | False | retire |

## Headline Findings

- KEEP strategies surviving DSR floor (p<0.3, conservative): 0 of 5
- KEEP at Tier A: 0
- KEEP at Tier B: 0
- KEEP at Tier C: 0
- KEEP at Tier D: 5
- RETIRED confirmed (Tier C/D): 6 of 6
- RETIRED surprises (Tier A/B -- warrant re-examination): 0

## Decisions Triggered

Any KEEP strategy whose tier changed has a PENDING-DEC note appended to its biography decision_log. File the DEC entry in BOTH .claude/DECISIONS.md and .agent/DECISIONS.md (next id DEC-2026-06-04-013) after operator review, then verify with `diff`.
