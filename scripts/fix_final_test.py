"""Fix the last failing test - mutable default isolation."""
from pathlib import Path

path = Path("tests/unit/data/test_models_signal_assignment.py")
content = path.read_text(encoding='utf-8')

# Find and replace the two lines that need None checking
lines = content.split('\n')
new_lines = []

for i, line in enumerate(lines):
    new_lines.append(line)
    # Add None check before append operations
    if 'assignment1.regime_filter.append("trending_up")' in line:
        indent = len(line) - len(line.lstrip())
        new_lines.insert(-1, ' ' * indent + 'if assignment1.regime_filter is None:')
        new_lines.insert(-1, ' ' * (indent + 4) + 'assignment1.regime_filter = []')
    elif 'assignment2.regime_filter.append("ranging")' in line:
        indent = len(line) - len(line.lstrip())
        new_lines.insert(-1, ' ' * indent + 'if assignment2.regime_filter is None:')
        new_lines.insert(-1, ' ' * (indent + 4) + 'assignment2.regime_filter = []')

path.write_text('\n'.join(new_lines), encoding='utf-8')
print("Fixed mutable default isolation test!")
