---
title: Coverage Gaps Analysis
status: current
stability: volatile
last_reviewed: 2025-11-28
review_frequency: per-release
---

# Suggested Additional Tests - PoE Price Checker

## Coverage Analysis Summary

> **Last Updated**: 2025-11-28
> **Test Count**: 1226 tests
> **Pass Rate**: 100%

Current overall coverage: ~60% (improved from 57%)

### High Priority Gaps

#### 1. Database Module (55% coverage)
Missing coverage in key areas:
- Price statistics calculations
- Sales tracking edge cases  
- Plugin state management
- Price history aggregation
- Error handling in transaction methods

#### 2. GUI Main Window (56% coverage)
Large gaps in:
- Menu actions and dialogs
- Column visibility management
- Session history operations
- Source filtering
- Error handling in GUI operations

#### 3. PoeNinja API (44% coverage)
Missing tests for:
- Currency overview fetching
- Item overview for different types
- Divine rate refresh logic
- Error handling for API failures
- Cache management

#### 4. Logging Setup (0% coverage)
No tests at all - needs basic coverage

#### 5. Game Version Module (49% coverage)
Missing enum validation and edge cases

## Recommended New Tests

See SUGGESTED_TESTS_DETAILED.md for specific test implementations.
