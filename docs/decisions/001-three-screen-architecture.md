# ADR-001: Three-Screen Architecture

## Status
Accepted (v1.6.0)

## Context

The original PoE Price Checker had a single-window design with multiple tabs and panels. As features grew (price checking, build optimization, sales tracking, AI advisor), the interface became cluttered and navigation confusing. Users struggled to find features, and the codebase had tangled dependencies between UI components.

Key pain points:
- Tab-based navigation didn't scale well
- Related features were scattered across different tabs
- No clear workflow for different user activities
- Complex widget interdependencies

## Decision

Reorganize the application into three dedicated screens, each focused on a distinct workflow:

1. **Item Evaluator** (Ctrl+1) - Price checking and item analysis
   - Price results table with multi-source data
   - Rare item evaluation panel (0-100 scoring)
   - Price rankings sidebar
   - Session tabs for organizing checks

2. **AI Advisor** (Ctrl+2) - Build optimization and upgrade planning
   - Path of Building integration
   - Upgrade recommendations
   - Build comparison tools
   - AI-powered analysis

3. **Daytrader** (Ctrl+3) - Economy and sales tracking
   - Sales history and analytics
   - Loot session tracking
   - Stash visualization
   - Market trends

Each screen is a self-contained component with its own:
- Screen class in `gui_qt/screens/`
- Related widgets and dialogs
- Dedicated worker threads for async operations

## Consequences

### Positive
- **Clearer mental model**: Users understand which screen to use for each task
- **Reduced cognitive load**: Each screen shows only relevant features
- **Better code organization**: Screen-focused modules with clear boundaries
- **Keyboard navigation**: Ctrl+1/2/3 provides instant access
- **Easier maintenance**: Changes to one workflow don't affect others

### Negative
- **Initial learning curve**: Existing users need to adapt to new layout
- **Some duplication**: Common widgets may appear on multiple screens
- **Navigation overhead**: Switching screens takes a keypress (vs. visible tabs)

### Neutral
- Screen state preserved when switching (tabs, scroll positions, etc.)
- Window size and layout saved per-screen

## References
- CHANGELOG.md v1.6.0
- `gui_qt/screens/item_evaluator_screen.py`
- `gui_qt/screens/ai_advisor_screen.py`
- `gui_qt/screens/daytrader_screen.py`
