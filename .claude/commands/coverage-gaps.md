# Coverage Gaps Command

Identify untested code paths in a specific module.

## Usage
`/coverage-gaps <module_path>`

## Arguments
- `$ARGUMENTS` - Module path (e.g., `core/item_parser.py`, `core`, `gui_qt/widgets`)

## Execution

### 1. Run Coverage Analysis
```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/ --cov=$ARGUMENTS --cov-report=term-missing --cov-report=html -q --timeout=120 2>&1 | grep -E "(TOTAL|Missing|Name|---)" | head -50
```

### 2. Identify Critical Gaps
After running coverage, analyze:
- Functions with 0% coverage (completely untested)
- Complex functions (high cyclomatic complexity) with low coverage
- Error handling paths not covered
- Edge cases in conditionals

### 3. Generate Test Suggestions
For each gap found, suggest:
- Test case name
- What scenario it covers
- Example test structure

### 4. Priority Ranking
Rank gaps by importance:
1. **Critical**: Public API methods with no tests
2. **High**: Error handling and edge cases
3. **Medium**: Internal methods with complex logic
4. **Low**: Simple getters/setters, logging

### Output Format
```
Module: {module_path}
Current Coverage: X%

Critical Gaps (0% coverage):
- function_name (line X-Y): Needs tests for...

High Priority:
- function_name (line X): Missing edge case for...

Suggested Tests:
1. test_function_name_happy_path
2. test_function_name_error_case
3. test_function_name_edge_case
```
