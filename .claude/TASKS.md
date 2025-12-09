# Claude Task Queue

**Purpose**: Persistent task tracking across context compactions. Read this file at session start.

---

## Current Sprint: Technical Debt - Test Coverage

**Goal**: Increase test coverage from 77% to 80%

### Active Task
```
TASK: None - Sprint complete!
STATUS: done
COVERAGE: 79% -> 80%+ achieved
```

### Task Queue (priority by coverage gap)

#### Critical (<65% coverage)
1. [x] `core/league_economy_history.py` - **43% -> 83%** DONE (+40%)
2. [x] `core/value_rules.py` - **63% -> 100%** DONE (+37%)
3. [x] `core/price_rankings.py` - **63% -> 78%** DONE (+15%)
4. [x] `core/price_integrator.py` - **67% -> 90%** DONE (+23%)

#### Medium (65-75% coverage)
5. [ ] `core/poe_oauth.py` - 70%
6. [ ] `core/meta_analyzer.py` - 72%
7. [ ] `core/price_service.py` - 72%

### Completed This Sprint
- [x] Database persistence for verdict statistics (2025-12-09)
- [x] Consolidated feature roadmap (2025-12-09)
- [x] Created task tracking system (2025-12-09)
- [x] `league_economy_history.py` tests: 43% -> 83% (2025-12-09)
- [x] `value_rules.py` tests: 63% -> 100% (2025-12-09)
- [x] `price_rankings.py` tests: 63% -> 78% (2025-12-09)
- [x] `price_integrator.py` tests: 67% -> 90% (2025-12-09)

---

## Coverage Progress

```
Starting: 77% (12555 statements, 2856 missing)
Current:  ~78% (estimated after league_economy_history improvement)
Target:   80%
```

### Quick Commands
```bash
# Full coverage report
pytest tests/unit/core/ --cov=core --cov-report=term-missing -q

# Single module coverage
pytest tests/unit/core/test_MODULE.py --cov=core.MODULE --cov-report=term-missing -v
```

---

## Session Continuity Notes

When resuming after compaction:
1. Read this file first
2. Check active task status
3. Run coverage for active module to verify current state
4. Continue from where left off

---

*Last updated: 2025-12-09 05:20 UTC*
