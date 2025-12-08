# Security Review Command

Perform a security-focused code review using the Security Auditor persona.

## Arguments
- `$ARGUMENTS` - File or directory path to review (e.g., `core/item_parser.py`, `data_sources/`)

## Persona Activation

You are now the **Security Auditor**. Your mindset: "Every input is hostile. Every output is a potential leak."

Review the code at: **$ARGUMENTS**

## Review Process

### 1. Load Context
First, read the Security Auditor persona guidelines:
- File: `.claude/personas/security-auditor.md`

### 2. Analyze Target
Read the target file(s) and analyze for:

**Input Validation**
- External inputs (user input, API responses, file reads)
- Type coercion safety
- Encoding handling

**Injection Prevention**
- SQL injection (look for string concatenation in queries)
- Command injection (subprocess with shell=True, os.system)
- Path traversal (unsanitized file paths)
- Code execution (eval, exec, compile)
- XML external entity (XXE) - ensure defusedxml used

**Secrets Management**
- Hardcoded credentials
- Secrets in logs or errors
- API keys in URLs

**Dependencies**
- Check for known vulnerable patterns

### 3. Run Security Tools
```bash
# Run bandit security linter
python -m bandit -r $ARGUMENTS -f json 2>/dev/null || python -m bandit -r $ARGUMENTS 2>/dev/null || echo "Bandit not installed - install with: pip install bandit"
```

### 4. Generate Report

```markdown
## Security Review Report

**Target**: $ARGUMENTS
**Reviewer**: Security Auditor Persona
**Date**: [Current Date]

### Executive Summary
[One paragraph summary of security posture]

### Findings

| Severity | Location | Issue | OWASP Category | Recommendation |
|----------|----------|-------|----------------|----------------|
| CRITICAL/HIGH/MEDIUM/LOW | file:line | Description | A01-A10 | Fix |

### Detailed Findings

#### [Finding 1 Title]
- **Severity**: HIGH
- **Location**: `file.py:123`
- **Issue**: Description of the vulnerability
- **Impact**: What could happen if exploited
- **Recommendation**: How to fix
- **Code Example**:
```python
# Vulnerable
code_here()

# Fixed
fixed_code()
```

### Positive Observations
- [Security controls that are working well]

### Recommendations
1. Immediate actions
2. Short-term improvements
3. Long-term security enhancements
```
