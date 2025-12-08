# Full Audit Command

Perform a comprehensive multi-persona audit of code or module.

## Arguments
- `$ARGUMENTS` - File or directory path to audit

## Overview

This command orchestrates all reviewer personas to provide comprehensive feedback on the target code. Each persona reviews from their specialized perspective.

## Audit Process

### 1. Target Analysis
First, understand what's being audited:
- Read the target file(s) at: **$ARGUMENTS**
- Identify the type of code (core logic, UI, API client, tests, etc.)
- Determine which personas are most relevant

### 2. Persona Selection
Based on the code type, prioritize personas:

| Code Type | Primary Personas | Secondary |
|-----------|------------------|-----------|
| `core/` business logic | Security, Architecture, Tests | Performance, Docs |
| `gui_qt/` widgets | Accessibility, Architecture | Performance, Tests |
| `data_sources/` APIs | Security, Performance | Architecture, Tests |
| `tests/` | Test Strategist | Docs |
| Any new feature | All personas | - |

### 3. Run Security Audit
Apply Security Auditor persona:
- Check OWASP vulnerabilities
- Scan for secrets
- Validate input handling

```bash
# Run bandit if available
python -m bandit -r $ARGUMENTS -ll 2>/dev/null || echo "Bandit not installed"
```

### 4. Run Architecture Review
Apply Architecture Guardian persona:
- Check layer compliance
- Verify SOLID principles
- Analyze dependencies

### 5. Run Performance Analysis
Apply Performance Engineer persona:
- Analyze complexity
- Check for blocking operations
- Review memory usage patterns

### 6. Run Test Coverage Check
Apply Test Strategist persona:
- Check test coverage
- Identify missing test cases
- Review test quality

```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/ --cov=$ARGUMENTS --cov-report=term-missing -q --timeout=120 2>&1 | tail -40
```

### 7. Run Accessibility Review (if GUI code)
Apply Accessibility Champion persona:
- Check keyboard navigation
- Verify screen reader support
- Validate color contrast

### 8. Run Documentation Review
Apply Documentation Curator persona:
- Check docstring coverage
- Verify type hints
- Review comments

### 9. Generate Consolidated Report

```markdown
# Comprehensive Audit Report

**Target**: $ARGUMENTS
**Date**: [Current Date]
**Auditors**: Security, Architecture, Performance, Tests, [Accessibility], Documentation

---

## Executive Summary

[2-3 paragraph overview of overall code quality, highlighting critical issues and strengths]

### Risk Assessment
| Category | Risk Level | Critical Issues |
|----------|------------|-----------------|
| Security | LOW/MED/HIGH | Count |
| Architecture | LOW/MED/HIGH | Count |
| Performance | LOW/MED/HIGH | Count |
| Test Coverage | LOW/MED/HIGH | Count |
| Accessibility | LOW/MED/HIGH | Count |
| Documentation | LOW/MED/HIGH | Count |

---

## Critical Findings (Immediate Action Required)

### 1. [Critical Finding Title]
- **Category**: Security/Architecture/etc.
- **Severity**: CRITICAL
- **Location**: `file.py:line`
- **Issue**: Description
- **Recommendation**: Fix
- **Assigned Persona**: Security Auditor

---

## Security Audit

### Summary
[Security Auditor findings summary]

### Findings
| Severity | Issue | Location | Status |
|----------|-------|----------|--------|
| ... | ... | ... | ... |

---

## Architecture Review

### Summary
[Architecture Guardian findings summary]

### Layer Compliance: [PASS/FAIL]
### SOLID Compliance: [X/5]

### Findings
| Severity | Issue | Location | Principle |
|----------|-------|----------|-----------|
| ... | ... | ... | ... |

---

## Performance Analysis

### Summary
[Performance Engineer findings summary]

### Complexity Hotspots
| Function | Complexity | Risk |
|----------|------------|------|
| ... | ... | ... |

### Findings
| Impact | Issue | Location |
|--------|-------|----------|
| ... | ... | ... |

---

## Test Coverage

### Summary
[Test Strategist findings summary]

### Coverage: X%

### Missing Tests
1. ...
2. ...

---

## Accessibility (if applicable)

### Summary
[Accessibility Champion findings summary]

### WCAG Compliance: [Level]

---

## Documentation

### Summary
[Documentation Curator findings summary]

### Docstring Coverage: X%

---

## Recommendations by Priority

### Immediate (Before Merge)
1. [Critical security fix]
2. [Critical bug fix]

### Short-term (This Sprint)
1. [Architecture improvement]
2. [Test coverage addition]

### Long-term (Backlog)
1. [Performance optimization]
2. [Documentation improvement]

---

## Approval Status

| Persona | Approval | Notes |
|---------|----------|-------|
| Security Auditor | ✓/✗ | Conditions |
| Architecture Guardian | ✓/✗ | Conditions |
| Performance Engineer | ✓/✗ | Conditions |
| Test Strategist | ✓/✗ | Conditions |
| Accessibility Champion | ✓/✗/N/A | Conditions |
| Documentation Curator | ✓/✗ | Conditions |

**Overall Verdict**: [APPROVED / APPROVED WITH CONDITIONS / NEEDS REVISION]
```
