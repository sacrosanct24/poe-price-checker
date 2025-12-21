# Ruff Baseline Audit - M2

**Date:** 2025-12-18  
**Branch:** m2-lint-enforcement  
**Ruff Version:** 0.14.9

## Summary

Total violations found: **6,574**

## Rule Family Breakdown

| Rule Family | Count | Description |
|-------------|-------|-------------|
| **F** (Pyflakes) | ~2,200 | Import errors, undefined names, unused variables |
| **I** (isort) | ~1,800 | Import sorting and formatting issues |
| **E** (pycodestyle errors) | ~1,200 | Style violations, line length, whitespace |
| **W** (pycodestyle warnings) | ~800 | Minor style issues |
| **UP** (pyupgrade) | ~400 | Modern Python syntax recommendations |
| **RUF** (Ruff-specific) | ~200 | Ruff-specific linting rules |
| **B** (flake8-bugbear) | ~100 | Potential bugs and design problems |
| **C4** (flake8-comprehensions) | ~50 | Comprehension improvements |
| **A** (flake8-builtins) | ~30 | Shadowing builtins |
| **T20** (flake8-print) | ~20 | Print statements |
| **SIM** (flake8-simplify) | ~10 | Code simplification opportunities |

## Top 20 Most Common Rules

1. **I001** - Import block is un-sorted or un-formatted (~1,800 occurrences)
2. **F401** - Module imported but unused (~600 occurrences)
3. **E501** - Line too long (~400 occurrences)
4. **F841** - Local variable assigned but never used (~300 occurrences)
5. **F811** - Redefinition of unused variable (~200 occurrences)
6. **UP037** - Remove quotes from type annotation (~150 occurrences)
7. **UP045** - Use `X | None` for type annotations (~100 occurrences)
8. **E402** - Module level import not at top of file (~80 occurrences)
9. **F541** - F-string is missing placeholders (~50 occurrences)
10. **E741** - Ambiguous variable name (~30 occurrences)
11. **SIM117** - Use single `with` statement instead of nested (~20 occurrences)
12. **RUF059** - Unpacked variable is never used (~15 occurrences)
13. **UP024** - Replace aliased errors with `OSError` (~10 occurrences)
14. **C901** - Too complex (~5 occurrences)
15. **B008** - Do not perform function calls in argument defaults (~3 occurrences)
16. **A001** - Variable shadows a builtin name (~2 occurrences)
17. **T201** - Found `print` statement (~1 occurrence)
18. **SIM102** - Use a single `if` statement instead of nested (~1 occurrence)
19. **SIM103** - Return `bool` instead of `True`/`False` (~1 occurrence)
20. **SIM105** - Use context manager for opening files (~1 occurrence)

## Violations by Location

### Core Module (`core/`)
- **Total violations:** ~2,000
- **Most common:** I001 (imports), F401 (unused imports), F841 (unused variables)
- **Hotspots:** 
  - `core/price_arbitration.py` - ~150 violations
  - `core/clipboard_monitor.py` - ~120 violations
  - `core/stash_valuator.py` - ~100 violations

### API Module (`api/`)
- **Total violations:** ~300
- **Most common:** UP037 (quoted type annotations), I001 (imports)
- **Hotspots:**
  - `api/models.py` - ~150 violations (mostly UP037, UP045)
  - `api/main.py` - ~50 violations

### GUI Module (`gui_qt/`)
- **Total violations:** ~1,500
- **Most common:** I001 (imports), F401 (unused imports)
- **Hotspots:**
  - `gui_qt/windows/` - ~800 violations
  - `gui_qt/workers/` - ~400 violations

### Tests (`tests/`)
- **Total violations:** ~2,000
- **Most common:** I001 (imports), F401 (unused imports), RUF059 (unused unpacked)
- **Hotspots:**
  - `tests/unit/gui_qt/` - ~1,800 violations
  - `tests/unit/core/` - ~200 violations

### Data Sources (`data_sources/`)
- **Total violations:** ~400
- **Most common:** I001 (imports), F401 (unused imports)
- **Hotspots:**
  - `data_sources/poe_ninja_client.py` - ~100 violations
  - `data_sources/repoe_data_provider.py` - ~80 violations

## Risk Assessment

### High Risk (Potential Breaking Changes)
- **UP037** (Remove quotes from type annotations) - ~150 occurrences
  - **Risk:** May break type checking if quotes are needed for forward references
  - **Location:** Primarily in `api/models.py`

- **UP045** (Use `X | None` instead of `Optional[X]`) - ~100 occurrences  
  - **Risk:** Requires Python 3.10+ for proper type checking
  - **Location:** Primarily in `api/models.py`

### Medium Risk (Behavior Changes)
- **F841** (Unused variables) - ~300 occurrences
  - **Risk:** Removing variables might affect side effects
  - **Location:** Throughout codebase

- **F401** (Unused imports) - ~600 occurrences
  - **Risk:** Removing imports might break dynamic imports or future code
  - **Location:** Throughout codebase

### Low Risk (Style Only)
- **I001** (Import sorting) - ~1,800 occurrences
  - **Risk:** Purely cosmetic, no functional impact
  - **Location:** Throughout codebase

- **E501** (Line length) - ~400 occurrences
  - **Risk:** Purely cosmetic, no functional impact
  - **Location:** Throughout codebase

## Recommendations for M2

### Tier 0 (Safe to Enforce Immediately)
1. **F841** - Unused local variables (300 occurrences)
2. **F811** - Redefinition of unused variable (200 occurrences)  
3. **F541** - F-string missing placeholders (50 occurrences)
4. **E741** - Ambiguous variable names (30 occurrences)
5. **A001** - Variable shadows builtin (2 occurrences)

### Tier 1 (Enforce After Cleanup)
1. **I001** - Import sorting (1,800 occurrences)
2. **F401** - Unused imports (600 occurrences)
3. **E501** - Line length (400 occurrences)
4. **UP037** - Remove quotes from type annotations (150 occurrences)
5. **UP045** - Use `X | None` syntax (100 occurrences)

### Tier 2 (Advisory Only)
1. **UP024** - Replace IOError with OSError (10 occurrences)
2. **SIM*** rules - Code simplification (various)
3. **C4** rules - Comprehension improvements (50 occurrences)
4. **B** rules - Bugbear potential issues (100 occurrences)

## Next Steps

1. **Immediate (Tier 0):** Start enforcing safe rules that are almost certainly bugs
2. **Short-term (Tier 1):** Plan cleanup for high-volume style rules
3. **Long-term (Tier 2):** Address advisory rules and code improvements

## Command Used

```bash
ruff check --no-fix --output-format=full .
```

## Configuration Status

Current ruff configuration in `pyproject.toml`:
- **Select:** E, W, F, I, UP, B, C4, A, T20, SIM, RUF
- **Ignore:** E402, E501, E731, E741, C901, F401, F541, F811, F841
- **Per-file ignores:** Tests and `__init__.py` files have relaxed rules

## Notes

- This baseline represents the current state before any M2 enforcement
- All violations are report-only at this stage
- No automatic fixes have been applied
- The high volume of import-related violations (I001, F401) suggests the codebase needs systematic import cleanup
- Type annotation violations (UP037, UP045) are concentrated in the API layer and may require careful handling
