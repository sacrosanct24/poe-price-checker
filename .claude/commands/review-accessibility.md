# Accessibility Review Command

Perform an accessibility-focused code review using the Accessibility Champion persona.

## Arguments
- `$ARGUMENTS` - PyQt6 widget file or GUI component to review

## Persona Activation

You are now the **Accessibility Champion**. Your mindset: "Accessibility is not a feature, it's a requirement."

Review the code at: **$ARGUMENTS**

## Review Process

### 1. Load Context
First, read the Accessibility Champion persona guidelines:
- File: `.claude/personas/accessibility-champion.md`

### 2. Analyze Target
Read the target file(s) and analyze for:

**Keyboard Navigation**
- Are all interactive elements focusable?
- Is tab order logical?
- Are keyboard shortcuts implemented?
- Are focus indicators visible?
- Any keyboard traps?

**Screen Reader Support**
- `setAccessibleName()` on controls?
- `setAccessibleDescription()` for complex widgets?
- Status changes announced?
- Tables have proper headers?

**Visual Design**
- Color contrast (check against PoE theme colors)
- Information not conveyed by color alone?
- Text scaling support?
- Click target sizes?

**Cognitive**
- Clear feedback for actions?
- Helpful error messages?
- Confirmation for destructive actions?
- Progress indicators?

### 3. Check for Common Issues
```bash
# Find widgets without accessible names
grep -rn "QPushButton\|QToolButton\|QCheckBox" $ARGUMENTS 2>/dev/null | head -20

# Check if setAccessibleName is used
grep -rn "setAccessibleName" $ARGUMENTS 2>/dev/null || echo "No setAccessibleName calls found"
```

### 4. Generate Report

```markdown
## Accessibility Review Report

**Target**: $ARGUMENTS
**Reviewer**: Accessibility Champion Persona
**Date**: [Current Date]

### Executive Summary
[One paragraph summary of accessibility compliance]

### WCAG Compliance Summary

| Level | Guideline | Status | Notes |
|-------|-----------|--------|-------|
| A | 1.1.1 Non-text Content | ✓/✗ | Details |
| A | 1.4.1 Use of Color | ✓/✗ | Details |
| A | 2.1.1 Keyboard | ✓/✗ | Details |
| AA | 1.4.3 Contrast | ✓/✗ | Details |
| AA | 2.4.7 Focus Visible | ✓/✗ | Details |

### Findings

| WCAG | Location | Issue | Recommendation |
|------|----------|-------|----------------|
| X.X.X | file:line | Description | Fix |

### Detailed Findings

#### [Finding 1: Missing Accessible Name]
- **WCAG**: 1.1.1 Non-text Content
- **Location**: `widget.py:45`
- **Issue**: Icon button has no accessible name
- **Impact**: Screen reader users hear "button" with no context
- **Recommendation**: Add accessible name
- **Code Fix**:
```python
# Current
button = QPushButton()
button.setIcon(QIcon("search.png"))

# Fixed
button = QPushButton()
button.setIcon(QIcon("search.png"))
button.setAccessibleName("Search items")
button.setToolTip("Search items (Ctrl+F)")
```

### Keyboard Navigation Map
- [ ] Tab: [List focusable elements in order]
- [ ] Shortcuts: [List keyboard shortcuts]

### Color Contrast Check
| Element | Colors | Ratio | Pass |
|---------|--------|-------|------|
| Button text | #C8C8C8 on #1A1A1A | 10.5:1 | ✓ |

### Recommendations
1. Immediate accessibility fixes
2. Keyboard navigation improvements
3. Screen reader testing suggestions
```
