#!/usr/bin/env python3
"""
Script to identify and fix unused imports based on CodeQL alerts.
"""
from pathlib import Path
from collections import defaultdict

# Parse the open_alerts.txt file
alerts_file = Path(__file__).parent.parent / "open_alerts.txt"

# Group unused imports by file
file_imports = defaultdict(list)

with open(alerts_file) as f:
    for line in f:
        line = line.strip()
        if not line or not line.startswith("py/unused-import|"):
            continue
        _, location = line.split("|", 1)
        filepath, line_num = location.rsplit(":", 1)
        file_imports[filepath].append(int(line_num))

# Process each file
for filepath, line_numbers in sorted(file_imports.items()):
    full_path = Path(__file__).parent.parent / filepath
    if not full_path.exists():
        print(f"SKIP (not found): {filepath}")
        continue

    print(f"\n=== {filepath} (lines: {line_numbers}) ===")

    # Read the file
    with open(full_path, encoding='utf-8') as f:
        lines = f.readlines()

    # Show the import lines
    for line_num in sorted(set(line_numbers)):
        if 0 < line_num <= len(lines):
            print(f"  L{line_num}: {lines[line_num-1].rstrip()}")

print(f"\n\nTotal files with unused imports: {len(file_imports)}")
print(f"Total unused import alerts: {sum(len(v) for v in file_imports.values())}")
