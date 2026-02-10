"""Fix all remaining 'inactive' status references in test files."""
from pathlib import Path

files_to_fix = [
    "tests/unit/data/test_models_strategy.py",
    "tests/unit/data/test_models_signal_assignment.py",
    "tests/unit/data/test_models_position.py",
]

for filepath in files_to_fix:
    path = Path(filepath)
    content = path.read_text(encoding='utf-8')
    content = content.replace('status="inactive"', 'status="draft"')
    path.write_text(content, encoding='utf-8')
    print(f"Fixed {filepath}")

print("All files fixed!")
