# Lint and Fix Command

Run linters and automatically fix issues where possible.

## Usage
`/lint-fix [path]`

## Arguments
- `$ARGUMENTS` - Optional path to lint (default: all source directories)

## Execution

### 1. Auto-fix Import Order
```bash
isort $ARGUMENTS --profile black
```
If no path provided:
```bash
isort core/ gui_qt/ data_sources/ api/ --profile black
```

### 2. Check Flake8 (Cannot Auto-fix)
```bash
flake8 $ARGUMENTS --count --show-source --statistics
```
If no path provided:
```bash
flake8 core/ gui_qt/ data_sources/ api/ --count --show-source --statistics
```

### 3. Type Check
```bash
mypy --config-file=mypy.ini $ARGUMENTS
```

### 4. Summary and Manual Fixes
After running automated fixes:
- Report what was auto-fixed (isort changes)
- List remaining flake8 errors that need manual fixes
- For each flake8 error, provide the fix

### Common Flake8 Fixes
- **E501**: Line too long - break into multiple lines
- **E302**: Expected 2 blank lines - add blank lines
- **F401**: Module imported but unused - remove import
- **F841**: Local variable assigned but never used - remove or use
- **E711**: Comparison to None - use `is None` instead of `== None`
- **E712**: Comparison to True/False - use `if x:` instead of `if x == True:`
