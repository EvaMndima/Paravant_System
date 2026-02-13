import asyncio
import sys
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

sys.path.append(os.getcwd())

from src.core.risk.kill_switch import KillSwitch
from src.data.models.system import SystemState

# Mocking Models and DataStore to avoid DB dependency for this logic test
class MockDataStore:
    def __init__(self):
        # Use real SystemState model with explicit defaults for python-side logic
        self._state = SystemState(
            kill_switch_active=False,
            kill_switch_reason=None,
            trading_enabled=True
        )
        self.logs = []

    def get_system_state(self):
        return self._state

    def update_system_state(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self._state, k):
                setattr(self._state, k, v)
        return self._state

    def add_audit_log(self, action, actor, details=None):
        self.logs.append({"action": action, "actor": actor, "details": details})

async def main():
    print("Starting Kill Switch Verification...")
    
    # 0. Setup: Mock Store
    mock_store = MockDataStore()
    ks = KillSwitch(store=mock_store) # type: ignore
    
    # 4.1 Activation Test
    print("\n--- 4.1 Activation Test ---")
    print(f"Initial State: Active={ks.is_active()}")
    if not ks.is_active():
        print("   Initial State OK")
    else:
        print("   Initial State FAIL")
        
    activation_reason = "Test Activation"
    ks.activate(reason=activation_reason)
    
    print(f"Post-Activation: Active={ks.is_active()}")
    if ks.is_active():
         print("   Activation OK")
    else:
         print("   Activation FAIL")
        
    status = ks.get_status()
    print(f"Reason match: {status['reason'] == activation_reason}")
    if status['reason'] == activation_reason:
         print("   Reason Storage OK")
    else:
         print(f"   Reason Mismatch: {status['reason']}")

    # 4.2 Persistence Test
    print("\n--- 4.2 Persistence Test ---")
    # In real app, DataStore persists to DB. Here MockStore holds state.
    # We verify KillSwitch reads from store.
    ks2 = KillSwitch(store=mock_store) # type: ignore
    print(f"Reloaded State: Active={ks2.is_active()}")
    status2 = ks2.get_status()
    if ks2.is_active() and status2['reason'] == activation_reason:
        print("   Persistence OK")
    else:
        print(f"   Persistence FAIL: {status2}")

    # 4.3 Order Blocking Test
    print("\n--- 4.3 Order Blocking Test ---")
    from src.core.risk.checks import check_kill_switch
    
    # Pass SystemState from store, not KillSwitch instance
    state = mock_store.get_system_state()
    res = check_kill_switch(state)
    print(f"Check Result: Approved={res.approved}")
    if not res.approved and "Kill switch is active" in res.rejection_reason: # type: ignore
        print("   Blocking OK")
    else:
        print(f"   Blocking FAIL: {res}")

    # 4.4 Deactivation Test
    print("\n--- 4.4 Deactivation Test ---")
    
    # Mock generation of code to get one to use
    code = ks2.generate_deactivation_code()
    print(f"Generated Code: {code}")

    # Wrong code
    result_wrong = ks2.deactivate(confirmation_code="WRONG_CODE")
    print(f"Wrong Code Deactivation: Success={result_wrong}")
    if not result_wrong and ks2.is_active():
        print("   Protection OK")
    else:
        print("   Protection FAIL")
        
    # Correct code
    result_right = ks2.deactivate(confirmation_code=code)
    print(f"Correct Code Deactivation: Success={result_right}")
    
    if result_right and not ks2.is_active():
        print("   Deactivation OK")
    else:
        print("   Deactivation FAIL")

    print("\nKill Switch Verification Complete")

if __name__ == "__main__":
    asyncio.run(main())
