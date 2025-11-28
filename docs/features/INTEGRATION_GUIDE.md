---
title: Meta-Based Dynamic Affix Weighting Integration Guide
status: current
stability: volatile
last_reviewed: 2025-11-28
review_frequency: monthly
related_code:
  - data_sources/build_scrapers.py
  - core/meta_analyzer.py
  - core/build_matcher.py
---

# Meta-Based Dynamic Affix Weighting - Integration Guide

## Overview

The build scraping and meta analysis system is now complete. This guide shows how to integrate it with the rare item evaluator for league-specific item valuation.

## System Components

### 1. Build Scrapers (`data_sources/build_scrapers.py`)
- **PoeNinjaBuildScraper**: Scrapes poe.ninja for top builds
- **PobbinScraper**: Fetches PoB codes from pobb.in
- **PastebinScraper**: Fetches PoB codes from pastebin
- **extract_pob_link()**: Extracts PoB links from text

### 2. Meta Analyzer (`core/meta_analyzer.py`)
- **MetaAnalyzer**: Aggregates affix data across builds
- **AffixPopularity**: Tracks appearance count, percentages, value ranges
- **generate_dynamic_weights()**: Creates weights based on popularity

### 3. Build Matcher (`core/build_matcher.py`)
- **BuildMatcher**: Existing infrastructure for PoB import
- **BuildRequirement**: Data structure for build requirements

## Current Capabilities

### Working Features ✓
- ✓ Manual build entry
- ✓ Meta analysis with popularity tracking
- ✓ Dynamic weight generation
- ✓ Cache results per league (data/meta_affixes.json)
- ✓ PoB link extraction from text
- ✓ Integration with existing BuildMatcher

### Partial Implementation ⚠️
- ⚠️ poe.ninja scraper (URL structure may have changed - returns 404)
- ⚠️ PoB code decoder (exists in BuildMatcher but needs integration)

### Not Yet Implemented ❌
- ❌ Automatic weight updates in RareItemEvaluator
- ❌ Meta bonus scoring
- ❌ Scheduled background updates

## Integration Steps

### Step 1: Add Meta Awareness to RareItemEvaluator

**File**: `core/rare_item_evaluator.py`

```python
from pathlib import Path
import json
from datetime import datetime, timedelta

class RareItemEvaluator:
    def __init__(self, ...):
        # Existing initialization
        self.meta_weights = self._load_meta_weights()

    def _load_meta_weights(self) -> dict:
        """Load meta-based weights if available and recent."""
        cache_path = Path("data/meta_affixes.json")

        if not cache_path.exists():
            return {}

        try:
            with open(cache_path) as f:
                data = json.load(f)

            # Check if stale (older than 7 days)
            last_analysis = datetime.fromisoformat(data.get('last_analysis', '2000-01-01'))
            if datetime.now() - last_analysis > timedelta(days=7):
                return {}  # Stale, use static weights

            # Check if same league
            current_league = self.config.get('league', 'Standard')
            if data.get('league') != current_league:
                return {}  # Different league

            # Extract weights
            from core.meta_analyzer import MetaAnalyzer
            analyzer = MetaAnalyzer()
            analyzer.load_cache()
            return analyzer.generate_dynamic_weights()

        except Exception as e:
            logger.warning(f"Failed to load meta weights: {e}")
            return {}
```

### Step 2: Apply Meta Bonuses to Affix Weights

```python
def _get_affix_weight(self, affix_type: str, tier: str) -> int:
    """Get weight for affix, with meta bonus if applicable."""
    # Get base weight from config
    affix_data = self.valuable_affixes.get(affix_type, {})
    base_weight = affix_data.get(f"{tier}_weight", affix_data.get("weight", 5))

    # Apply meta bonus
    if self.meta_weights and affix_type in self.meta_weights:
        meta_weight = self.meta_weights[affix_type]
        # Add +2 bonus for meta affixes (weight >= 10)
        if meta_weight >= 10:
            base_weight = min(10, base_weight + 2)
            logger.debug(f"Meta bonus applied to {affix_type}: {base_weight-2} → {base_weight}")

    return base_weight
```

### Step 3: Update evaluate_affixes() Method

```python
def evaluate_affixes(self, item: ParsedItem) -> Tuple[int, List[AffixMatch]]:
    """Evaluate affixes with meta awareness."""
    matches = []

    # Existing affix matching logic...
    for mod_text in item.explicits:
        for affix_type, affix_data in self.valuable_affixes.items():
            # ... matching logic ...

            # Get weight (now includes meta bonus)
            weight = self._get_affix_weight(affix_type, tier)

            matches.append(AffixMatch(
                affix_type=affix_type,
                mod_text=mod_text,
                value=value,
                weight=weight,  # Includes meta bonus
                tier=tier,
            ))

    # Calculate score
    return self._calculate_affix_score(matches), matches
```

### Step 4: Add Meta Summary to Output

```python
def _format_meta_info(self) -> str:
    """Format meta analysis info for display."""
    if not self.meta_weights:
        return "Meta Analysis: Not available (using static weights)"

    # Load meta data
    with open("data/meta_affixes.json") as f:
        data = json.load(f)

    top_affixes = sorted(
        [(k, v['popularity_percent']) for k, v in data['affixes'].items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]

    lines = [
        f"Meta Analysis: {data['league']} league ({data['builds_analyzed']} builds)",
        "Top Meta Affixes:"
    ]
    for affix, pop in top_affixes:
        lines.append(f"  • {affix}: {pop:.1f}%")

    return "\n".join(lines)
```

## Usage Workflow

### Manual Workflow (Current)

```python
from core.build_matcher import BuildMatcher
from core.meta_analyzer import MetaAnalyzer

# 1. Collect builds (manual for now)
matcher = BuildMatcher()
matcher.add_manual_build("Lightning Strike Raider", ...)
matcher.add_manual_build("RF Juggernaut", ...)

# 2. Analyze meta
analyzer = MetaAnalyzer()
analyzer.analyze_builds(matcher.builds, league="Settlers")

# 3. Generate weights (cached to data/meta_affixes.json)
weights = analyzer.generate_dynamic_weights()

# 4. Evaluate items (automatically uses cached weights if available)
from core.rare_item_evaluator import RareItemEvaluator
evaluator = RareItemEvaluator()
score, matches = evaluator.evaluate_affixes(item)
```

### Automated Workflow (Future)

```python
# Background task (e.g., daily cron job)
def update_meta_weights(league: str):
    """Update meta weights by scraping builds."""
    from data_sources.build_scrapers import PoeNinjaBuildScraper
    from core.meta_analyzer import MetaAnalyzer

    # 1. Scrape builds
    scraper = PoeNinjaBuildScraper(league=league)
    scraped_builds = scraper.scrape_top_builds(limit=50)

    # 2. Convert to BuildRequirement objects
    # (TODO: Implement conversion logic)

    # 3. Analyze meta
    analyzer = MetaAnalyzer()
    analyzer.analyze_builds(builds, league=league)

    # 4. Weights automatically cached
    logger.info("Meta weights updated for league: " + league)
```

## Example: Meta Impact on Item Evaluation

### Before Meta Integration (Static Weights)

```
Rare Boots: Vengeance Stride
Score: 65/100

Affixes:
  [OK] life: +78 Life (tier2) weight:8
  [OK] movement_speed: 25% MS (tier1) weight:9
  [OK] cold_resistance: +45% (tier2) weight:6

Total Weight: 23
```

### After Meta Integration (Dynamic Weights)

```
Rare Boots: Vengeance Stride
Score: 72/100

Affixes:
  [OK] life: +78 Life (tier2) weight:10 [META +2]
  [OK] movement_speed: 25% MS (tier1) weight:9
  [OK] cold_resistance: +45% (tier2) weight:8 [META +2]

Total Weight: 27
Meta Analysis: Settlers league (13 builds)
Top Meta Affixes:
  • resistances: 138.5%
  • life: 130.8%
  • chaos_resistance: 100.0%
```

## Testing

Run the demo to see the full workflow:

```bash
python demo_meta_integration.py
```

This will show:
1. Manual build analysis
2. Weight mapping
3. Build scraping (requires poe.ninja availability)
4. PoB link extraction
5. Complete integration workflow

## Next Steps

### Priority 1: Core Integration
- [ ] Implement `_load_meta_weights()` in RareItemEvaluator
- [ ] Implement `_get_affix_weight()` with meta bonus
- [ ] Update `evaluate_affixes()` to use meta-aware weights
- [ ] Add meta info to evaluation output

### Priority 2: Build Import
- [ ] Fix poe.ninja scraper URL structure
- [ ] Implement PoB code parsing integration
- [ ] Add BuildRequirement converter for ScrapedBuild

### Priority 3: Automation
- [ ] Add scheduled meta updates (daily/weekly)
- [ ] League detection from Trade API
- [ ] Auto-update on league change

### Priority 4: UI Integration
- [ ] Display meta bonuses in GUI
- [ ] Add "Update Meta Weights" button
- [ ] Show league/last update timestamp

## Configuration

### Tuning Parameters

**Meta bonus multiplier** (default: +2 for weight >= 10)
```python
META_BONUS_THRESHOLD = 10  # Apply bonus if meta_weight >= threshold
META_BONUS_AMOUNT = 2      # How much to boost weight
```

**Popularity multiplier** (default: 0.1)
```python
# In MetaAnalyzer.generate_dynamic_weights()
popularity_multiplier = 0.1  # Weight increase per 1% popularity
```

**Cache expiry** (default: 7 days)
```python
META_CACHE_EXPIRY_DAYS = 7
```

## Files Modified

- ✓ `data_sources/build_scrapers.py` (NEW)
- ✓ `core/meta_analyzer.py` (NEW)
- ✓ `requirements.txt` (added beautifulsoup4)
- ✓ `.gitignore` (exclude meta_affixes.json)
- ✓ `demo_meta_integration.py` (NEW)
- ⏳ `core/rare_item_evaluator.py` (TODO)

## Key Insights from Demo

From the demo run with 13 builds:

1. **Chaos Resistance is Essential** (100% of builds)
   - Every build needs chaos res
   - Should be weighted very high (15.0)

2. **Life & Resistances Dominate** (130-138%)
   - Appearing multiple times per build
   - Core defensive layers

3. **Attack/Cast Speed are Common** (46%)
   - Meta is balanced between attack and spell builds

4. **Movement Speed Less Critical** (23%)
   - Than previously thought
   - Current static weight (9) might be too high

5. **Energy Shield is Niche** (46%)
   - Only CI/Low-Life builds
   - Weight correctly reflects specialist nature

## Benefits

1. **League-Specific Valuation**: Automatically adapts to meta shifts
2. **Undervalued Items**: Identifies items valuable for current meta
3. **Accurate Pricing**: Reflects real build requirements
4. **Auto-Updates**: Stays current without manual config changes
5. **Build Integration**: Leverages existing BuildMatcher infrastructure
