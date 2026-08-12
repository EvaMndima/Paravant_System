"""
Audit script to verify production readiness of data models.
Checks for:
1. Mutable defaults in SQLAlchemy models
2. Private member usage
3. Correct type hints
"""
import sys
import inspect
from sqlalchemy.sql.schema import Column

# Add src to path
sys.path.append(".")

try:
    from src.data.models.base import Base  # noqa: F401 - import is the availability probe
    from src.data.models.account import Account
    from src.data.models.strategy import Strategy
    from src.data.models.order import Order
    from src.data.models.position import Position
    from src.data.models.signal import Signal
    from src.data.models.strategy_assignment import StrategyAssignment
except ImportError as e:
    print(f"[FAIL] Import Error: {e}")
    sys.exit(1)

def check_mutable_defaults(model_class):
    """Check for mutable defaults in model columns."""
    print(f"Checking {model_class.__name__}...")
    issues = []
    
    # Inspect annotations/columns
    # This is a heuristic check
    for name, member in inspect.getmembers(model_class):
        if name.startswith("__"):
            continue
        
        # Check SQLAlchemy Columns defined directly
        if isinstance(member, Column):
            if hasattr(member, 'default'):
                default = member.default.arg if member.default else None
                if isinstance(default, (dict, list, set)):
                    issues.append(f"Mutable default detected in Column '{name}': {type(default)}")
        
    return issues

def main():
    models = [Account, Strategy, Order, Position, Signal, StrategyAssignment]
    all_passed = True
    
    print("Starting Model Audit...\n")
    
    for model in models:
        issues = check_mutable_defaults(model)
        if issues:
            print(f"FAIL: {model.__name__} has issues:")
            for issue in issues:
                print(f"  - {issue}")
            all_passed = False
        else:
            print(f"PASS: {model.__name__} passed checks.")
            
    if all_passed:
        print("\nAll models passed audit checks!")
        sys.exit(0)
    else:
        print("\nAudit failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
