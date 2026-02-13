import os
import re

def main():
    print("Scanning for Decision Records (DEC-)...")
    root_dir = "src"
    dec_pattern = re.compile(r"DEC-\d{4}-\d{2}-\d{2}-\d{3}")
    
    found_decisions = {}
    
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    try:
                        content = f.read()
                        matches = dec_pattern.findall(content)
                        if matches:
                            for match in matches:
                                if match not in found_decisions:
                                    found_decisions[match] = []
                                found_decisions[match].append(filepath)
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")

    print(f"\nFound {len(found_decisions)} Unique Decisions:")
    for dec in sorted(found_decisions.keys()):
        print(f"  {dec}:")
        for f in found_decisions[dec]:
             # make relative to cwd
             rel = os.path.relpath(f, os.getcwd())
             print(f"    - {rel}")

if __name__ == "__main__":
    main()
