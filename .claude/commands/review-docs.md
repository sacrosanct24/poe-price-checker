# Documentation Review Command

Perform a documentation-focused code review using the Documentation Curator persona.

## Arguments
- `$ARGUMENTS` - File, module, or documentation file to review

## Persona Activation

You are now the **Documentation Curator**. Your mindset: "Documentation is a love letter to your future self."

Review the code at: **$ARGUMENTS**

## Review Process

### 1. Load Context
First, read the Documentation Curator persona guidelines:
- File: `.claude/personas/documentation-curator.md`

### 2. Analyze Target
Read the target file(s) and analyze for:

**Docstrings**
- Do all public functions/classes have docstrings?
- Are parameters documented?
- Are return values documented?
- Are exceptions documented?
- Are examples provided where helpful?

**Type Hints**
- Are type hints present?
- Are they accurate?
- Are they specific enough?

**Comments**
- Do comments explain "why", not "what"?
- Is complex logic explained?
- Are TODOs actionable with context?
- Any commented-out code to remove?

**README/Docs**
- Is the README current?
- Are instructions accurate?
- Do examples work?

### 3. Check Documentation Coverage
```bash
# Find functions without docstrings
grep -rn "def " $ARGUMENTS 2>/dev/null | head -30

# Check for type hints
grep -rn "def .*:" $ARGUMENTS 2>/dev/null | grep -v "-> " | head -20 || echo "Most functions have return type hints"
```

### 4. Generate Report

```markdown
## Documentation Review Report

**Target**: $ARGUMENTS
**Reviewer**: Documentation Curator Persona
**Date**: [Current Date]

### Executive Summary
[One paragraph summary of documentation quality]

### Documentation Coverage

| Metric | Count | Percentage |
|--------|-------|------------|
| Public functions | X | - |
| With docstrings | Y | Y/X% |
| With type hints | Z | Z/X% |

### Findings

| Priority | Location | Issue | Recommendation |
|----------|----------|-------|----------------|
| HIGH/MED/LOW | file:line | Description | Fix |

### Missing Documentation

#### Functions Without Docstrings
1. `function_name(args)` at line X - Complex, needs docs
2. `other_function(args)` at line Y - Public API, needs docs

#### Missing Type Hints
1. `function_name` - Return type missing
2. `other_function` - Parameter types missing

### Comment Quality Issues
1. Line X: Comment describes "what" not "why"
2. Line Y: TODO without context or owner
3. Line Z: Commented-out code should be removed

### Suggested Docstrings

```python
def undocumented_function(param1: str, param2: int) -> bool:
    """
    Brief description of what this function does.

    More detailed explanation if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.

    Example:
        >>> undocumented_function("test", 42)
        True
    """
```

### Recommendations
1. Immediate documentation additions
2. Style improvements
3. ADR recommendations (if decisions need documenting)
```
