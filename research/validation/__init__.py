"""Statistical validation primitives for the research layer.

Mandatory methodology primitives per DEC-2026-06-04-002. The Deflated Sharpe
Ratio (`deflated_sharpe`) is the non-negotiable statistical floor for all
promotion decisions (DEC-2026-06-04-008): no strategy with DSR p-value >= 0.3
may deploy at any capital allocation.
"""
