---
title: Documentation Manifest
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
---

# Documentation Manifest

> **Purpose**: Central registry for tracking documentation status, ownership, and maintenance schedule.
> **Last Updated**: 2025-11-28
> **Next Review**: 2026-02-28 (Quarterly)

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

### Planning (2 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| roadmap.md | outdated | volatile | 2025-11-28 | 2025-12-15 | Needs consolidation |
| roadmap_pob_integration.md | outdated | volatile | 2025-11-28 | 2025-12-15 | Consider merging with roadmap.md |

### Development (8 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| CARGO_API_GUIDE.md | current | stable | 2025-11-28 | 2026-02-28 | PoE Wiki API reference |
| code_review.md | current | stable | 2025-11-28 | 2026-02-28 | Code practices |
| Context.md | current | stable | 2025-11-28 | 2026-02-28 | Design decisions |
| DATA_SOURCES_GUIDE.md | current | volatile | 2025-11-28 | Per-release | Update when sources change |
| DEVELOPMENT_GUIDE.md | current | stable | 2025-11-28 | 2026-02-28 | Core architecture |
| PLUGIN_SPEC.md | current | stable | 2025-11-28 | 2026-02-28 | Plugin API |
| STASH_SCANNER_CHECKLIST.md | outdated | archived | 2025-11-28 | - | Feature incomplete |
| STASH_SCANNER_SETUP.md | outdated | archived | 2025-11-28 | - | Feature incomplete |

### Features (6 files)

| File | Status | Stability | Last Reviewed | Next Review | Notes |
|------|--------|-----------|---------------|-------------|-------|
| BIS_SEARCH_GUIDE.md | current | volatile | 2025-11-28 | Per-release | New feature |
| GUI_INTEGRATION_GUIDE.md | outdated | volatile | 2025-11-28 | 2025-12-05 | Code paths need update |
| HOW_TO_SEE_MULTI_SOURCE_PRICING.md | current | volatile | 2025-11-28 | Per-release | |
| INTEGRATION_GUIDE.md | current | volatile | 2025-11-28 | Per-release | Meta integration |
| QUICK_REFERENCE.md | current | volatile | 2025-11-28 | Per-release | |
| RARE_EVALUATOR_QUICK_START.md | current | stable | 2025-11-28 | 2026-02-28 | |

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
| Total Documents | 33 |
| Current | 27 |
| Outdated | 5 |
| Deprecated | 0 |
| Archived | 1 |

| Stability | Count |
|-----------|-------|
| Stable | 22 |
| Volatile | 9 |
| Archived | 2 |

---

## Action Items

### Immediate (This Week)

- [ ] Update GUI_INTEGRATION_GUIDE.md code paths
- [ ] Update COVERAGE_GAPS.md metrics (1226 tests, not 163)
- [ ] Add MAXROLL_INTEGRATION to INDEX.md

### Short-term (This Month)

- [ ] Consolidate roadmap.md and roadmap_pob_integration.md
- [ ] Clarify STASH_SCANNER status (active development or archived?)
- [ ] Add frontmatter to all 33 documents

### Long-term (Next Quarter)

- [ ] Create missing docs: DEPLOYMENT.md, DATABASE_SCHEMA.md
- [ ] Consider MkDocs setup for hosted documentation
- [ ] Automated link checking in CI

---

## Review Process

1. **Per-Release Review**: Update all `volatile` docs when releasing
2. **Quarterly Review**: Audit all `stable` docs (Feb, May, Aug, Nov)
3. **On-Demand**: Fix `outdated` docs within 1 week of discovery

## Changelog

| Date | Changes |
|------|---------|
| 2025-11-28 | Initial manifest created from documentation audit |
