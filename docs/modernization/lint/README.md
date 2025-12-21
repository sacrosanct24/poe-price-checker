# Lint Enforcement - Ruff

This document describes the lint enforcement strategy for the Poe Price Checker project using Ruff.

## Overview

We use [Ruff](https://docs.astral.sh/ruff/) as our canonical linter to maintain code quality, consistency, and catch potential issues early in the development process.

**As of M3**: Flake8 has been completely retired. Ruff is now the only linting tool in use.

## Current Status (M3)

**Milestone M3** completed the transition to Ruff-only by:

1. **Removing** flake8 and all plugins from CI and dev dependencies
2. **Standardizing** on Ruff Tier-0 enforcement exclusively
3. **Simplifying** the development workflow (single linter)
4. **Maintaining** the same Tier-0 rule set (no behavior changes)

See [M3_flake8_inventory.md](./M3_flake8_inventory.md) for details on the flake8 removal.

## Previous Milestones

**Milestone M2** established a controlled lint enforcement posture by:

1. **Measuring** the current lint surface area
2. **Classifying** violations by risk and cost
3. **Enforcing** a small, safe subset first
4. **Deferring** noisy or stylistic rules
5. **Ensuring** CI gating never surprises contributors

## Enforcement Tiers

### Tier 0 - Safe to Enforce Immediately
These rules are enforced in CI and catch genuine bugs with minimal developer friction:

| Rule | Description | Example |
|------|-------------|---------|
| **F401** | Module imported but unused | `import os  # unused` |
| **F821** | Undefined name | `print(undefined_var)` |
| **F841** | Local variable assigned but never used | `x = 5  # never used` |
| **F811** | Redefinition of unused variable | `def foo(): pass; def foo(): pass` |
| **F541** | F-string is missing placeholders | `f"Hello world"` |
| **E741** | Ambiguous variable name | `l = 1  # lowercase L` |
| **A001** | Variable shadows builtin name | `id = 5  # shadows builtin id` |

### Tier 1 - Enforce Later (After Cleanup)
These rules are mostly stylistic and will be enforced after systematic cleanup:

| Rule | Description | Status |
|------|-------------|--------|
| **I001** | Import block is un-sorted | Planned |
| **E501** | Line too long | Planned |
| **UP037** | Remove quotes from type annotation | Planned |
| **UP045** | Use `X \| None` instead of `Optional[X]` | Planned |

### Tier 2 - Advisory Only
These rules are better suited for code review than CI gates:

| Rule | Description | Status |
|------|-------------|--------|
| **C901** | Too complex | Advisory |
| **B** family | Flake8-bugbear (complex rules) | Advisory |
| **RUF** family | Ruff-specific (opinionated) | Advisory |

## Configuration

The Ruff configuration is located in `pyproject.toml` under the `[tool.ruff]` section.

### Current M2 Configuration

```toml
[tool.ruff]
line-length = 127
target-version = "py311"
lint.select = [
    "F401",  # module imported but unused
    "F821",  # undefined name
    "F841",  # local variable assigned but never used
    "F811",  # redefinition of unused variable
    "F541",  # f-string is missing placeholders
    "E741",  # ambiguous variable name
    "A001",  # variable shadows builtin name
    "T201",  # found print statement
]
lint.ignore = ["T201"]  # Ignore print statements for now
```

## Running Ruff

### Check Only (No Fixes)
```bash
ruff check .
```

### Check with Auto-fixes
```bash
ruff check --fix .
```

### Check Specific Files
```bash
ruff check path/to/file.py
```

### Check Only Tier 0 Rules
```bash
ruff check --select=F401,F821,F841,F811,F541,E741,A001 .
```

## CI Integration

Ruff is enforced as a required CI step. The CI configuration:

- Only enforces Tier 0 rules
- Provides clear, fast failure output
- Points directly to ruff output (no wrapper ambiguity)

## Developer Experience

### Local Development

1. **Install Ruff**: `pip install ruff`
2. **Check before commit**: `ruff check .`
3. **Auto-fix issues**: `ruff check --fix .`
4. **IDE Integration**: Most editors have Ruff plugins available

### VS Code Integration

Install the "Ruff" extension for real-time linting:

1. Open Extensions (`Ctrl+Shift+X`)
2. Search for "Ruff"
3. Install and reload

### Pre-commit Hook

We use pre-commit hooks to automatically run Ruff before each commit:

```bash
pip install pre-commit
pre-commit install
```

## Rule Justification

### Why These Rules?

**Tier 0 rules were chosen because they:**

- ✅ Have very low false positive rates
- ✅ Catch genuine bugs (undefined variables, unused imports)
- ✅ Are safe to auto-fix
- ✅ Have minimal developer friction
- ✅ Don't require subjective judgment calls

**Examples of what they catch:**

```python
# F821 - Undefined name
def calculate_total():
    return item_count * price  # NameError if variables not defined

# F401 - Unused import
import os  # Never used - can be removed safely

# F841 - Unused variable
def process_data():
    temp = get_data()  # Variable assigned but never used
    return clean_data()

# F541 - F-string without placeholders
name = "World"
message = f"Hello"  # Should be "Hello" (regular string)

# E741 - Ambiguous variable name
l = 1  # Could be confused with 1 or I
```

### Why Not Other Rules?

**Rules deferred to Tier 1:**

- **I001 (Import sorting)**: Creates large diffs, requires coordination
- **E501 (Line length)**: Many legitimate exceptions, not auto-fixable
- **UP037/UP045 (Type annotations)**: Requires careful handling of forward references

**Rules in Tier 2:**

- **C901 (Complexity)**: Subjective, requires human judgment
- **B family (Bugbear)**: Some rules are opinionated or context-dependent

## Migration Path

### From Current State to M2
1. ✅ Baseline audit completed (6,574 violations found)
2. ✅ Rule classification completed
3. ✅ Tier 0 enforcement configured (364 violations)
4. 🔄 CI integration in progress

### Future Phases

**Phase 2 (Post-M2):**
- Address Tier 1 violations systematically
- Import sorting cleanup
- Line length standardization
- Type annotation modernization

**Phase 3 (Long-term):**
- Evaluate Tier 2 rules for selective enforcement
- Establish team consensus on style preferences
- Integrate with code review process

## Monitoring and Metrics

### Success Criteria for M2
- [ ] No CI failures due to unexpected rule violations
- [ ] Contributors can easily fix violations
- [ ] No legitimate code is flagged as problematic
- [ ] Auto-fixes work correctly

### Metrics Tracked
- Number of violations per rule
- Time to resolve violations
- Developer feedback on rule usefulness
- CI failure rate due to linting

### Review Points
- **Week 1:** Assess initial impact and adjust if needed
- **Week 2:** Review developer feedback and violation patterns
- **Week 4:** Evaluate readiness for Tier 1 rollout

## Rollback Plan

If enforcement causes unexpected issues:

1. **Immediate**: Add targeted ignores for problematic rules
2. **Short-term**: Review and adjust rule selection
3. **Long-term**: Re-evaluate tier assignments

**Example rollback configuration:**
```toml
lint.ignore = [
    "F841",  # If unused variables are intentional
    "F401"   # If imports are needed for side effects
]
```

## Contributing

### Adding New Rules

1. **Assess risk**: Is it safe to auto-fix? Low false positive rate?
2. **Classify tier**: Tier 0 (safe), Tier 1 (stylistic), or Tier 2 (advisory)?
3. **Test impact**: Run on the codebase and assess violation count
4. **Update documentation**: Add to appropriate tier in this README
5. **Update configuration**: Add to `pyproject.toml`
6. **Communicate changes**: Notify team of new enforcement

### Requesting Rule Changes

If you believe a rule should be moved between tiers or modified:

1. Open an issue with specific examples
2. Explain the impact (false positives, developer friction, etc.)
3. Suggest an alternative approach if applicable
4. Tag the team for discussion

## Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Rule Reference](https://docs.astral.sh/ruff/rules/)
- [Configuration Guide](https://docs.astral.sh/ruff/configuration/)
- [M2 Baseline Audit](./M2_ruff_baseline.md)
- [M2 Rule Tiers](./M2_rule_tiers.md)

## Questions?

- For rule-specific questions: Check the [Ruff documentation](https://docs.astral.sh/ruff/rules/)
- For configuration issues: Open an issue in the repository
- For general discussion: Start a discussion in Discussions
