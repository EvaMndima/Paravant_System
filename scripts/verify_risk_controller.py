import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

sys.path.append(os.getcwd())

from src.core.risk.controller import RiskController
from src.core.risk.types import OrderRequest, RiskCheckResult
from src.core.config.risk_profiles import RiskProfileManager, RiskProfileConfig, RegimeAdjustments
from src.data.models.system import SystemState
from src.data.models.account import Account
from src.data.models.pnl import PnLRecord

# --- Mocks ---

@dataclass
class MockAccount:
    id: str
    equity_usdt: float
    balance_usdt: float
    profile: Any # Enum value
    regime: str = "ranging"

@dataclass
class MockPosition:
    symbol: str
    side: Any
    size: float
    current_price: float
    # Add other fields if Position model requires them
    entry_price: float = 0.0
    unrealized_pnl: float = 0.0

@dataclass
class MockPnL:
    total_pnl: float
    drawdown_pct: float = 0.0

class MockDataStore:
    def __init__(self):
        self.system_state = SystemState(
            kill_switch_active=False,
            kill_switch_reason=None,
            trading_enabled=True
        )
        self.accounts = {}
        self.positions = {} # account_id -> list[MockPosition]
        self.pnl_daily = {} # (account_id, date) -> MockPnL
        self.pnl_history = {} # account_id -> list[MockPnL]

    def get_system_state(self):
        return self.system_state
    
    def get_account(self, account_id: str):
        return self.accounts.get(account_id)
    
    def get_open_positions(self, account_id: str):
        return self.positions.get(account_id, [])
    
    def get_pnl_for_date(self, account_id, date):
        return self.pnl_daily.get((account_id, date))

    def get_pnl_history(self, account_id, start_date, end_date):
        return self.pnl_history.get(account_id, [])

class MockProfileManager:
    def __init__(self):
        self.profiles = {}
    
    def get_profile(self, name):
        return self.profiles.get(name)

# --- Test Data Setup ---

class ProfileEnum(Enum):
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"

class SideEnum(Enum):
    LONG = "long"
    SHORT = "short"

async def main():
    print("Starting Risk Controller Verification (Integration)...")
    
    # 1. Setup
    store = MockDataStore()
    profile_manager = MockProfileManager()
    
    # Setup Profile
    config = RiskProfileConfig(
        name="aggressive",
        description="Test Profile",
        max_position_size_pct=10.0,
        daily_loss_limit_pct=5.0,
        weekly_loss_limit_pct=10.0,
        max_drawdown_pct=15.0,
        max_open_positions=5,
        max_concentration_pct=20.0,
        volatility_multiplier=2.0,
        max_leverage=1.0, 
        max_correlation=1.0, 
        max_strategies_per_account=10, 
        regime_adjustments=RegimeAdjustments(
            volatile=1.0,
            ranging=1.0,
            trending_up=1.0,
            trending_down=1.0,
            unknown=1.0
        ) 
    )
    profile_manager.profiles["aggressive"] = config
    
    # Setup Account
    account_id = "test_acc"
    store.accounts[account_id] = MockAccount(
        id=account_id,
        equity_usdt=10000.0,
        balance_usdt=10000.0,
        profile=ProfileEnum.AGGRESSIVE
    )
    
    controller = RiskController(store, profile_manager)
    
    # 2. Test: Happy Path
    print("\n--- 2. Happy Path ---")
    req = OrderRequest(
        account_id=account_id,
        strategy_id="strat1",
        symbol="BTCUSDT",
        side="buy", # type: ignore
        quantity=0.02, # Reduced to $1000 (10%)
        price=50000.0,
        order_type="market" # type: ignore
    )
    
    results = controller.validate_order(req)
    # Check if last result is approved (all approved)
    all_passed = all(r.approved for r in results)
    print(f"Happy Path: Passed={all_passed}, Checks={len(results)}")
    
    if all_passed and len(results) >= 1:
        print("   [PASS] Happy Path OK")
    else:
        print(f"   [FAIL] Happy Path FAIL: {[r.rejection_reason for r in results if not r.approved]}")

    # 3. Test: Kill Switch Integration
    print("\n--- 3. Kill Switch Integration ---")
    store.system_state.kill_switch_active = True
    store.system_state.kill_switch_reason = "Integration Test"
    
    results_ks = controller.validate_order(req)
    if not results_ks[0].approved and "Kill switch is active" in (results_ks[0].rejection_reason or ""):
         print("   [PASS] Kill Switch Block OK")
    else:
         print(f"   [FAIL] Kill Switch Block FAIL: {results_ks[0]}")
         
    # Reset Kill Switch
    store.system_state.kill_switch_active = False

    # 4. Test: Daily Loss Limit
    print("\n--- 4. Daily Loss Limit ---")
    # Simulate today's PnL being -600 (6% loss, limit is 5%)
    today = datetime.now(timezone.utc).date()
    store.pnl_daily[(account_id, today)] = MockPnL(total_pnl=-600.0)
    
    results_dl = controller.validate_order(req)
    # 2nd check is daily loss
    if len(results_dl) >= 2 and not results_dl[1].approved and "Daily loss" in (results_dl[1].rejection_reason or ""):
        print("   [PASS] Daily Loss Block OK")
    else:
        print(f"   [FAIL] Daily Loss Block FAIL: {[r.check_name for r in results_dl]}")

    # Reset PnL
    store.pnl_daily[(account_id, today)] = MockPnL(total_pnl=0.0)

    # 5. Test: Max Positions
    print("\n--- 5. Max Positions ---")
    # Add 5 positions (limit is 5). Opening 6th should fail.
    store.positions[account_id] = [
        MockPosition(symbol=f"COIN{i}", side=SideEnum.LONG, size=1.0, current_price=10.0) 
        for i in range(5)
    ]
    # Update account balance to be consistent (equity = cash + positions)
    # Positions value = 5 * 1.0 * 10.0 = 50.0
    # Equity = 10000.0
    # Cash = Equity - Positions = 9950.0
    store.accounts[account_id].balance_usdt = 9950.0
    
    results_mp = controller.validate_order(req)
    # Max positions is check 5
    # Find which check failed
    failed_check = next((r for r in results_mp if not r.approved), None)
    if failed_check and "At max positions" in (failed_check.rejection_reason or ""):
        print("   [PASS] Max Positions Block OK")
    else:
        print(f"   [FAIL] Max Positions Block FAIL: {failed_check}")

    # Test Closing Trade (should pass even at max positions)
    print("   Testing Closing Trade Exception...")
    # Order for one of the existing symbols, opposite side
    close_req = OrderRequest(
        account_id=account_id,
        strategy_id="strat1",
        symbol="COIN0",
        side="sell", # Opposite to LONG
        quantity=1.0,
        price=10.0,
        order_type="market"
    )
    results_close = controller.validate_order(close_req)
    if all(r.approved for r in results_close):
        print("   [PASS] Closing Trade Allowed OK")
    else:
         print(f"   [FAIL] Closing Trade FAIL: {[r.rejection_reason for r in results_close if not r.approved]}")

    # 6. Edge Cases
    print("\n--- 6. Edge Cases ---")
    
    # 6a. Missing Account
    print("   Testing Missing Account...")
    try:
        controller.validate_order(OrderRequest(
            account_id="non_existent",
            strategy_id="strat1",
            symbol="BTCUSDT",
            side="buy", quantity=0.01, price=50000.0, order_type="market"
        ))
        print("   [FAIL] Missing Account: Did not raise ValueError")
    except ValueError as e:
        print(f"   [PASS] Missing Account: Raised ValueError as expected ({e})")
    except Exception as e:
        print(f"   [FAIL] Missing Account: Raised unexpected exception: {type(e)}")

    # 6b. Zero Equity
    print("   Testing Zero Equity...")
    store.accounts["zero_acc"] = MockAccount(
        id="zero_acc",
        equity_usdt=0.0,
        balance_usdt=0.0,
        profile=ProfileEnum.AGGRESSIVE
    )
    # Ensure profile manager has profile for this new account check logic? 
    # Profile is on account object.
    
    req_zero = OrderRequest(
        account_id="zero_acc",
        strategy_id="strat1",
        symbol="BTCUSDT",
        side="buy", quantity=0.01, price=50000.0, order_type="market"
    )
    # Expect rejection due to financial health or position size
    results_zero = controller.validate_order(req_zero)
    if not all(r.approved for r in results_zero):
         print(f"   [PASS] Zero Equity: Order Rejected ({results_zero[0].rejection_reason})")
    else:
         print("   [FAIL] Zero Equity: Order Approved (Unexpected)")

    # 6c. Missing Profile
    print("   Testing Missing Profile...")
    store.accounts["no_profile_acc"] = MockAccount(
        id="no_profile_acc",
        equity_usdt=10000.0,
        balance_usdt=10000.0,
        profile=ProfileEnum.CONSERVATIVE # "conservative" not in manager
    )
    req_no_prof = OrderRequest(
        account_id="no_profile_acc",
        strategy_id="strat1",
        symbol="BTCUSDT",
        side="buy", quantity=0.01, price=50000.0, order_type="market"
    )
    try:
        results_np = controller.validate_order(req_no_prof)
        # Check if it failed or defaulted
        # If it failed, check reason
        if not results_np[0].approved:
             print(f"   [PASS] Missing Profile: Order Rejected ({results_np[0].rejection_reason})")
        else:
             print("   [FAIL] Missing Profile: Order Approved (Unexpected)")
    except Exception as e:
         print(f"   [PASS] Missing Profile: Raised Exception ({e}) - Acceptable behavior")

    print("\nRisk Controller Integration Verification Complete")

if __name__ == "__main__":
    asyncio.run(main())
