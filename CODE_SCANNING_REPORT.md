# Code Scanning Alerts Report

Generated: 2025-11-30

## Summary: 333 Open Alerts

| Rule | Count | Severity | Description |
|------|-------|----------|-------------|
| `py/unused-import` | 145 | Note | Unused import statements |
| `B105` | 36 | Note | Hardcoded password string (mostly test files) |
| `py/empty-except` | 29 | Note | Empty except blocks |
| `py/unused-local-variable` | 45 | Note | Unused local variables |
| `B314` | 8 | Warning | XML parsing without defusedxml |
| `B405` | 6 | Note | Import of xml.etree.ElementTree |
| `B110` | 10 | Note | Try-except-pass pattern |
| `py/ineffectual-statement` | 8 | Note | Statement with no effect |
| `py/import-and-import-from` | 11 | Note | Module imported with import and from |
| `py/import-of-mutable-attribute` | 5 | Warning | Import of mutable module attribute |
| `B113` | 5 | Warning | Request without timeout |
| `B603` | 4 | Note | subprocess without shell=True |
| `B606` | 2 | Note | Start process without shell |
| `B607` | 1 | Note | Start process with partial path |
| `B608` | 1 | Warning | SQL injection possible |
| `py/unused-global-variable` | 5 | Note | Unused global variables |
| `B311` | 2 | Note | Use of random for crypto |
| `B404` | 2 | Note | Import of subprocess |
| `B106` | 2 | Note | Hardcoded password in function arg |
| `B108` | 1 | Warning | Hardcoded temp file |
| `py/repeated-import` | 2 | Note | Same module imported twice |
| `py/unnecessary-lambda` | 1 | Note | Lambda that just calls function |
| `py/commented-out-code` | 1 | Note | Commented out code |

---

## Alerts by Category

### 1. Unused Imports (145 alerts)
Most common issue. These are safe to fix by removing the unused imports.

**Top files:**
- `tests/` directory: ~80 alerts (test files often have extra imports)
- `gui_qt/`: ~25 alerts
- `core/`: ~15 alerts

### 2. Empty Except Blocks (29 alerts) - `py/empty-except` + `B110`
Files with empty `except: pass` patterns:
- `api/routers/stats.py`: 6 alerts
- `gui/main_window.py`: 5 alerts
- `core/item_parser.py`: 5 alerts
- `core/guide_gear_extractor.py`: 2 alerts
- `gui_qt/styles.py`: 1 alert

### 3. Hardcoded Passwords - B105/B106 (38 alerts)
Almost all in `tests/unit/core/test_poe_oauth.py` - these are test tokens/passwords which is expected.

### 4. XML Parsing Security - B314/B405 (14 alerts)
Using `xml.etree.ElementTree` instead of `defusedxml`:
- `core/pob_integration.py`
- `core/guide_gear_extractor.py`
- `core/build_comparison.py`
- `core/build_matcher.py`
- `gui_qt/dialogs/loadout_selector_dialog.py`
- `tests/test_loadout_selector.py`

### 5. Requests Without Timeout - B113 (5 alerts)
HTTP requests without timeout parameter:
- `core/stash_scanner.py`: 3 alerts
- `core/poe_oauth.py`: 2 alerts

### 6. SQL Injection - B608 (1 alert)
- `core/database.py:1110` - Needs review

### 7. Subprocess/Shell Issues - B603/B606/B607/B404 (9 alerts)
- `gui/main_window.py`: Already has `# nosec` comments
- `core/secure_storage.py`: File permission commands
- `build.py`: PyInstaller build script

### 8. Unused Local Variables (45 alerts)
Variables assigned but never used. Common in:
- Test files (often setup variables)
- GUI files (often unused widget references)

---

## Priority Fixes

### High Priority (Security)
1. **B608 SQL Injection** - `core/database.py:1110`
2. **B113 Request Timeout** - Add timeout to HTTP requests
3. **B314 XML Parsing** - Consider using defusedxml for untrusted XML

### Medium Priority (Code Quality)
1. **Empty except blocks** - Add proper exception handling or logging
2. **Unused imports** - Remove to reduce noise
3. **Import of mutable attribute** - Use proper import patterns

### Low Priority (Informational)
1. **B105 in tests** - Test passwords are expected, add `# nosec` if needed
2. **Subprocess alerts** - Already secured with `# nosec` comments
3. **Commented-out code** - Review and remove if not needed

---

## Files with Most Alerts

| File | Alerts | Main Issues |
|------|--------|-------------|
| `tests/unit/core/test_poe_oauth.py` | 38 | B105 (test passwords) |
| `tests/` (various) | 80+ | Unused imports |
| `api/routers/stats.py` | 8 | Empty except, unused vars |
| `gui/main_window.py` | 10 | Empty except, unused imports |
| `core/item_parser.py` | 5 | Empty except |

---

## Quick Fix Commands

```bash
# Find all unused imports in a file
python -c "import ast; print([n.name for n in ast.walk(ast.parse(open('FILE').read())) if isinstance(n, ast.alias)])"

# Add nosec to test file hardcoded passwords
# (These are expected in test files)
```

---

## Recommended Action Plan

1. **First pass**: Fix unused imports (145 alerts) - Mechanical, low risk
2. **Second pass**: Add timeouts to HTTP requests (5 alerts) - Security fix
3. **Third pass**: Review and fix empty except blocks (29 alerts) - Improve error handling
4. **Fourth pass**: Review SQL injection concern (1 alert) - Security fix
5. **Fifth pass**: Consider defusedxml for XML parsing (14 alerts) - Security improvement
6. **Ongoing**: Add `# nosec` to false positives in test files
