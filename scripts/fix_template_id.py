"""Quick fix to add template_id to all Strategy instantiations in test files."""
from pathlib import Path
import re

def fix_strategy_instantiations() -> None:
    """Add template_id to all Strategy() calls missing it."""
    test_files = [
        "tests/unit/data/test_models_signal_assignment.py",
        "tests/unit/data/test_models_position.py",
        "tests/unit/data/test_models_order.py",
    ]
    
    for filepath in test_files:
        path = Path(filepath)
        if not path.exists():
            print(f"Skipping {filepath} - not found")
            continue
            
        content = path.read_text(encoding='utf-8')
        original = content
        
        # Fix "simple_ma" to "trend_following" (valid enum value)
        content = content.replace('type="simple_ma"', 'type="trend_following"')
        
        # Pattern: Strategy(name=..., type="...", status="...")
        # We need to add template_id after type
        pattern = r'Strategy\(name="([^"]+)",\s*type="([^"]+)",\s*status="([^"]+)"\)'
        replacement = r'Strategy(name="\1", type="\2", template_id="test_template", status="\3")'
        
        content = re.sub(pattern, replacement, content)
        
        if content != original:
            path.write_text(content, encoding='utf-8')
            print(f"Fixed {filepath}")
        else:
            print(f"No changes needed for {filepath}")

if __name__ == "__main__":
    fix_strategy_instantiations()
    print("Done!")
