"""Comprehensive fix for test_base.py issues."""
from pathlib import Path

def fix_test_base():
    """Fix all issues in test_base.py."""
    path = Path("tests/unit/data/test_base.py")
    content = path.read_text(encoding='utf-8')
    
    # Fix 1: ID format test - expect timestamp_uuid format, not UUID4
    content = content.replace(
        '        # Should be a UUID-like format\n        parts = id1.split("-")\n        assert len(parts) == 5',
        '        # Format: YYYYMMDDHHMMSS_uuid8 (e.g., 20260208140540_6873ea17)\n        parts = id1.split("_")\n        assert len(parts) == 2  # timestamp_uuid\n        assert len(parts[0]) == 14  # YYYYMMDDHHMMSS\n        assert len(parts[1]) == 8  # First 8 chars of UUID'
    )
    
    # Fix 2: to_dict test - field name is 'name', not 'account_name'
    content = content.replace(
        '        assert result["account_name"] == "Test Account"',
        '        assert result["name"] == "Test Account"'
    )
    
    # Fix 3: Account field name in update test
    content = content.replace(
        '        account.account_name = "Updated Name"',
        '        account.name = "Updated Name"'
    )
    
    # Fix 4: Strategy needs template_id and correct enums
    content = content.replace(
        '        strategy = Strategy(\n            name="Test Strategy",\n            type="simple_ma",\n            status="inactive",',
        '        strategy = Strategy(\n            name="Test Strategy",\n            type="trend_following",\n            template_id="test_template",\n            status="draft",'
    )
    
    path.write_text(content, encoding='utf-8')
    print("Fixed test_base.py")

if __name__ == "__main__":
    fix_test_base()
