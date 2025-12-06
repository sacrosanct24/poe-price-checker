---
title: Documentation Manifest
status: current
stability: stable
last_reviewed: 2025-12-06
review_frequency: quarterly
---

# Documentation Manifest

> **Purpose**: Central registry for tracking documentation status and maintenance schedule.
> **Last Updated**: 2025-12-06
> **Next Review**: 2026-03-06 (Quarterly)

---

## Metadata Standards

All documentation files should include YAML frontmatter:

```yaml
---
title: Document Title
description: Brief description for search/indexing
status: current | outdated | deprecated
stability: stable | volatile | archived
category: reference | guide | tutorial | troubleshooting | planning
last_reviewed: YYYY-MM-DD
review_frequency: quarterly | monthly | per-release | as-needed
related_code:
  - path/to/file.py
  - path/to/other.py
---
```

### Status Definitions

| Status | Description | Action Required |
|--------|-------------|-----------------|
| `current` | Accurate and up-to-date | Review on schedule |
| `outdated` | Contains stale information | Update within 1 week |
| `deprecated` | Should not be used | Remove or archive |

### Stability Definitions

| Stability | Description | Review Frequency |
|-----------|-------------|------------------|
| `stable` | Core concepts, unlikely to change | Quarterly |
| `volatile` | Changes with features/releases | Per-release |
| `archived` | Historical reference only | Never |

---

## Documentation Registry

### Root Level (4 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| INDEX.md | current | stable | 2025-11-28 | 2026-02-28 | Main navigation hub |
| RARE_ITEM_VALUATION.md | current | stable | 2025-11-28 | 2026-02-28 | Core reference |
| POE_API_REFERENCE.md | current | stable | 2025-11-28 | 2026-02-28 | External API docs |
| POEWATCH_API_REFERENCE.md | current | stable | 2025-11-28 | 2026-02-28 | External API docs |

### Development (6 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| CARGO_API_GUIDE.md | current | stable | 2025-11-28 | 2026-02-28 | PoE Wiki API reference |
| DATA_SOURCES_GUIDE.md | current | volatile | 2025-11-28 | Per-release | Update when sources change |
| DEVELOPMENT_GUIDE.md | current | stable | 2025-11-28 | 2026-02-28 | Core architecture |
| PLUGIN_SPEC.md | current | stable | 2025-11-28 | 2026-02-28 | Plugin API |
| STASH_SCANNER_CHECKLIST.md | current | stable | 2025-12-06 | 2026-03-06 | Implementation checklist |
| STASH_SCANNER_SETUP.md | current | stable | 2025-12-06 | 2026-03-06 | Setup instructions |

### Features (8 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| BIS_SEARCH_GUIDE.md | current | volatile | 2025-11-28 | Per-release | BiS search feature |
| GUI_INTEGRATION_GUIDE.md | current | volatile | 2025-12-06 | Per-release | GUI integration |
| HOW_TO_SEE_MULTI_SOURCE_PRICING.md | current | volatile | 2025-11-28 | Per-release | Multi-source pricing |
| INTEGRATION_GUIDE.md | current | volatile | 2025-11-28 | Per-release | Meta integration |
| ITEM_COMPARISON_GUIDE.md | current | volatile | 2025-12-06 | Per-release | Item comparison feature |
| KEYBOARD_SHORTCUTS.md | current | stable | 2025-12-06 | 2026-03-06 | Shortcuts reference |
| QUICK_REFERENCE.md | current | volatile | 2025-11-28 | Per-release | Quick reference |
| RARE_EVALUATOR_QUICK_START.md | current | stable | 2025-11-28 | 2026-02-28 | Rare evaluator guide |

### Integration (1 file)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| MAXROLL_INTEGRATION.md | current | stable | 2025-11-28 | 2026-02-28 | Was orphaned, now linked |

### MCP/AI (6 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| CLAUDE_SETUP.md | current | stable | 2025-11-28 | 2026-02-28 | Claude-specific |
| MCP_INTEGRATION.md | current | stable | 2025-11-28 | 2026-02-28 | Primary reference |
| MCP_NO_NODEJS.md | current | stable | 2025-11-28 | 2026-02-28 | Alternative setup |
| QUICK_START.md | current | stable | 2025-11-28 | 2026-02-28 | Entry point |
| SETUP_GUIDE.md | current | stable | 2025-11-28 | 2026-02-28 | Detailed setup |
| WHY_MCP.md | current | stable | 2025-11-28 | 2026-02-28 | Decision guide |

### Testing (3 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| COVERAGE_GAPS.md | outdated | volatile | 2025-11-28 | 2025-12-05 | Metrics need update |
| TESTING_GUIDE.md | current | stable | 2025-11-28 | 2026-02-28 | |
| TEST_SUITE_GUIDE.md | current | stable | 2025-11-28 | 2026-02-28 | |

### Troubleshooting (3 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| ITEM_CLASS_BUG.md | current | stable | 2025-11-28 | 2026-02-28 | Historical reference |
| PARSER_ISSUES.md | current | stable | 2025-11-28 | 2026-02-28 | Primary troubleshooting |
| UNKNOWN_ITEM.md | current | stable | 2025-11-28 | 2026-02-28 | Links to PARSER_ISSUES |

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total Documents | 29 |
| Current | 29 |
| Outdated | 0 |
| Deprecated | 0 |

| Stability | Count |
|-----------|-------|
| Stable | 18 |
| Volatile | 11 |

---

## Review Process

1. **Per-Release Review**: Update all `volatile` docs when releasing
2. **Quarterly Review**: Audit all `stable` docs (Feb, May, Aug, Nov)
3. **On-Demand**: Fix `outdated` docs within 1 week of discovery

## Changelog

| Date | Changes |
|------|---------|
| 2025-12-06 | Cleaned up manifest: removed planning docs, updated statistics |
| 2025-11-28 | Initial manifest created from documentation audit |
