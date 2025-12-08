# Quality Gates

This document defines the quality gates that must be passed before code can be merged. These gates are enforced through automated checks and persona-based reviews.

## Overview

Quality gates ensure that all code meets our standards for:
- **Security** - No vulnerabilities or secrets exposure
- **Architecture** - Follows established patterns and principles
- **Performance** - Acceptable complexity and no blocking operations
- **Testing** - Adequate coverage and test quality
- **Accessibility** - UI components are accessible
- **Documentation** - Code is well-documented

## Gate Definitions

### Gate 1: Automated Checks (CI)

These checks run automatically on every PR:

| Check | Tool | Pass Criteria |
|-------|------|---------------|
| Linting | flake8 | Zero errors |
| Import Order | isort | Properly sorted |
| Type Checking | mypy | No errors in typed modules |
| Unit Tests | pytest | 100% pass rate |
| Security Scan | bandit | No HIGH/CRITICAL issues |
| Dependency Scan | safety | No known vulnerabilities |

```yaml
# CI must pass these commands:
flake8 core/ gui_qt/ data_sources/ --count
isort --check-only core/ gui_qt/ data_sources/
mypy --config-file=mypy.ini core/ data_sources/
pytest tests/unit/ -v --timeout=120
bandit -r core/ data_sources/ -ll
safety check
```

### Gate 2: Test Coverage

| Module | Minimum Coverage | Target Coverage |
|--------|------------------|-----------------|
| `core/` | 70% | 85% |
| `data_sources/` | 65% | 80% |
| `gui_qt/` | 40% | 60% |
| **Overall** | 60% | 80% |

New code should:
- Not decrease overall coverage
- Have at least 80% coverage for new modules
- Include tests for all public APIs

### Gate 3: Security Review

Required for:
- Any code handling user input
- API clients and network code
- Authentication/authorization changes
- Cryptography or secrets handling
- File system operations

Checklist:
- [ ] No hardcoded secrets
- [ ] Input validation on all external data
- [ ] No injection vulnerabilities (SQL, command, path)
- [ ] Secure error handling (no info leakage)
- [ ] Dependencies checked for vulnerabilities

### Gate 4: Architecture Review

Required for:
- New modules or significant refactoring
- Changes to core abstractions
- New dependencies
- Cross-layer interactions

Checklist:
- [ ] Code in correct architectural layer
- [ ] No circular dependencies
- [ ] Dependencies injected via AppContext
- [ ] SOLID principles followed
- [ ] Consistent with existing patterns

### Gate 5: Performance Review

Required for:
- Algorithms processing user data
- Database queries
- Network operations
- UI components with dynamic content

Checklist:
- [ ] No O(n²) or worse without justification
- [ ] Long operations in worker threads
- [ ] Appropriate caching
- [ ] Timeouts on external calls

### Gate 6: Accessibility Review

Required for:
- New UI components
- Changes to existing widgets
- Keyboard shortcut changes

Checklist:
- [ ] Keyboard navigable
- [ ] Screen reader accessible names
- [ ] Color contrast compliant
- [ ] No color-only information

### Gate 7: Documentation Review

Required for:
- Public API changes
- New features
- Architecture changes

Checklist:
- [ ] Docstrings on public functions
- [ ] Type hints present
- [ ] README updated if needed
- [ ] ADR created for significant decisions

## Review Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                        PR Created                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Gate 1: Automated Checks (CI)                   │
│   flake8 │ isort │ mypy │ pytest │ bandit │ safety          │
└─────────────────────────────────────────────────────────────┘
                              │
                     ┌────────┴────────┐
                     │                 │
                 FAIL ▼             PASS ▼
            ┌─────────────┐    ┌─────────────┐
            │ Fix Issues  │    │ Gate 2:     │
            │ & Re-push   │    │ Coverage    │
            └─────────────┘    └──────┬──────┘
                                      │
                              ┌───────┴───────┐
                              │               │
                          FAIL ▼           PASS ▼
                     ┌─────────────┐  ┌──────────────┐
                     │ Add Tests   │  │ Persona      │
                     └─────────────┘  │ Reviews      │
                                      └──────┬───────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
            ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
            │ Security      │      │ Architecture  │      │ Other         │
            │ Auditor       │      │ Guardian      │      │ Personas      │
            └───────┬───────┘      └───────┬───────┘      └───────┬───────┘
                    │                      │                      │
                    └──────────────────────┼──────────────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   All Personas Approve  │
                              └────────────┬────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │        MERGE            │
                              └─────────────────────────┘
```

## Using Quality Gates with Claude Code

### Run All Checks Locally
```bash
/check-pr
```

### Request Persona Reviews
```bash
# Individual reviews
/review-security core/item_parser.py
/review-architecture core/new_module.py
/review-performance data_sources/api_client.py
/review-tests tests/unit/core/test_new.py
/review-accessibility gui_qt/widgets/new_widget.py
/review-docs core/new_module.py

# Comprehensive audit
/audit-full core/
```

### Pre-merge Checklist

Before requesting merge:

```markdown
## Pre-merge Checklist

### Automated Checks
- [ ] CI pipeline passes
- [ ] No flake8 errors
- [ ] No mypy errors
- [ ] All tests pass

### Coverage
- [ ] Coverage not decreased
- [ ] New code has tests

### Security (if applicable)
- [ ] `/review-security` completed
- [ ] No HIGH/CRITICAL findings
- [ ] Secrets scan clean

### Architecture (if applicable)
- [ ] `/review-architecture` completed
- [ ] Layer compliance verified
- [ ] Dependencies approved

### Performance (if applicable)
- [ ] `/review-performance` completed
- [ ] No blocking operations
- [ ] Complexity acceptable

### Accessibility (if applicable)
- [ ] `/review-accessibility` completed
- [ ] Keyboard navigation works
- [ ] Screen reader tested

### Documentation
- [ ] `/review-docs` completed
- [ ] Public APIs documented
- [ ] README updated if needed
```

## Exceptions

Quality gates may be bypassed in emergencies with:
1. Documentation of the exception
2. Approval from project maintainer
3. Follow-up issue to address the gap

Exceptions should be rare and tracked.

## Metrics

Track quality gate effectiveness:
- Pass rate on first review
- Time to pass all gates
- Post-merge bug rate
- Security incident rate

Review and adjust gates quarterly based on metrics.
