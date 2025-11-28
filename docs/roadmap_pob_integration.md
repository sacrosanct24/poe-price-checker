---
title: PoB Build-Aware Integration Roadmap
status: current
stability: volatile
last_reviewed: 2025-11-28
review_frequency: monthly
related_code:
  - core/pob_integration.py
  - core/build_matcher.py
---

# PoB Build-Aware Integration Roadmap

## Overview

Transform item evaluation from generic pricing to **build-aware intelligence** by fully utilizing the Path of Building data we already parse.

## Current State

### What We Have
- PoB share code decoder (working)
- Build stats extraction (Life, EHP, resistances, DPS)
- Equipment parsing with mods
- Character profiles stored in JSON

### What's Underutilized
- Build archetype detection
- Scaling multipliers
- Skill gem context
- Ascendancy synergies
- Stat contribution analysis

---

## Phase 1: Build Archetype Detection (Foundation)

**Goal:** Auto-classify builds to parameterize affix weights

### Tasks
1. **Create BuildArchetype enum/dataclass**
   ```python
   @dataclass
   class BuildArchetype:
       defense_type: Literal["life", "es", "hybrid", "low_life"]
       damage_type: Literal["physical", "elemental", "chaos", "minion"]
       attack_type: Literal["attack", "spell", "dot", "minion"]
       crit_based: bool
       primary_element: Optional[Literal["fire", "cold", "lightning"]]
   ```

2. **Implement archetype detection from PoB stats**
   - Life vs ES ratio → defense_type
   - Damage breakdown → damage_type, primary_element
   - Crit chance/multi presence → crit_based
   - Skill gem tags → attack_type

3. **Store archetype with character profile**

### Files to Modify
- `core/pob_integration.py` - Add archetype detection
- `data/characters.json` - Store archetype per profile

### Success Criteria
- 90%+ accuracy detecting build type from PoB stats
- Archetype stored and accessible for evaluation

---

## Phase 2: Dynamic Affix Weighting

**Goal:** Adjust affix importance based on build archetype

### Tasks
1. **Create weight modifier system**
   ```python
   ARCHETYPE_WEIGHT_MODIFIERS = {
       "life_build": {"life": 1.5, "energy_shield": 0.3},
       "es_build": {"life": 0.3, "energy_shield": 1.5, "intelligence": 1.2},
       "crit_build": {"critical_strike_chance": 1.5, "critical_strike_multiplier": 1.5},
       "elemental_fire": {"fire_damage": 1.5, "cold_damage": 0.5},
   }
   ```

2. **Modify affix evaluator to accept archetype**
   - Load base weights from `valuable_affixes.json`
   - Apply archetype multipliers
   - Return build-adjusted scores

3. **Update UI to show build-aware evaluation**
   - Badge: "Evaluated for [Build Name]"
   - Show which mods are prioritized for this build

### Files to Modify
- `core/affix_evaluator.py` - Add archetype parameter
- `data/archetype_weights.json` - New file for weight modifiers
- `gui_qt/widgets/item_inspector.py` - Show build context

### Success Criteria
- Life mods score higher for life builds
- ES mods score higher for ES builds
- Crit mods only valuable for crit builds

---

## Phase 3: Scaling Context Integration

**Goal:** Apply build's actual scaling multipliers to tier evaluation

### Tasks
1. **Extract scaling multipliers from PoB**
   ```python
   @dataclass
   class BuildScaling:
       life_percent: float  # e.g., 180% increased life
       es_percent: float
       damage_multiplier: float
       crit_multiplier: float
   ```

2. **Calculate effective value of affixes**
   ```python
   def effective_life(flat_life: int, scaling: BuildScaling) -> float:
       return flat_life * (1 + scaling.life_percent / 100)
   ```

3. **Show effective values in UI**
   - "+80 Life (144 effective)" for 180% life scaling
   - Compare to current gear: "+32 effective life upgrade"

### Files to Modify
- `core/pob_integration.py` - Extract scaling values
- `core/effective_value_calculator.py` - New module
- `gui_qt/widgets/item_inspector.py` - Show effective values

### Success Criteria
- Effective values calculated for life, ES, damage
- Upgrade comparisons vs current gear

---

## Phase 4: Skill-Aware Recommendations

**Goal:** Filter and prioritize mods based on active skills

### Tasks
1. **Extract main skill from PoB**
   - Identify 6-link or highest DPS skill
   - Parse gem tags (spell, attack, projectile, melee, etc.)
   - Detect element scaling

2. **Create skill→mod affinity mappings**
   ```python
   SKILL_AFFINITIES = {
       "Cyclone": ["attack_speed", "physical_damage", "area_damage"],
       "Arc": ["spell_damage", "lightning_damage", "cast_speed"],
       "Righteous Fire": ["fire_damage_over_time", "burning_damage"],
   }
   ```

3. **Highlight skill-synergistic mods**
   - Show "Great for Cyclone" badge
   - Deprioritize irrelevant mods

### Files to Create
- `data/skill_affinities.json` - Skill to mod mappings
- `core/skill_analyzer.py` - Skill detection and affinity

### Success Criteria
- Main skill detected from PoB
- Relevant mods highlighted in evaluation

---

## Phase 5: Upgrade Impact Calculator

**Goal:** Show real impact of item upgrades on build

### Tasks
1. **Compare item stats to current gear**
   - Load current gear from PoB profile
   - Calculate stat deltas

2. **Apply scaling to get effective impact**
   ```python
   def calculate_upgrade_impact(new_item, current_item, scaling):
       life_delta = (new_item.life - current_item.life) * scaling.life_mult
       res_delta = sum resistance deltas
       return UpgradeImpact(life=life_delta, resistances=res_delta, ...)
   ```

3. **Show upgrade summary**
   - "+45 effective life, +12% total resistance"
   - "Covers 23% of resistance gap"

### Files to Create
- `core/upgrade_calculator.py` - Impact calculations
- `gui_qt/dialogs/upgrade_comparison_dialog.py` - UI

### Success Criteria
- Clear upgrade impact shown for any item
- Resistance gap tracking

---

## Phase 6: Smart Trade Filtering

**Goal:** Auto-generate build-optimized trade queries

### Tasks
1. **Build trade filters from archetype**
   - Auto-select relevant pseudo stats
   - Set minimums based on build needs

2. **Priority-based filter ordering**
   - Critical stats first (life/ES)
   - Then damage-relevant stats
   - Then nice-to-haves

3. **Gap-based filtering**
   - If under resistance cap, prioritize res
   - If life is low, prioritize life

### Files to Modify
- `data_sources/pricing/trade_query_builder.py` - Build-aware queries

### Success Criteria
- Trade queries auto-tuned to build needs
- Finds actually useful upgrades

---

## Implementation Priority

| Phase | Effort | Impact | Priority |
|-------|--------|--------|----------|
| 1. Archetype Detection | Low | High | **P0** |
| 2. Dynamic Weighting | Medium | High | **P0** |
| 3. Scaling Context | Medium | Medium | P1 |
| 4. Skill Awareness | High | Medium | P2 |
| 5. Upgrade Calculator | Medium | High | P1 |
| 6. Smart Trade Filters | Medium | High | P1 |

**Recommended order:** 1 → 2 → 5 → 6 → 3 → 4

---

## Data Dependencies

### Required from PoB
- PlayerStats (already parsed)
- Skill gems with links (partially parsed)
- Equipment with mods (already parsed)
- Passive tree (not currently parsed - future)

### Required Static Data
- `archetype_weights.json` - Weight modifiers by archetype
- `skill_affinities.json` - Skill to mod mappings

### External APIs
- No new dependencies (use existing Trade API, RePoE)

---

## Success Metrics

1. **Evaluation Accuracy**
   - Users report evaluations match their build needs
   - A/B test: build-aware vs generic evaluation

2. **Search Quality**
   - Trade results more relevant to build
   - Fewer irrelevant items shown

3. **User Engagement**
   - Increased use of PoB profile features
   - More profile imports

---

## Timeline Estimate

- **Phase 1-2:** 1-2 sessions (foundation)
- **Phase 3-4:** 2-3 sessions (context)
- **Phase 5-6:** 2-3 sessions (integration)
- **Total:** 5-8 focused sessions

---

## Notes

- Keep generic evaluation as fallback when no PoB profile loaded
- Consider caching archetype detection (expensive to recalculate)
- May need UI changes to show "Build Mode" vs "Generic Mode"
