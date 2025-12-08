# LLM-Assisted Development Workflow

This document describes the recommended workflow for developing this project with AI assistance (Claude Code or similar LLMs). It showcases how to use specialized personas and quality gates for rigorous, secure development.

## Overview

This project uses a **persona-based review system** where AI assistants adopt specialized expert roles to provide comprehensive code review. This ensures:

1. **Depth over breadth** - Each persona goes deep in their domain
2. **Consistency** - Checklists ensure nothing is missed
3. **Audit trail** - Reviews are documented and traceable
4. **Security focus** - Security is a first-class concern

## Development Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. PLAN & DESIGN                              │
│  - Discuss requirements with AI                                  │
│  - Architecture Guardian reviews design                          │
│  - Create ADR if significant decision                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    2. IMPLEMENT                                  │
│  - AI writes code following CLAUDE.md guidelines                 │
│  - Test Strategist suggests test cases                           │
│  - Documentation Curator ensures docstrings                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    3. LOCAL VALIDATION                           │
│  - /check-pr (automated checks)                                  │
│  - /security-scan (security analysis)                            │
│  - Fix any issues found                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    4. PERSONA REVIEWS                            │
│  - /review-security for security-sensitive code                  │
│  - /review-architecture for structural changes                   │
│  - /review-performance for algorithms/data processing            │
│  - /review-tests for test files                                  │
│  - /review-accessibility for UI components                       │
│  - /review-docs for documentation                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    5. COMPREHENSIVE AUDIT                        │
│  - /audit-full for final review                                  │
│  - All personas approve                                          │
│  - Quality gates pass                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    6. COMMIT & PUSH                              │
│  - Commit with descriptive message                               │
│  - CI runs automated checks                                      │
│  - Create PR for human review                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Using Personas

### Available Personas

| Persona | File | Use For |
|---------|------|---------|
| Security Auditor | `.claude/personas/security-auditor.md` | Input validation, injection, secrets |
| Performance Engineer | `.claude/personas/performance-engineer.md` | Complexity, memory, async |
| Architecture Guardian | `.claude/personas/architecture-guardian.md` | SOLID, patterns, layers |
| Test Strategist | `.claude/personas/test-strategist.md` | Coverage, test quality |
| Accessibility Champion | `.claude/personas/accessibility-champion.md` | A11y, keyboard, screen reader |
| Documentation Curator | `.claude/personas/documentation-curator.md` | Docstrings, ADRs, README |

### Invoking Personas

```bash
# Single file review
/review-security core/item_parser.py

# Directory review
/review-architecture core/

# Full multi-persona audit
/audit-full gui_qt/widgets/new_widget.py
```

### Persona Selection Guide

| Change Type | Recommended Personas |
|-------------|----------------------|
| New API endpoint | Security, Architecture, Tests, Docs |
| Database query | Security, Performance, Tests |
| UI widget | Accessibility, Architecture, Tests |
| Algorithm | Performance, Tests |
| Refactoring | Architecture, Tests |
| Bug fix | Tests, (relevant domain persona) |
| Documentation | Documentation |

## Slash Commands Reference

### Development Commands
| Command | Purpose |
|---------|---------|
| `/test-module <name>` | Run tests for specific module |
| `/check-pr` | Full CI validation |
| `/add-feature <name>` | Scaffold new feature |
| `/debug-qt [pattern]` | Debug Qt tests |
| `/coverage-gaps <path>` | Find untested code |
| `/lint-fix [path]` | Auto-fix linting |

### Security Commands
| Command | Purpose |
|---------|---------|
| `/security-scan [path]` | Run security tools |
| `/review-security <path>` | Security Auditor review |

### Review Commands
| Command | Purpose |
|---------|---------|
| `/review-security <path>` | Security-focused review |
| `/review-performance <path>` | Performance analysis |
| `/review-architecture <path>` | Architecture compliance |
| `/review-tests <path>` | Test quality review |
| `/review-accessibility <path>` | A11y compliance |
| `/review-docs <path>` | Documentation review |
| `/audit-full <path>` | Comprehensive audit |

## Example Workflows

### Adding a New Feature

```bash
# 1. Plan the feature
> Let's add a price alert feature. What's the best approach?
# AI discusses options, Architecture Guardian perspective

# 2. Create ADR if needed
> Create an ADR for the price alert architecture decision

# 3. Scaffold the feature
> /add-feature price_alerts core

# 4. Implement with TDD
> Write tests first for the price alert feature
> Now implement the PriceAlertService

# 5. Validate
> /check-pr
> /security-scan core/price_alerts.py

# 6. Request reviews
> /review-security core/price_alerts.py
> /review-architecture core/price_alerts.py
> /review-tests tests/unit/core/test_price_alerts.py

# 7. Full audit
> /audit-full core/price_alerts.py

# 8. Commit
> Commit the price alerts feature
```

### Fixing a Security Issue

```bash
# 1. Identify the issue
> /security-scan core/

# 2. Understand the vulnerability
> Explain the SQL injection risk in database.py

# 3. Fix with Security Auditor
> Fix the SQL injection vulnerability, following Security Auditor guidelines

# 4. Verify fix
> /review-security core/database.py

# 5. Add regression test
> Add a test that would catch this SQL injection

# 6. Full validation
> /check-pr
> /audit-full core/database.py
```

### Refactoring Code

```bash
# 1. Analyze current state
> /review-architecture core/price_service.py

# 2. Plan refactoring
> How should we split PriceService to follow Single Responsibility?

# 3. Implement changes
> Refactor PriceService following the Architecture Guardian's recommendations

# 4. Verify no regressions
> /review-tests tests/unit/core/test_price_service.py
> Run all tests for price_service

# 5. Update documentation
> /review-docs core/price_service.py
> Update docstrings to reflect the refactoring
```

## Quality Metrics

Track these metrics to measure LLM-assisted development effectiveness:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Security issues found pre-merge | 100% | Audit findings vs post-merge bugs |
| Test coverage on new code | ≥80% | Coverage reports |
| Architecture violations | 0 | `/review-architecture` findings |
| Documentation coverage | ≥90% | Docstring presence |
| Accessibility compliance | WCAG AA | `/review-accessibility` findings |
| First-time CI pass rate | ≥80% | CI metrics |

## Best Practices

### Do
- Run `/check-pr` before every commit
- Use appropriate personas for the code type
- Create ADRs for significant decisions
- Write tests alongside code
- Document "why" not "what"

### Don't
- Skip security reviews for "simple" changes
- Ignore persona recommendations without justification
- Commit without running tests
- Let coverage decrease
- Merge with unresolved findings

## Continuous Improvement

Review and update:
- **Weekly**: Persona checklists based on new patterns
- **Monthly**: Quality gate thresholds
- **Quarterly**: Overall workflow effectiveness
- **Per release**: ADRs and architecture docs

## Tools & Configuration

### Required Dev Dependencies
```bash
pip install -r requirements-dev.txt
```

### Pre-commit Setup
```bash
pre-commit install
```

### Environment Variables
```bash
export QT_QPA_PLATFORM=offscreen  # For headless Qt testing
export POE_DISABLE_PLUGIN_AUTOLOAD=1  # For test isolation
```
