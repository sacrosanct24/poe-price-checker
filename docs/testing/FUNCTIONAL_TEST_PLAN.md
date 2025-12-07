# Functional Test Plan

End-to-end manual testing checklist for PoE Price Checker.
Use this document to systematically test all features and track progress.

**Test Date:** _______________
**Tester:** _______________
**Version/Commit:** _______________

---

## Legend

- [ ] = Not tested
- [x] = Passed
- [!] = Issue found (document in Notes)
- [~] = Partially working
- [-] = Skipped / N/A

---

## 1. Application Startup

### 1.1 Initial Launch
| Test | Status | Notes |
|------|--------|-------|
| App launches without errors | [ ] | |
| Loading screen appears | [ ] | |
| Main window displays correctly | [ ] | |
| System tray icon appears | [ ] | |
| Status bar shows ready state | [ ] | |
| Rankings cache loads (if valid) | [ ] | |

### 1.2 Configuration Loading
| Test | Status | Notes |
|------|--------|-------|
| Config loads from ~/.poe_price_checker | [ ] | |
| League setting persists between sessions | [ ] | |
| Theme/accent persists between sessions | [ ] | |
| Window position/size restored | [ ] | |

**Startup Ideas/Issues:**
```
(Add notes here during testing)


```

---

## 2. File Menu

### 2.1 Session Management
| Test | Status | Notes |
|------|--------|-------|
| File menu opens | [ ] | |
| New Session creates new tab | [ ] | |
| Session tabs switch correctly | [ ] | |
| Session tabs can be closed | [ ] | |
| Session data persists in each tab | [ ] | |

### 2.2 Import/Export
| Test | Status | Notes |
|------|--------|-------|
| Export History works | [ ] | |
| Export format is correct | [ ] | |

### 2.3 Exit
| Test | Status | Notes |
|------|--------|-------|
| Exit closes application | [ ] | |
| Minimize to tray works (if enabled) | [ ] | |
| Tray icon double-click restores window | [ ] | |

**File Menu Ideas/Issues:**
```


```

---

## 3. Economy Menu

### 3.1 Pricing Section
| Test | Status | Notes |
|------|--------|-------|
| "Top 20 Rankings" opens window | [ ] | |
| Rankings table displays data | [ ] | |
| Rankings categories work | [ ] | |
| "Data Sources Info" shows sources | [ ] | |
| Source status indicators correct | [ ] | |

### 3.2 Sales & Loot Section
| Test | Status | Notes |
|------|--------|-------|
| "Recent Sales" opens window | [ ] | |
| Sales history displays | [ ] | |
| "Sales Dashboard" opens | [ ] | |
| Dashboard charts render | [ ] | |
| "Loot Tracking..." opens | [ ] | |
| Loot dashboard functional | [ ] | |

### 3.3 Historical Data Section
| Test | Status | Notes |
|------|--------|-------|
| "Price History..." opens | [ ] | |
| League dropdown populates | [ ] | |
| Selecting league loads data | [ ] | |
| Currency statistics table shows data | [ ] | |
| - Avg/Min/Max columns correct | [ ] | |
| - Start/End columns correct | [ ] | |
| - Days column shows data points | [ ] | |
| Top 10 uniques table shows data | [ ] | |
| "Aggregate Data" button works | [ ] | |
| - Shows "Re-aggregate" if already done | [ ] | |
| - Aggregation completes without error | [ ] | |
| - Data refreshes after aggregation | [ ] | |
| Switching leagues updates both tables | [ ] | |
| "Collect Economy Snapshot" works | [ ] | |

**Economy Menu Ideas/Issues:**
```


```

---

## 4. View Menu

### 4.1 Windows Section
| Test | Status | Notes |
|------|--------|-------|
| "Session History" opens | [ ] | |
| History window shows past checks | [ ] | |
| "Stash Viewer" opens | [ ] | |
| Stash viewer connects to API | [ ] | |

### 4.2 Theme Submenu
| Test | Status | Notes |
|------|--------|-------|
| Theme submenu opens | [ ] | |
| Standard themes work: | | |
| - Light | [ ] | |
| - Dark | [ ] | |
| - System | [ ] | |
| PoE themes work: | | |
| - Exalted (Gold) | [ ] | |
| - Chaos | [ ] | |
| - Divine | [ ] | |
| Quick Toggle (Ctrl+T) works | [ ] | |
| Theme persists after restart | [ ] | |

### 4.3 Accent Color Submenu
| Test | Status | Notes |
|------|--------|-------|
| Accent submenu opens | [ ] | |
| "Theme Default" option works | [ ] | |
| Currency colors work: | | |
| - Chaos Orb | [ ] | |
| - Divine Orb | [ ] | |
| - Exalted Orb | [ ] | |
| - Mirror | [ ] | |
| Accent applies to UI elements | [ ] | |

### 4.4 Columns Submenu
| Test | Status | Notes |
|------|--------|-------|
| Columns submenu opens | [ ] | |
| Toggling columns hides/shows them | [ ] | |
| All columns can be toggled | [ ] | |

**View Menu Ideas/Issues:**
```


```

---

## 5. Tools Menu

### 5.1 PoB Integration
| Test | Status | Notes |
|------|--------|-------|
| "Import from PoB" opens dialog | [ ] | |
| PoB file picker works | [ ] | |
| Build imports successfully | [ ] | |
| Build stats display in UI | [ ] | |
| "Find Builds..." opens search | [ ] | |

### 5.2 Settings
| Test | Status | Notes |
|------|--------|-------|
| Settings dialog opens | [ ] | |
| All tabs accessible | [ ] | |
| Changes save correctly | [ ] | |
| Cancel discards changes | [ ] | |

**Tools Menu Ideas/Issues:**
```


```

---

## 6. Help Menu

### 6.1 Documentation
| Test | Status | Notes |
|------|--------|-------|
| "Getting Started" opens | [ ] | |
| "Keyboard Shortcuts" opens | [ ] | |
| Shortcuts list is accurate | [ ] | |
| "About" shows version info | [ ] | |

**Help Menu Ideas/Issues:**
```


```

---

## 7. Main Window Features

### 7.1 Price Checking
| Test | Status | Notes |
|------|--------|-------|
| Ctrl+V pastes and checks item | [ ] | |
| Results display in table | [ ] | |
| Multiple sources shown | [ ] | |
| Price values formatted correctly | [ ] | |
| Unique items priced correctly | [ ] | |
| Rare items evaluated | [ ] | |
| Currency items priced | [ ] | |
| Gem items priced | [ ] | |

### 7.2 Results Table
| Test | Status | Notes |
|------|--------|-------|
| Columns sortable | [ ] | |
| Row selection works | [ ] | |
| Double-click opens detail | [ ] | |
| Copy to clipboard works | [ ] | |

### 7.3 Build Stats Panel
| Test | Status | Notes |
|------|--------|-------|
| Life stats display | [ ] | |
| DPS stats display | [ ] | |
| Build name shows | [ ] | |
| Panel updates with build changes | [ ] | |

### 7.4 Rate Limit Indicator
| Test | Status | Notes |
|------|--------|-------|
| Indicator visible in status bar | [ ] | |
| Shows rate limit status | [ ] | |
| Updates during API calls | [ ] | |

**Main Window Ideas/Issues:**
```


```

---

## 8. Context Menus (Right-Click)

### 8.1 Results Table Context Menu
| Test | Status | Notes |
|------|--------|-------|
| Right-click shows menu | [ ] | |
| "Copy" option works | [ ] | |
| "Ask AI About This Item" appears | [ ] | |
| AI analysis opens dialog | [ ] | |
| AI response displays | [ ] | |

### 8.2 History Context Menu
| Test | Status | Notes |
|------|--------|-------|
| Right-click in history works | [ ] | |
| "Re-check Price" works | [ ] | |
| "Ask AI" option available | [ ] | |

### 8.3 Stash Viewer Context Menu
| Test | Status | Notes |
|------|--------|-------|
| Right-click on stash item | [ ] | |
| "Check Price" option works | [ ] | |
| "Ask AI" option works | [ ] | |

**Context Menu Ideas/Issues:**
```


```

---

## 9. AI Features

### 9.1 Configuration
| Test | Status | Notes |
|------|--------|-------|
| AI tab in Settings exists | [ ] | |
| Provider selection works | [ ] | |
| - Gemini | [ ] | |
| - Claude | [ ] | |
| - OpenAI | [ ] | |
| API key can be entered | [ ] | |
| API key validated | [ ] | |
| Custom prompt editor works | [ ] | |
| Build name field works | [ ] | |

### 9.2 AI Analysis
| Test | Status | Notes |
|------|--------|-------|
| AI analysis completes | [ ] | |
| Response is relevant to item | [ ] | |
| Build context included | [ ] | |
| League context included | [ ] | |
| Error handling for API failures | [ ] | |

**AI Feature Ideas/Issues:**
```


```

---

## 10. Stash Features

### 10.1 Stash Viewer
| Test | Status | Notes |
|------|--------|-------|
| Account name entry | [ ] | |
| Tab list loads | [ ] | |
| Tab contents display | [ ] | |
| Item tooltips work | [ ] | |
| Refresh button works | [ ] | |

### 10.2 Rate Limiting
| Test | Status | Notes |
|------|--------|-------|
| 429 errors handled gracefully | [ ] | |
| 60-second wait notification shows | [ ] | |
| Auto-retry after wait | [ ] | |

**Stash Feature Ideas/Issues:**
```


```

---

## 11. Keyboard Shortcuts

| Shortcut | Action | Status | Notes |
|----------|--------|--------|-------|
| Ctrl+V | Paste & check item | [ ] | |
| Ctrl+T | Toggle dark/light theme | [ ] | |
| Ctrl+N | New session | [ ] | |
| Ctrl+W | Close session | [ ] | |
| Ctrl+Q | Quit | [ ] | |
| F1 | Help | [ ] | |
| Escape | Close dialog | [ ] | |

**Shortcut Ideas/Issues:**
```


```

---

## 12. Performance & Stability

| Test | Status | Notes |
|------|--------|-------|
| App responsive during price checks | [ ] | |
| No UI freezing during API calls | [ ] | |
| Memory usage reasonable | [ ] | |
| No crashes during extended use | [ ] | |
| Multiple rapid price checks work | [ ] | |
| Large stash tabs load | [ ] | |
| Price History loads quickly (aggregated) | [ ] | |

**Performance Ideas/Issues:**
```


```

---

## 13. Error Handling

| Test | Status | Notes |
|------|--------|-------|
| Invalid item text handled | [ ] | |
| Network errors shown gracefully | [ ] | |
| API errors don't crash app | [ ] | |
| Missing config handled | [ ] | |
| Database errors handled | [ ] | |

**Error Handling Ideas/Issues:**
```


```

---

## Summary

### Test Results
| Category | Passed | Failed | Skipped |
|----------|--------|--------|---------|
| Startup | /6 | | |
| File Menu | /7 | | |
| Economy Menu | /17 | | |
| View Menu | /18 | | |
| Tools Menu | /6 | | |
| Help Menu | /4 | | |
| Main Window | /12 | | |
| Context Menus | /9 | | |
| AI Features | /12 | | |
| Stash Features | /7 | | |
| Shortcuts | /7 | | |
| Performance | /7 | | |
| Error Handling | /5 | | |
| **TOTAL** | /117 | | |

### Critical Issues Found
```
1.
2.
3.
```

### Feature Ideas / Enhancements
```
1.
2.
3.
4.
5.
```

### UI/UX Improvements
```
1.
2.
3.
```

### Notes for Next Session
```


```

---

*Last updated: 2024-12-06*
