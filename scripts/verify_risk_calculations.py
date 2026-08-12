import asyncio
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

from src.core.risk.types import OrderRequest, PortfolioState
from src.core.config.risk_profiles import RiskProfileConfig, RegimeAdjustments
from src.core.risk.checks import (
    check_position_size,
    check_concentration
)
from src.core.risk.sizing import (
    calculate_fixed_risk_size,
    calculate_atr_size,
    calculate_available_capital
)

async def main():
    print("starting financial correctness verification...")
    
    # Setup Mock Profile
    profile = RiskProfileConfig(
        description="balanced",
        max_position_size_pct=5.0,
        daily_loss_limit_pct=3.0,
        weekly_loss_limit_pct=10.0,
        max_drawdown_pct=15.0,
        max_open_positions=10,
        max_concentration_pct=30.0,
        max_strategies_per_account=5,
        max_leverage=1.0,
        max_correlation=1.0,
        volatility_multiplier=2.0,
        regime_adjustments=RegimeAdjustments(
            volatile=0.5,
            ranging=1.0,
            trending_up=1.0,
            trending_down=1.0,
            unknown=0.5
        )
    )

    # 2.1 Position Size Check Validation
    print("\n--- 2.1 Position Size Check Validation ---")
    
    # Scenario 1: Exceeds limit
    # 0.5 BTC @ 50000 = 25000. Equity 10000. 250% > 5%
    req1 = OrderRequest(
        account_id="test", strategy_id="test", symbol="BTCUSDT",
        side="buy", quantity=0.5, price=50000.0, order_type="market"
    )
    port1 = PortfolioState(
        account_id="test", total_equity=10000.0, cash_balance=10000.0,
        positions_value=0.0, open_positions=(), daily_pnl=0.0, weekly_pnl=0.0,
        drawdown_pct=0.0, peak_equity=10000.0, regime="ranging"
    )
    res1 = check_position_size(req1, port1, profile)
    print(f"Scenario 1 (Exceed): Approved={res1.approved} (Expected False)")
    # Check rejection reason safely
    if not res1.approved and res1.rejection_reason and "exceeds" in res1.rejection_reason:
        print("   PASS")
    else:
        print(f"   FAIL: {res1}")

    # Scenario 2: Within limit
    # 0.1 BTC @ 50000 = 5000. Equity 100000. 5% == 5%
    req2 = OrderRequest(
        account_id="test", strategy_id="test", symbol="BTCUSDT",
        side="buy", quantity=0.1, price=50000.0, order_type="market"
    )
    port2 = PortfolioState(
        account_id="test", total_equity=100000.0, cash_balance=100000.0,
        positions_value=0.0, open_positions=(), daily_pnl=0.0, weekly_pnl=0.0,
        drawdown_pct=0.0, peak_equity=100000.0, regime="ranging"
    )
    res2 = check_position_size(req2, port2, profile)
    print(f"Scenario 2 (Limit): Approved={res2.approved} (Expected True)")
    if res2.approved:
        print("   PASS")
    else:
        print(f"   FAIL: {res2}")

    # 2.2 Concentration Check Validation
    print("\n--- 2.2 Concentration Check Validation ---")
    
    # Mock position: 0.4 BTC @ 50000 = 20000
    pos1 = MagicMock()
    pos1.symbol = "BTCUSDT"
    pos1.size = 0.4
    pos1.current_price = 50000.0
    
    # Scenario 1: Existing + New = 30%
    # Equity 100000. Existing 20000 (20%). New 0.2 * 50000 = 10000 (10%). Total 30%.
    req3 = OrderRequest(
        account_id="test", strategy_id="test", symbol="BTCUSDT",
        side="buy", quantity=0.2, price=50000.0, order_type="market"
    )
    port3 = PortfolioState(
        account_id="test", total_equity=100000.0, cash_balance=80000.0,
        positions_value=20000.0, open_positions=(pos1,), 
        daily_pnl=0.0, weekly_pnl=0.0, drawdown_pct=0.0, peak_equity=100000.0, regime="ranging"
    )
    res3 = check_concentration(req3, port3, profile)
    print(f"Scenario 1 (Exact 30%): Approved={res3.approved} (Expected True)")
    if res3.approved:
        print("   PASS")
    else:
        print(f"   FAIL: {res3}")

    # Scenario 2: Exceeds 30%
    # New 0.25 * 50000 = 12500 (12.5%). Total 32.5%.
    req4 = OrderRequest(
        account_id="test", strategy_id="test", symbol="BTCUSDT",
        side="buy", quantity=0.25, price=50000.0, order_type="market"
    )
    res4 = check_concentration(req4, port3, profile)
    print(f"Scenario 2 (Exceed 30%): Approved={res4.approved} (Expected False)")
    if not res4.approved and res4.rejection_reason and "Remaining capacity" in res4.rejection_reason:
        print("   PASS")
    else:
        print(f"   FAIL: {res4}")

    # 2.3 Position Sizing Calculator
    print("\n--- 2.3 Position Sizing Calculator ---")
    
    # Fixed Risk: size = (equity * risk_pct) / (entry - stop)
    # 10000 * 0.01 = 100 risk.
    # Entry 50000, Stop 49000. Diff 1000.
    # Qty = 100 / 1000 = 0.1
    
    size_res = calculate_fixed_risk_size(
        capital=10000.0,
        risk_pct=0.01,
        entry_price=50000.0,
        stop_loss_price=49000.0
    )
    print(f"Fixed Risk: Qty={size_res.quantity} (Expected 0.1)")
    if abs(size_res.quantity - 0.1) < 0.0001:
        print("   PASS")
    else:
        print("   FAIL")

    # ATR Based
    # (10000 * 0.01) / (500 * 2.0) = 100 / 1000 = 0.1
    atr_res = calculate_atr_size(
        capital=10000.0,
        risk_pct=0.01,
        entry_price=50000.0,
        stop_loss_price=49000.0,
        atr_value=500.0,
        atr_multiplier=2.0
    )
    print(f"ATR Risk: Qty={atr_res.quantity} (Expected 0.1)")
    if abs(atr_res.quantity - 0.1) < 0.0001:
        print("   PASS")
    else:
        print("   FAIL")

    # 2.4 Capital Allocation
    print("\n--- 2.4 Capital Allocation ---")
    # Equity 100000. Reserve 20% + 10% = 30000.
    # Cash 50000. Available = 50000 - 30000 = 20000.
    
    port_alloc = PortfolioState(
        account_id="test", total_equity=100000.0, cash_balance=50000.0,
        positions_value=50000.0, open_positions=(), daily_pnl=0.0, weekly_pnl=0.0,
        drawdown_pct=0.0, peak_equity=100000.0, regime="ranging"
    )
    avail = calculate_available_capital(port_alloc)
    print(f"Available Capital: {avail} (Expected 20000.0)")
    if abs(avail - 20000.0) < 0.01:
        print("   PASS")
    else:
        print("   FAIL")
        
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
