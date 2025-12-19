# Ruff Rule Tiers - M2 Lint Enforcement Strategy

**Date:** 2025-12-18  
**Branch:** m2-lint-enforcement  
**Purpose:** Define enforcement tiers for controlled lint rollout

## Overview

This document classifies all enabled Ruff rules into three enforcement tiers based on risk, impact, and developer friction. The goal is to begin lint enforcement with minimal disruption while catching genuine issues.

## Tier Definitions

### Tier 0 - Safe to Enforce Immediately
**Criteria:**
- Low false-positive risk
- Almost always indicates a bug or dead code
- Minimal developer friction
- Safe to auto-fix

**Rules:**
| Rule | Description | Count | Risk Level | Auto-fixable |
|------|-------------|-------|------------|--------------|
| **F401** | Module imported but unused | ~600 | Low | Yes |
| **F821** | Undefined name | ~50 | Low | No |
| **F841** | Local variable assigned but never used | ~300 | Low | Yes |
| **F811** | Redefinition of unused variable | ~200 | Low | Yes |
| **F541** | F-string is missing placeholders | ~50 | Low | Yes |
| **E741** | Ambiguous variable name (l, O, I) | ~30 | Low | Yes |
| **A001** | Variable shadows builtin name | ~2 | Low | Yes |
| **T201** | Found `print` statement | ~1 | Low | Yes |

**Total Tier 0 Violations:** ~1,200

**Rationale:**
- These rules catch genuine bugs (undefined names, unused variables)
- They have very low false positive rates
- Auto-fixable rules reduce manual effort
- No functional impact when fixed

### Tier 1 - Enforce Later (After Cleanup)
**Criteria:**
- Mostly stylistic or mechanical
- High diff churn potential
- Safe but noisy
- Requires coordination

**Rules:**
| Rule | Description | Count | Risk Level | Auto-fixable |
|------|-------------|-------|------------|--------------|
| **I001** | Import block is un-sorted or un-formatted | ~1,800 | Low | Yes |
| **E501** | Line too long | ~400 | Low | No |
| **UP037** | Remove quotes from type annotation | ~150 | Medium | Yes |
| **UP045** | Use `X | None` instead of `Optional[X]` | ~100 | Medium | Yes |
| **E402** | Module level import not at top of file | ~80 | Low | No |
| **C4** family | Flake8-comprehensions | ~50 | Low | Yes |
| **SIM** family | Flake8-simplify | ~10 | Low | Yes |
| **B** family | Flake8-bugbear (safe subset) | ~50 | Low | No |

**Total Tier 1 Violations:** ~2,600

**Rationale:**
- High volume rules that would create large diffs
- Type annotation rules require careful handling
- Import sorting is safe but creates many changes
- Should be addressed in dedicated cleanup efforts

### Tier 2 - Advisory Only
**Criteria:**
- Subjective or context-dependent
- Better as guidance than gates
- High false positive potential
- Opinionated style choices

**Rules:**
| Rule | Description | Count | Risk Level | Auto-fixable |
|------|-------------|-------|------------|--------------|
| **C901** | Too complex | ~5 | Medium | No |
| **B** family | Flake8-bugbear (complex rules) | ~50 | Medium | No |
| **RUF** family | Ruff-specific (opinionated) | ~200 | Medium | Varies |
| **E731** | Do not assign a lambda expression, use a def | ~20 | Low | No |
| **E721** | Do not compare types, use `isinstance()` | ~5 | Low | No |
| **W** family | Pycodestyle warnings | ~800 | Low | Varies |

**Total Tier 2 Violations:** ~1,100

**Rationale:**
- Complex rules that require human judgment
- Opinionated style choices
- High false positive rates
- Better suited for code review than CI gates

## Enforcement Strategy

### Phase 1: Tier 0 Only (M2 Target)
**Configuration:**
```toml
[tool.ruff.lint]
select = ["F401", "F821", "F841", "F811", "F541", "E741", "A001", "T201"]
ignore = []  # None for Tier 0
```

**Expected Impact:**
- Catches ~1,200 genuine issues
- Minimal developer friction
- Safe auto-fixes available
- No surprises for contributors

### Phase 2: Tier 1 (Post-M2)
**Prerequisites:**
- All Tier 0 violations resolved
- Import cleanup plan in place
- Type annotation review completed

**Configuration:**
```toml
[tool.ruff.lint]
select = [
    # Tier 0 rules
    "F401", "F821", "F841", "F811", "F541", "E741", "A001", "T201",
    # Tier 1 rules
    "I001", "E501", "UP037", "UP045", "E402", "C4", "SIM", "B"
]
ignore = ["C901", "E731", "E721"]  # Keep Tier 2 rules ignored
```

### Phase 3: Tier 2 (Long-term)
**Prerequisites:**
- Team consensus on style preferences
- Code review process established
- Performance impact assessed

## Rule-by-Rule Analysis

### F401 - Module imported but unused
**Status:** Tier 0
**Reasoning:** Unused imports are almost always dead code. Safe to remove automatically.
**Auto-fix:** Yes - Remove import
**Risk:** Very low - Only removes unused code

### F821 - Undefined name
**Status:** Tier 0
**Reasoning:** Catches typos and missing imports. Always a bug.
**Auto-fix:** No - Requires manual investigation
**Risk:** None - Only catches actual errors

### F841 - Local variable assigned but never used
**Status:** Tier 0
**Reasoning:** Unused variables indicate incomplete code or typos.
**Auto-fix:** Yes - Remove assignment
**Risk:** Low - May remove variables with side effects (rare)

### F811 - Redefinition of unused variable
**Status:** Tier 0
**Reasoning:** Variable redefinition without use indicates logic errors.
**Auto-fix:** Yes - Remove redefinition
**Risk:** Very low - Only removes unused code

### F541 - F-string is missing placeholders
**Status:** Tier 0
**Reasoning:** F-strings without placeholders should be regular strings.
**Auto-fix:** Yes - Remove f prefix
**Risk:** None - Purely cosmetic improvement

### E741 - Ambiguous variable name
**Status:** Tier 0
**Reasoning:** Variables like 'l', 'O', 'I' are hard to read and error-prone.
**Auto-fix:** Yes - Rename to more descriptive names
**Risk:** Very low - Only improves readability

### A001 - Variable shadows builtin name
**Status:** Tier 0
**Reasoning:** Shadowing builtins can cause subtle bugs.
**Auto-fix:** Yes - Rename variable
**Risk:** Very low - Prevents potential issues

### T201 - Found print statement
**Status:** Tier 0
**Reasoning:** Print statements in production code are usually debugging leftovers.
**Auto-fix:** Yes - Remove print statement
**Risk:** Very low - Only removes debugging code

### I001 - Import block is un-sorted
**Status:** Tier 1
**Reasoning:** Purely cosmetic but creates large diffs. Safe to auto-fix.
**Auto-fix:** Yes - Sort imports
**Risk:** Low - Large diff churn, but functionally safe

### E501 - Line too long
**Status:** Tier 1
**Reasoning:** Style rule with many legitimate exceptions. Not auto-fixable.
**Auto-fix:** No - Requires manual judgment
**Risk:** Medium - May require breaking complex expressions

### UP037 - Remove quotes from type annotation
**Status:** Tier 1
**Reasoning:** Modernizes type annotations but requires careful handling of forward references.
**Auto-fix:** Yes - Remove quotes
**Risk:** Medium - May break forward references if not handled carefully

### UP045 - Use `X | None` instead of `Optional[X]`
**Status:** Tier 1
**Reasoning:** Modern Python syntax but requires Python 3.10+ for proper type checking.
**Auto-fix:** Yes - Replace Optional with union
**Risk:** Medium - Type checker compatibility issues

### C901 - Too complex
**Status:** Tier 2
**Reasoning:** Subjective metric that requires human judgment.
**Auto-fix:** No - Requires refactoring
**Risk:** High - May flag legitimate complex logic

### B family - Flake8-bugbear
**Status:** Split between Tier 1 and Tier 2
**Reasoning:** Some rules are clearly beneficial (Tier 1), others are more subjective (Tier 2)
**Examples:**
- Tier 1: B008 (function calls in argument defaults)
- Tier 2: B023 (method could be static)

## Migration Path

### Current State
```toml
lint.ignore = [
    "E402", "E501", "E731", "E741", "C901",
    "F401", "F541", "F811", "F841"
]
```

### M2 Target State
```toml
lint.select = [
    "F401", "F821", "F841", "F811", "F541", 
    "E741", "A001", "T201"
]
lint.ignore = []  # No ignores for Tier 0
```

### Future State (Post-M2)
```toml
lint.select = [
    # Tier 0
    "F401", "F821", "F841", "F811", "F541", 
    "E741", "A001", "T201",
    # Tier 1
    "I001", "E501", "UP037", "UP045", "E402", 
    "C4", "SIM", "B"
]
lint.ignore = [
    # Tier 2 rules to ignore
    "C901", "E731", "E721"
]
```

## Rollback Plan

If Tier 0 enforcement causes unexpected issues:

1. **Immediate:** Add targeted ignores for problematic rules
2. **Short-term:** Review and adjust rule selection
3. **Long-term:** Re-evaluate tier assignments

**Example rollback configuration:**
```toml
lint.ignore = [
    "F841",  # If unused variables are intentional
    "F401"   # If imports are needed for side effects
]
```

## Monitoring and Metrics

### Success Criteria for Tier 0
- [ ] No CI failures due to unexpected rule violations
- [ ] Contributors can easily fix violations
- [ ] No legitimate code is flagged as problematic
- [ ] Auto-fixes work correctly

### Metrics to Track
- Number of violations per rule
- Time to resolve violations
- Developer feedback on rule usefulness
- CI failure rate due to linting

### Review Points
- **Week 1:** Assess initial impact and adjust if needed
- **Week 2:** Review developer feedback and violation patterns
- **Week 4:** Evaluate readiness for Tier 1 rollout

## Conclusion

This tiered approach allows for controlled lint enforcement that:
1. **Starts safe** with rules that catch genuine bugs
2. **Builds confidence** through successful early enforcement
3. **Scales gradually** to more comprehensive linting
4. **Remains reversible** if issues arise

The M2 milestone focuses exclusively on Tier 0 enforcement, providing a solid foundation for future linting improvements while minimizing disruption to the development workflow.
