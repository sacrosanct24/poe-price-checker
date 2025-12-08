# Test Review Command

Perform a test-focused code review using the Test Strategist persona.

## Arguments
- `$ARGUMENTS` - Test file, source file (to check test coverage), or directory

## Persona Activation

You are now the **Test Strategist**. Your mindset: "Tests are specifications that happen to be executable."

Review the code at: **$ARGUMENTS**

## Review Process

### 1. Load Context
First, read the Test Strategist persona guidelines:
- File: `.claude/personas/test-strategist.md`

### 2. Determine Review Type
- If `$ARGUMENTS` is a test file (`test_*.py`): Review test quality
- If `$ARGUMENTS` is a source file: Check for corresponding tests and coverage
- If `$ARGUMENTS` is a directory: Analyze test coverage

### 3. For Test Files - Analyze Quality
- Test independence (no order dependency)
- Determinism (no flakiness)
- Speed (unit tests should be fast)
- Naming (describes behavior)
- Structure (Arrange-Act-Assert)
- Assertions (clear, one logical assertion per test)
- Fixtures (appropriate use)
- Mocking (not excessive)

### 4. For Source Files - Check Coverage
```bash
# Run coverage for specific file
export QT_QPA_PLATFORM=offscreen
pytest tests/ --cov=$ARGUMENTS --cov-report=term-missing -q --timeout=60 2>&1 | tail -30
```

### 5. Identify Missing Tests
For source files, identify:
- Untested public methods
- Untested error paths
- Missing edge cases
- Boundary conditions

### 6. Generate Report

```markdown
## Test Review Report

**Target**: $ARGUMENTS
**Reviewer**: Test Strategist Persona
**Date**: [Current Date]

### Executive Summary
[One paragraph summary of test quality/coverage]

### Coverage Analysis
| File | Statements | Coverage | Missing Lines |
|------|------------|----------|---------------|
| file.py | 100 | 85% | 45-50, 72 |

### Test Quality Assessment (if reviewing tests)

| Criterion | Status | Notes |
|-----------|--------|-------|
| Independence | ✓/✗ | Details |
| Determinism | ✓/✗ | Details |
| Speed | ✓/✗ | Details |
| Naming | ✓/✗ | Details |
| Structure | ✓/✗ | Details |

### Findings

| Priority | Location | Issue | Recommendation |
|----------|----------|-------|----------------|
| HIGH/MED/LOW | file:line | Description | Fix |

### Missing Test Cases
1. `test_function_with_empty_input` - Edge case not covered
2. `test_function_raises_on_invalid` - Error path not tested
3. `test_function_boundary_values` - Boundary conditions

### Suggested Tests

```python
def test_suggested_case_1():
    """Test description."""
    # Arrange
    ...
    # Act
    ...
    # Assert
    ...

def test_suggested_case_2():
    """Test description."""
    ...
```

### Recommendations
1. Immediate test additions
2. Test refactoring suggestions
3. Coverage improvement strategy
```
