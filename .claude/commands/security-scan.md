# Security Scan Command

Run comprehensive security scanning tools on the codebase.

## Arguments
- `$ARGUMENTS` - Optional path to scan (default: entire codebase)

## Execution

### 1. Bandit Security Linter
Static analysis for common security issues in Python.

```bash
echo "=== Bandit Security Scan ==="
python -m bandit -r ${ARGUMENTS:-core/ data_sources/ gui_qt/} -ll -f txt 2>/dev/null || echo "Install bandit: pip install bandit"
```

### 2. Check for Hardcoded Secrets
Search for potential secrets in code.

```bash
echo ""
echo "=== Potential Secrets Check ==="
# Common secret patterns
grep -rn --include="*.py" -E "(api_key|apikey|secret|password|token|credential).*['\"][A-Za-z0-9+/=]{20,}['\"]" ${ARGUMENTS:-.} 2>/dev/null | grep -v "test" | head -20 || echo "No obvious hardcoded secrets found"
```

### 3. Dependency Vulnerability Check
Check installed packages for known vulnerabilities.

```bash
echo ""
echo "=== Dependency Vulnerability Check ==="
python -m pip_audit 2>/dev/null || python -m safety check 2>/dev/null || echo "Install pip-audit or safety: pip install pip-audit"
```

### 4. Check for Dangerous Functions
Look for potentially dangerous Python patterns.

```bash
echo ""
echo "=== Dangerous Function Check ==="
echo "eval() usage:"
grep -rn --include="*.py" "eval(" ${ARGUMENTS:-.} 2>/dev/null | grep -v "#.*eval" | head -10 || echo "  None found"

echo "exec() usage:"
grep -rn --include="*.py" "exec(" ${ARGUMENTS:-.} 2>/dev/null | grep -v "#.*exec" | head -10 || echo "  None found"

echo "subprocess shell=True:"
grep -rn --include="*.py" "shell=True" ${ARGUMENTS:-.} 2>/dev/null | head -10 || echo "  None found"

echo "os.system() usage:"
grep -rn --include="*.py" "os.system(" ${ARGUMENTS:-.} 2>/dev/null | head -10 || echo "  None found"
```

### 5. XML Parser Check
Ensure defusedxml is used for XML parsing.

```bash
echo ""
echo "=== XML Security Check ==="
echo "Standard XML usage (should use defusedxml):"
grep -rn --include="*.py" "from xml\|import xml" ${ARGUMENTS:-.} 2>/dev/null | grep -v defused | head -10 || echo "  All XML appears to use defusedxml"
```

### 6. SQL Injection Check
Look for potential SQL injection patterns.

```bash
echo ""
echo "=== SQL Injection Check ==="
echo "String formatting in SQL (potential injection):"
grep -rn --include="*.py" -E "(execute|query).*(%|\.format|f\")" ${ARGUMENTS:-.} 2>/dev/null | head -10 || echo "  No obvious SQL injection patterns"
```

## Report Format

After running scans, summarize:

```markdown
## Security Scan Results

**Target**: ${ARGUMENTS:-Full Codebase}
**Date**: [Current Date]

### Bandit Results
| Severity | Count | Issues |
|----------|-------|--------|
| HIGH | X | List |
| MEDIUM | X | List |
| LOW | X | List |

### Secrets Detection
- [ ] No hardcoded secrets found
- Findings: [List any potential secrets]

### Dependency Vulnerabilities
- [ ] No vulnerable dependencies
- Findings: [List any vulnerable packages]

### Dangerous Functions
- eval(): [Count] usage(s)
- exec(): [Count] usage(s)
- shell=True: [Count] usage(s)
- os.system(): [Count] usage(s)

### XML Security
- [ ] All XML parsing uses defusedxml

### SQL Security
- [ ] No SQL injection patterns detected

### Recommendations
1. [Priority fixes]
2. [Secondary improvements]
```
