"""
Comprehensive fix for ALL remaining test issues.

Fixes:
1. RiskProfile.MODERATE → RiskProfile.BALANCED
2. Add missing template_id to Strategy instantiation
3. Add missing symbol to StrategyAssignment
4. Fix risk_config defaults
5. Fix status enum references
"""
import re
from pathlib import Path

def comprehensive_test_fix(file_path: Path) -> bool:
    """Apply all necessary fixes to test files."""
    content = file_path.read_text(encoding="utf-8")
    original = content
    
    # Fix RiskProfile enum (MODERATE → BALANCED)
    content = content.replace("RiskProfile.MODERATE", "RiskProfile.BALANCED")
    content = content.replace("risk_profile=", "profile=")
    
    # Fix StrategyAssignment status strings
    content = re.sub(
        r'StrategyAssignment\([^)]*status="active"',
        lambda m: m.group(0).replace('status="active"', 'status=AssignmentStatus.ACTIVE'),
        content
    )
    
    # Add template_id to any Strategy() calls that don't have it
    # Match Strategy(...) and add template_id if needed
    def add_template_id(match):
        strategy_call = match.group(0)
        if 'template_id=' not in strategy_call:
            # Insert template_id after type parameter
            strategy_call = re.sub(
                r'(type=\w+(?:\.\w+)?),',
                r'\1,\n            template_id="test_template",',
                strategy_call
            )
        return strategy_call
    
    content = re.sub(
        r'Strategy\([^)]*\)',
        add_template_id,
        content,
        flags=re.DOTALL
    )
    
    # Add symbol to StrategyAssignment calls that don't have it
    def add_symbol(match):
        assignment_call = match.group(0)
        if 'symbol=' not in assignment_call:
            # Insert symbol after strategy_id
            assignment_call = re.sub(
                r'(strategy_id=\w+(?:\.\w+)?),',
                r'\1,\n            symbol="BTCUSDT",',
                assignment_call
            )
        return assignment_call
    
    content = re.sub(
        r'StrategyAssignment\([^)]*\)',
        add_symbol,
        content,
        flags=re.DOTALL
    )
    
    # Ensure AssignmentStatus import where StrategyAssignment is used
    if 'StrategyAssignment' in content and 'AssignmentStatus' not in content:
        content = re.sub(
            r'from src\.data\.models import ([^\n]+)',
            lambda m: m.group(0) if 'AssignmentStatus' in m.group(0) else m.group(0).rstrip() + ', AssignmentStatus',
            content,
            count=1
        )
    
    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False

def main():
    """Fix all test files."""
    test_dir = Path("d:/Eva/Projects/Paravant_System/tests")
    
    test_files = list(test_dir.rglob("*.py"))
    
    fixed_count = 0
    for test_file in test_files:
        try:
            if comprehensive_test_fix(test_file):
                print(f"Fixed: {test_file.relative_to(test_dir)}")
                fixed_count += 1
        except Exception as e:
            print(f"Error fixing {test_file}: {e}")
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()
