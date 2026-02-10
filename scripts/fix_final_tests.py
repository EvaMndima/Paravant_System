"""Final comprehensive fix for all remaining test files."""
from pathlib import Path
import re

def fix_all_remaining_tests():
    """Apply all known fixes to remaining test files."""
    
    fixes_applied = {}
    
    # Files that still need enum/field fixes
    test_files = [
        "tests/unit/data/test_models_order.py",
        "tests/unit/data/test_models_position.py",
        "tests/unit/data/test_models_signal_assignment.py",
    ]
    
    for filepath in test_files:
        path = Path(filepath)
        if not path.exists():
            print(f"Skipping {filepath} - not found")
            continue
            
        content = path.read_text(encoding='utf-8')
        original = content
        changes = []
        
        # Fix: Strategy needs template_id
        if 'template_id' not in content:
            # Already has template_id from previous fix
            pass
        
        # Fix: Enum values that are still wrong after template_id fix
        # Note: We already fixed "simple_ma" to "trend_following" in earlier script
        # Now we need to verify "inactive" → "draft" for status
        if 'status="inactive"' in content:
            content = content.replace('status="inactive"', 'status="draft"')
            changes.append("status inactive→draft")
        
        if 'status=\"inactive\"' in content: 
            content = content.replace('status=\"inactive\"', 'status=\"draft\"')
            changes.append("status inactive→draft (escaped)")
        
        if content != original:
            path.write_text(content, encoding='utf-8')
            fixes_applied[filepath] = changes
            print(f"Fixed {filepath}: {', '.join(changes)}")
        else:
            print(f"No changes needed for {filepath}")
    
    return fixes_applied

if __name__ == "__main__":
    results = fix_all_remaining_tests()
    print(f"\nTotal files fixed: {len(results)}")
    for file, changes in results.items():
        print(f"  {file}: {changes}")
