# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant design decisions in the PoE Price Checker project.

## What is an ADR?

An Architecture Decision Record captures a single architectural decision along with its context and consequences. ADRs help:

- **Document** why decisions were made
- **Communicate** decisions to team members and AI assistants
- **Preserve** institutional knowledge
- **Enable** better future decisions by understanding past choices

## ADR Format

Each ADR follows this template:

```markdown
# ADR-XXX: Title

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
What is the issue we're addressing? What forces are at play?

## Decision
What is the change we're making?

## Consequences
What becomes easier or harder as a result?
```

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [001](001-three-screen-architecture.md) | Three-Screen Architecture | Accepted |
| [002](002-dependency-injection.md) | Dependency Injection with AppContext | Accepted |
| [003](003-multi-source-pricing.md) | Multi-Source Price Aggregation | Accepted |
| [004](004-ai-provider-abstraction.md) | AI Provider Abstraction Layer | Accepted |
| [005](005-pyqt6-migration.md) | PyQt6 UI Framework | Accepted |

## Creating New ADRs

1. Copy the template below
2. Number sequentially (e.g., `006-your-decision.md`)
3. Fill in all sections
4. Update this README index
5. Commit with the related code changes

## Template

```markdown
# ADR-XXX: [Title]

## Status
Proposed

## Context
[Describe the context and problem]

## Decision
[Describe the decision]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Drawback 1]
- [Drawback 2]

### Neutral
- [Neither positive nor negative impact]

## References
- [Related PR/Issue]
- [External documentation]
```
