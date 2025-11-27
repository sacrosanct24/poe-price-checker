# Next Session Plan: Build-Aware Integration

## Priority Tasks

### 1. Database Schema v4 Migration
Add historical analytics columns:
```sql
ALTER TABLE sales ADD COLUMN league TEXT;
ALTER TABLE sales ADD COLUMN rarity TEXT;
ALTER TABLE sales ADD COLUMN game_version TEXT;
```

### 2. Build Archetype Detection (Phase 1)
**File:** `core/build_archetype.py` (new)

Create `BuildArchetype` dataclass:
- `defense_type`: life | es | hybrid | low_life
- `damage_type`: physical | elemental | chaos | minion
- `attack_type`: attack | spell | dot | minion
- `crit_based`: bool
- `primary_element`: fire | cold | lightning | None

Detection logic from PoB PlayerStats:
- Life > 3x ES → life build
- ES > 2x Life → ES build
- Crit chance > 30% → crit build
- Check main skill tags for attack/spell

### 3. Dynamic Affix Weighting (Phase 2)
**File:** `data/archetype_weights.json` (new)

```json
{
  "life_build": {"life": 1.5, "energy_shield": 0.3},
  "es_build": {"life": 0.3, "energy_shield": 1.5},
  "crit_build": {"critical_strike_chance": 1.5}
}
```

Modify `rare_item_evaluator.py` to accept archetype parameter.

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `core/build_archetype.py` | CREATE | Archetype detection |
| `data/archetype_weights.json` | CREATE | Weight modifiers |
| `core/database.py` | MODIFY | Schema v4 migration |
| `core/rare_item_evaluator.py` | MODIFY | Accept archetype |
| `tests/test_build_archetype.py` | CREATE | Unit tests |

---

## Test Plan

1. Unit tests for archetype detection
2. Integration test: PoB code → archetype → evaluation
3. Verify weighted scoring changes based on build type
4. Check database migration works cleanly

---

## Definition of Done

- [ ] BuildArchetype dataclass implemented
- [ ] Detection algorithm with 90%+ accuracy
- [ ] Archetype stored with character profile
- [ ] Affix weights adjusted by archetype
- [ ] Database schema v4 migrated
- [ ] All tests passing
- [ ] Documentation updated

---

## Reference Documents

- `docs/roadmap_pob_integration.md` - Full 6-phase roadmap
- `docs/development/DATA_SOURCES_GUIDE.md` - Data source authority
- `core/pob_integration.py` - Existing PoB decoder

---

## Quick Start Command

```bash
# Run existing tests first
python -m pytest tests/ -v --ignore=tests/integration -x

# Then start implementing Phase 1
# Edit core/build_archetype.py
```
