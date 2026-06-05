"""Strategy biographies — the institutional memory layer (PRD Section 13.4).

Every strategy has one continuous biography from hypothesis to retirement. The
biography YAML is the CANONICAL store of DSR results, tier classification, and
cost-adjusted metrics (Appendix A schema). Markdown/JSON reports are derived
views that can be regenerated from the biography at any time.

Research-only code: ``src/`` must never import from here (PRD Section 5.2).
"""
