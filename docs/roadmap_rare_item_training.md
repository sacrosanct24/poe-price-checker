# Rare Item Training Module Roadmap

**Version:** 1.0 | **Created:** 2025-12-04 | **Status:** Planning

## Executive Summary

A training system to help users learn rare item valuation through prediction-feedback loops, pattern recognition, and market validation. The core insight: rare item value comes from **affix synergy for specific builds**, not individual mod tiers.

---

## Research Findings

### How FilterBlade/NeverSink Handles It
- **Economy data mining** every 4 hours from trade API
- **Basetype tiering** - items ranked by market activity and average prices
- **Dynamic adjustment** - tiers shift as economy evolves through league
- **Limitation**: Filters catch "probably valuable" items but can't evaluate specific rolls

### Machine Learning Approaches (poeprices.info)
- **Per-item-class models** - separate random forest for each equipment type
- **Feature engineering** - explicit mods, implicit, links, corruptions, influences
- **Acknowledged limitations**:
  - No sell confirmation data (listing ≠ sale)
  - Economy resets every 3 months
  - "Good enough" for bulk estimation, struggles with mirror-tier
  - Complex affix interactions hard to model

### Key Insight: Build-Driven Value
Rare items are valuable when they:
1. Provide **multiple synergistic mods** for a popular build
2. Have **hard-to-craft combinations** (prefix/suffix distribution)
3. Meet **item level thresholds** for top-tier rolls
4. Possess **crafting potential** (open affixes, good base)

---

## Perfect End State Vision 🌟

### The Ideal Training System

```
┌─────────────────────────────────────────────────────────────────┐
│                    RARE ITEM TRAINING CENTER                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   EVALUATE   │  │    LEARN     │  │   PRACTICE   │           │
│  │    Mode      │  │    Mode      │  │    Mode      │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                  │
│  EVALUATE: Paste item → See AI analysis → Compare to market     │
│  LEARN: Review curated examples → Understand why items are good │
│  PRACTICE: Quiz mode → Guess price → Get feedback               │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                     KNOWLEDGE BASE                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ • Meta Build Database (what's popular, what they need)      ││
│  │ • Affix Tier Reference (which mods are T1, crafting rules)  ││
│  │ • Synergy Patterns (life+res+MS on boots = good)            ││
│  │ • Historical Predictions (your accuracy over time)          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    FEEDBACK LOOP                                 │
│                                                                  │
│  1. User evaluates item → Records prediction                     │
│  2. System checks market prices (immediate + 24h later)          │
│  3. Shows prediction accuracy → Identifies blind spots           │
│  4. Suggests learning modules for weak areas                     │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    ADAPTIVE DIFFICULTY                           │
│                                                                  │
│  • Start with obvious cases (6-link, high life+tri-res)         │
│  • Graduate to nuanced (build-specific, crafting bases)         │
│  • Expert: Mirror-tier evaluation, niche build synergies        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Perfect End State Features

1. **Intelligent Item Analysis**
   - Parses all affixes with tier detection
   - Maps mods to meta build requirements
   - Identifies crafting potential (open prefixes/suffixes)
   - Calculates "build fit score" for top 20 builds

2. **Prediction Tracking**
   - User records: "I think this is worth X chaos"
   - System tracks actual market prices
   - Shows accuracy trends over time
   - Identifies item categories where user struggles

3. **Active Learning**
   - Curated examples of valuable items with explanations
   - "Why is this worth 10 divine?" breakdowns
   - Anti-patterns: items that look good but aren't
   - Quiz mode with immediate feedback

4. **Market Integration**
   - Real-time price lookups for similar items
   - Price distribution graphs (not just average)
   - "Items like this sold for X in last 24h"
   - Tracks listing vs. actual sale prices (when detectable)

5. **Pattern Recognition Engine**
   - Learns which affix combinations have value
   - Understands build-specific synergies
   - Knows current meta (updates with build popularity)
   - Identifies underpriced opportunities

---

## Incremental Path to Vision

### Phase 1: Foundation (Weeks 1-2) ✅ START HERE
*Basic prediction tracking and tier detection*

### Phase 2: Knowledge Base (Weeks 3-4)
*Build-aware affix importance*

### Phase 3: Feedback Loop (Weeks 5-6)
*Market validation and accuracy tracking*

### Phase 4: Learning Module (Weeks 7-8)
*Curated examples and quiz mode*

### Phase 5: Intelligence (Ongoing)
*Pattern recognition and ML refinement*

---

## Phase 1: Foundation (Detailed)

### Goals
1. Display affix tiers on any rare item
2. Record user price predictions
3. Fetch current market prices for comparison
4. Store prediction history in database

### Implementation Steps

#### Step 1.1: Affix Tier Detection
**Files to create/modify:**
- `core/affix_tier_detector.py` (NEW)
- Use existing RePoE data for tier thresholds

```python
# core/affix_tier_detector.py
@dataclass
class DetectedAffix:
    mod_text: str
    mod_type: Literal["prefix", "suffix", "implicit"]
    tier: int  # 1 = best, 7+ = low
    tier_label: str  # "T1", "T2", etc.
    value: float  # Numeric value extracted
    max_value: float  # Max possible for this tier

class AffixTierDetector:
    def detect_tiers(self, parsed_item: ParsedItem) -> list[DetectedAffix]:
        """Analyze all mods on item and determine their tiers."""
        pass
```

**Acceptance Criteria:**
- [ ] Correctly identifies prefix vs suffix
- [ ] Detects tier 1-7+ for common mods
- [ ] Handles hybrid mods (life + armor)
- [ ] Shows % of max roll

#### Step 1.2: Prediction Recording UI
**Files to create/modify:**
- `gui_qt/dialogs/prediction_dialog.py` (NEW)
- `gui_qt/main_window.py` (add menu action)

```python
# Simple dialog flow:
# 1. User checks item price
# 2. "Record Prediction" button appears
# 3. Dialog: "What do you think this is worth?"
# 4. User enters: 50 chaos (with confidence: low/medium/high)
# 5. Stored to database with item hash + timestamp
```

**Acceptance Criteria:**
- [ ] Quick entry (chaos or divine with conversion)
- [ ] Confidence selector (helps track certainty vs accuracy)
- [ ] Links to specific item check in history

#### Step 1.3: Market Price Lookup
**Files to create/modify:**
- `data_sources/trade_api_client.py` (enhance)
- `core/price_comparison.py` (NEW)

```python
# Price comparison flow:
# 1. Build trade query from item affixes
# 2. Search for similar items (same base, similar mods)
# 3. Return price distribution: min, median, max, count
# 4. Store as "actual price" for prediction comparison
```

**Acceptance Criteria:**
- [ ] Generates valid trade queries
- [ ] Returns price statistics, not just average
- [ ] Rate-limit compliant (very important!)
- [ ] Caches results to avoid repeated queries

#### Step 1.4: Prediction History Schema
**Database additions:**

```sql
CREATE TABLE item_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_hash TEXT NOT NULL,        -- Hash of item text
    item_text TEXT NOT NULL,        -- Full item text
    parsed_json TEXT,               -- Parsed item as JSON

    -- Prediction
    predicted_chaos REAL NOT NULL,
    confidence TEXT CHECK(confidence IN ('low', 'medium', 'high')),
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Actual (filled in later)
    actual_min_chaos REAL,
    actual_median_chaos REAL,
    actual_max_chaos REAL,
    actual_count INTEGER,           -- How many similar listings
    checked_at TIMESTAMP,

    -- Analysis
    accuracy_pct REAL,              -- How close was prediction?

    game_version TEXT NOT NULL,
    league TEXT NOT NULL
);

CREATE INDEX idx_predictions_accuracy ON item_predictions(accuracy_pct);
CREATE INDEX idx_predictions_date ON item_predictions(predicted_at);
```

**Acceptance Criteria:**
- [ ] Schema migration handled cleanly
- [ ] Query for accuracy trends over time
- [ ] Query for worst prediction categories

#### Step 1.5: Basic Accuracy Dashboard
**Files to create:**
- `gui_qt/windows/prediction_stats_window.py` (NEW)

```
┌─────────────────────────────────────────┐
│        PREDICTION ACCURACY              │
├─────────────────────────────────────────┤
│ Last 7 days:  23 predictions            │
│ Within 25%:   15 (65%)                  │
│ Within 50%:   19 (83%)                  │
│ Way off:      4 (17%)                   │
├─────────────────────────────────────────┤
│ Your blind spots:                       │
│ • Influenced items (42% accuracy)       │
│ • Jewelry (55% accuracy)                │
│ • You undervalue boots consistently     │
└─────────────────────────────────────────┘
```

### Phase 1 Deliverables
1. `core/affix_tier_detector.py` - Tier detection engine
2. `core/price_comparison.py` - Market lookup wrapper
3. `gui_qt/dialogs/prediction_dialog.py` - Record prediction UI
4. `gui_qt/windows/prediction_stats_window.py` - Accuracy dashboard
5. Database schema update for predictions
6. Unit tests for tier detection (target: 90%+ coverage)

### Success Metrics
- Users can see tier labels on any rare item
- Users can record price predictions in <5 seconds
- System retrieves comparable market prices
- Accuracy tracking shows trends over time

---

## Future Phase Sketches

### Phase 2: Knowledge Base
- Import meta builds from poe.ninja/pob
- Map builds to required affixes
- Show "this item fits X build" indicators
- Track which builds user knows well vs poorly

### Phase 3: Feedback Loop
- Scheduled background job: check predictions after 24h
- Push notifications for large misses
- Weekly accuracy report
- "Your pricing improved 12% this week"

### Phase 4: Learning Module
- Curated "valuable item" examples with explanations
- "Why is this worth 10 divine?" breakdowns
- Quiz mode: show item, guess price, get feedback
- Adaptive difficulty based on accuracy

### Phase 5: Intelligence
- Local ML model trained on user's league data
- Pattern recognition for valuable combinations
- "Items like this are often underpriced" alerts
- Integration with PoB for build-specific valuation

---

## Technical Considerations

### Rate Limiting
- Trade API: Max 4 req/sec, be conservative
- Cache aggressively (similar items = similar prices)
- Batch prediction verification in background

### Data Freshness
- Prices change hourly in active league
- Predictions valid for ~24h max
- Clear old data at league transitions

### Privacy
- All data stored locally
- No item data sent to external services (except trade API)
- User can export/delete prediction history

---

## Open Questions

1. **How to handle build popularity shifts?**
   - Meta changes mid-league; need to track build popularity trends

2. **Crafting potential valuation?**
   - Open prefix = worth more, but how much?

3. **PoE2 differences?**
   - Different affix system, need separate models

4. **Mirror-tier edge cases?**
   - Extremely rare items have tiny sample sizes

---

## Next Actions

1. [ ] Create `core/affix_tier_detector.py` with basic tier lookup
2. [ ] Add prediction recording schema to database.py
3. [ ] Build simple prediction dialog UI
4. [ ] Implement trade API query builder for similar items
5. [ ] Create accuracy dashboard window

---

*This roadmap will be updated as phases complete.*
