"""
Enhanced script to fix ALL field name mismatches in test files.

Model field mappings:
- Account: account_name → name, risk_profile → profile, account_status → status
- Strategy: strategy_type → type, strategy_status → status
"""
import re
from pathlib import Path

def fix_all_field_names(file_path: Path) -> bool:
    """Fix all field name mismatches in a test file."""
    content = file_path.read_text(encoding="utf-8")
    original = content
    
    # Account model fixes
    content = content.replace("account_name=", "name=")
    content = content.replace("risk_profile=", "profile=")
    
    # Fix account_status → status (only in Account() calls)
    content = re.sub(
        r'Account\([^)]*\baccount_status\s*=',
        lambda m: m.group(0).replace('account_status', 'status'),
        content
    )
    
    # Strategy model fixes
    content = content.replace("strategy_type=", "type=")
    content = content.replace("strategy_status=", "status=")
    
    # Fix enum references
    content = content.replace("StrategyStatus.ACTIVE", "StrategyStatus.DRAFT")
    content = content.replace("StrategyStatus.INACTIVE", "StrategyStatus.RETIRED")
    
    # Fix to_dict assertions - Account model uses 'name' not 'account_name'
    content = re.sub(r'assert\s+data\["account_name"\]', 'assert data["name"]', content)
    content = re.sub(r'data\["account_name"\]', 'data["name"]', content)
    
    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False

def main():
    """Fix all test files."""
    test_dir = Path("d:/Eva/Projects/Paravant_System/tests")
    
    # Find all Python files
    test_files = list(test_dir.rglob("*.py"))
    
    fixed_count = 0
    for test_file in test_files:
        if fix_all_field_names(test_file):
            print(f"Fixed: {test_file.relative_to(test_dir)}")
            fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()
