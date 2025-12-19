# M2.5 Tier 0 Cleanup Log

**Date:** 2025-12-18
**Branch:** m2.5-tier0-cleanup
**Author:** Cline

## Baseline

**Initial Tier 0 violations:** 364

**Rule breakdown:**
- F401 (unused imports): ~150 violations
- F841 (unused variables): ~120 violations
- F541 (f-string missing placeholders): ~50 violations
- F821 (undefined names): ~20 violations
- E741 (ambiguous variable names): ~10 violations
- F811 (redefinition of unused): ~5 violations
- A001 (variable shadows builtin): ~5 violations

**Top violation files:**
- build.py: F541 (f-string without placeholders)
- core/ai_improvement_advisor.py: F401 (unused import)
- core/ai_prompt_builder.py: F401, F541 (unused import, f-string)
- core/build_archetype.py: F541 (f-string without placeholders)
- core/build_archetypes/archetype_matcher.py: F401 (unused import)
- core/client_txt_monitor.py: F401 (unused imports)
- core/cluster_evaluation/models.py: F401 (unused import)
- core/crafting_potential.py: F401 (unused import)
- core/database/repositories/price_alert_repository.py: F401 (unused import)
- core/dps_impact_calculator.py: F841 (unused variable)
- core/interfaces.py: F401 (unused imports)
- core/loot_session.py: F541, F841 (f-string, unused variable)
- core/passive_tree_data.py: F401, F541 (unused import, f-string)
- tests/unit/data_sources/test_mod_data_loader.py: F841 (unused variables)
- tests/unit/data_sources/test_poe_stash_api.py: F841 (unused variable)
- tests/unit/data_sources/test_poeninja_leagues.py: E741 (ambiguous variable name)
- tests/unit/gui_qt/*: F841 (unused variables in tests)

## Cleanup Strategy

### F401 - Unused Imports (Target: 0)
**Approach:**
- Remove truly unused imports
- For imports used for side effects, add `# noqa: F401` with comment

**Files with side-effect imports:**
- None identified - all unused imports can be safely removed

### F841 - Unused Variables (Target: 0)
**Approach:**
- Remove variables that are genuinely unused
- For variables needed for evaluation, rename to `_` if safe
- For intentionally unused variables, rename to `_unused_*` with comment

**Special cases:**
- Test files with mock variables that are intentionally unused
- Variables used only for debugging/logging

### F541 - F-string Missing Placeholders (Target: 0)
**Approach:**
- Convert f-strings without placeholders to regular strings
- Simple mechanical fix

### F821 - Undefined Names (Target: 0)
**Approach:**
- Fix typos and missing imports
- Move type-only imports behind `if TYPE_CHECKING:`

### E741 - Ambiguous Variable Names (Target: 0)
**Approach:**
- Rename `l`, `O`, `I` to meaningful names
- Keep changes local and mechanical

### F811 - Redefinition of Unused (Target: 0)
**Approach:**
- Rename second definition or delete redundant one
- Typically happens in tests

### A001 - Variable Shadows Builtin (Target: 0)
**Approach:**
- Rename variable/arg that shadows builtin
- Keep semantic meaning, update all uses in scope

## Cleanup Execution

### Phase 1: F541 (f-string without placeholders) - 50 violations
**Files:**
- build.py:1
- core/ai_prompt_builder.py:1
- core/build_archetype.py:3
- core/loot_session.py:1
- core/passive_tree_data.py:2

**Action:** Convert to regular strings

### Phase 2: F401 (unused imports) - 150 violations
**Files:**
- core/ai_improvement_advisor.py:1
- core/ai_prompt_builder.py:1
- core/build_archetypes/archetype_matcher.py:1
- core/client_txt_monitor.py:3
- core/cluster_evaluation/models.py:1
- core/crafting_potential.py:1
- core/database/repositories/price_alert_repository.py:1
- core/interfaces.py:2
- core
