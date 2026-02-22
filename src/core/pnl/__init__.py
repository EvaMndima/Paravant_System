"""PnL tracking module.

This namespace package exists for organisational clarity. All P&L business
logic lives in the execution layer, not here:

  - Real-time P&L calculations and position tracking:
      src/core/execution/position_tracker.py  (PositionTracker class)

  - Trade-level P&L records (fills, commissions, slippage):
      src/core/execution/quality.py  (SlippageTracker, FillRateTracker)

  - Historical P&L persistence:
      src/data/store.py  (DataStore.get_orders_for_account, etc.)

Design decision: P&L logic was kept in the execution layer (position_tracker.py)
rather than moved here to avoid import cycle risk and preserve the cohesion of
fill processing with P&L accounting. Do NOT move code here without updating all
imports and confirming no circular dependencies.
"""
