# M3.0.1 — Version Floor Update

**Date:** 2025-12-19  
**Type:** Maintenance update  
**Status:** ✅ COMPLETE

## Changes Made

Updated ruff version floors and improved pre-commit hook formatting:

### 1. Updated Version Requirements

**requirements-dev.txt:**
```diff
- ruff>=0.1.0
+ ruff>=0.6.0
```

**pyproject.toml:**
```diff
- ruff>=0.1.0
+ ruff>=0.6.0
```

### 2. Updated Pre-commit Hook

**.pre-commit-config.yaml:**
```diff
- rev: v0.1.9
+ rev: v0.8.4

- args: [--select=F401,F821,F841,F811,F541,E741,A001, --ignore=T201]
+ args:
+   - --select=F401,F821,F841,F811,F541,E741,A001
+   - --ignore=T201
```

**Benefits:**
- Better YAML formatting (multi-line args)
- Updated to more recent ruff version
- Improved readability

## Verification Results

✅ **Pre-commit hook**: Passed (initialized and ran successfully)  
✅ **Ruff version**: 0.14.9 (installed)  
✅ **Ruff Tier-0**: All checks passed!  
✅ **Unit tests**: 1128 passed in 52.83s  
✅ **check.sh**: All CI-equivalent unit tests completed successfully

## Rationale

- **Version 0.6.0+**: Ensures stable API and features
- **Pre-commit rev v0.8.4**: More recent than v0.1.9, aligns with current best practices
- **Multi-line args**: Improves readability and follows YAML conventions

## Files Changed

- `requirements-dev.txt` — Updated ruff version floor
- `pyproject.toml` — Updated ruff version floor
- `.pre-commit-config.yaml` — Updated rev and improved args formatting

No behavior changes, purely maintenance update.

---

**End of M3.0.1 Update**
