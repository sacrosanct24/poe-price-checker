# Reviewer Personas

This directory contains specialized reviewer personas for AI-assisted code review. Each persona represents a domain expert with specific focus areas, checklists, and review guidelines.

## Purpose

When an LLM reviews code, it can adopt these personas to provide focused, expert-level feedback. This ensures:

1. **Comprehensive coverage** - Multiple perspectives catch different issues
2. **Consistent quality** - Checklists ensure nothing is missed
3. **Specialized depth** - Each persona goes deep in their domain
4. **Audit trail** - Reviews are traceable and documented

## Available Personas

### Technical Reviewers
Code quality, security, and engineering best practices.

| Persona | Focus | Command |
|---------|-------|---------|
| [Security Auditor](security-auditor.md) | OWASP, secrets, input validation | `/review-security` |
| [Performance Engineer](performance-engineer.md) | Complexity, memory, async | `/review-performance` |
| [Architecture Guardian](architecture-guardian.md) | Design patterns, SOLID, coupling | `/review-architecture` |
| [Test Strategist](test-strategist.md) | Coverage, edge cases, test quality | `/review-tests` |
| [Accessibility Champion](accessibility-champion.md) | A11y, Qt accessibility | `/review-accessibility` |
| [Documentation Curator](documentation-curator.md) | Docstrings, ADRs, accuracy | `/review-docs` |

### Domain Expert Reviewers
Product functionality and user experience from domain expertise.

| Persona | Focus | Command | Knowledge Update |
|---------|-------|---------|------------------|
| [PoE Expert Player](poe-expert-player.md) | Game functionality, feature gaps, competitive analysis | `/review-poe-expert` | Every 30 days |
| [PoE Journeyman Player](poe-journeyman-player.md) | Usability, education, guidance, clarity | `/review-poe-journeyman` | Every 30 days |

**Player Persona Comparison**:
| Aspect | Expert (5000+ hrs) | Journeyman (200-500 hrs) |
|--------|-------------------|-------------------------|
| Focus | Is it accurate & fast? | Is it understandable? |
| Evaluates | Feature completeness | Educational value |
| Asks | "Would I use this?" | "Would I learn from this?" |
| Priorities | Speed, accuracy, power features | Clarity, guidance, explanation |

**Note**: Domain expert personas require periodic knowledge updates to stay current with game changes. Use `/update-poe-knowledge` to refresh game information.

### Reference Materials
| Resource | Description |
|----------|-------------|
| [PoE Glossary](poe-glossary.md) | Comprehensive terms, abbreviations, and slang |

## Usage

### Single Persona Review
```
/review-security core/item_parser.py
```

### Multi-Persona Audit
```
/audit-full core/
```

### In Code Comments
Reference personas in PR descriptions:
```markdown
## Review Requested
- [ ] @SecurityAuditor - New API endpoint
- [ ] @PerformanceEngineer - Database query changes
- [ ] @ArchitectureGuardian - New service pattern
```

## Creating New Personas

1. Copy `_template.md` to `your-persona.md`
2. Define expertise, focus areas, and checklist
3. Add corresponding slash command in `.claude/commands/`
4. Update this README

## Review Workflow

```
┌─────────────────┐
│  Code Change    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Auto-Detection  │ ← Suggests relevant personas
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Security│ │ Perf  │ │ Arch  │ │ Tests │
│Auditor│ │Engineer│ │Guardian│ │Strategist│
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │        │        │
    └────┬────┴────────┴────────┘
         │
         ▼
┌─────────────────┐
│ Combined Report │
└─────────────────┘
```
