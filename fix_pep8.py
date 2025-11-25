"""
Script to fix remaining PEP 8 violations.
"""
import re
from pathlib import Path

def remove_unused_import(filepath, import_line):
    """Remove unused import from a file."""
    content = Path(filepath).read_text(encoding='utf-8')
    # Remove the line
    lines = content.split('\n')
    new_lines = [line for line in lines if import_line not in line]
    Path(filepath).write_text('\n'.join(new_lines), encoding='utf-8')
    print(f"  Removed '{import_line}' from {filepath}")

def fix_f_strings(filepath):
    """Convert f-strings without placeholders to regular strings."""
    content = Path(filepath).read_text(encoding='utf-8')
    # Find f-strings without {} placeholders
    # Pattern: f"..." or f'...' without {}
    pattern = r'f(["\'])((?:(?!\1).)*?)\1'
    
    def replacer(match):
        quote = match.group(1)
        text = match.group(2)
        # Check if it has placeholders
        if '{' not in text:
            return f'{quote}{text}{quote}'  # Remove f prefix
        return match.group(0)  # Keep as is
    
    new_content = re.sub(pattern, replacer, content)
    Path(filepath).write_text(new_content, encoding='utf-8')
    print(f"  Fixed f-strings in {filepath}")

def fix_regex_escapes(filepath):
    """Fix invalid escape sequences in regex patterns."""
    content = Path(filepath).read_text(encoding='utf-8')
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Line 219 has: r"\+\d+\s"
        if 'r"\\+\\d+\\s' in line or '"\\+\\d+\\s' in line:
            # Already a raw string or needs to be
            if not line.strip().startswith('r"') and '\\+' in line:
                lines[i] = line.replace('"\\+', 'r"\\+')
                print(f"  Fixed escape sequence on line {i+1}")
    
    Path(filepath).write_text('\n'.join(lines), encoding='utf-8')

def strip_whitespace_from_blank_lines(filepath):
    """Remove trailing whitespace from blank lines."""
    content = Path(filepath).read_text(encoding='utf-8')
    lines = content.split('\n')
    
    new_lines = []
    for line in lines:
        if line.strip() == '':  # Blank line
            new_lines.append('')  # No whitespace
        else:
            new_lines.append(line)
    
    Path(filepath).write_text('\n'.join(lines), encoding='utf-8')
    print(f"  Stripped whitespace from {filepath}")

# Main fixes
print("Fixing PEP 8 violations...")

# 1. Remove unused imports
print("\n1. Removing unused imports...")
# remove_unused_import('core/build_matcher.py', 'import re')  # Commented - might be used
remove_unused_import('core/derived_sources.py', 'from typing import Iterable')
remove_unused_import('core/poe_oauth.py', 'from typing import Dict')
remove_unused_import('core/item_parser.py', 'from core.game_version import GameVersion')

# 2. Fix f-strings
print("\n2. Fixing f-strings without placeholders...")
fix_f_strings('core/price_service.py')
fix_f_strings('core/rare_item_evaluator.py')

# 3. Fix regex escapes
print("\n3. Fixing regex escape sequences...")
fix_regex_escapes('core/value_rules.py')

# 4. Strip remaining whitespace
print("\n4. Stripping whitespace from blank lines...")
for file in ['core/build_matcher.py', 'core/poe_oauth.py', 'core/rare_item_evaluator.py', 'core/stash_scanner.py']:
    strip_whitespace_from_blank_lines(file)

print("\n✓ All fixes applied!")
print("\nRun: python -m flake8 core/ --count --statistics --max-line-length=100")
