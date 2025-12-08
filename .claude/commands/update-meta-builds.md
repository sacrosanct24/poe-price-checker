# Update Meta Builds Knowledge

Update the meta builds knowledge base with current trending builds and their gear requirements.

## Update Schedule
- **Pre-League**: Full refresh 1-2 days before league start
- **Week 1-2**: Daily updates (meta forming rapidly)
- **Week 3+**: Weekly updates

## Instructions

1. **Check Current State**
   - Review `data/meta_builds/poe1/current_league.json`
   - Review `data/meta_builds/poe2/current_league.json`
   - Note the `last_updated` field

2. **Gather Current Meta Data**

   For PoE1:
   - Visit poe.ninja/poe1/builds for ladder data
   - Check Maxroll.gg/poe/meta for tier list
   - Note top 5-10 builds by popularity %

   For PoE2:
   - Visit poe2.ninja/builds or poe.ninja/poe2/builds
   - Check Maxroll.gg/poe2/meta for tier list
   - Note top 5-10 builds by popularity %

3. **For Each Meta Build, Capture**:
   - Build name and ascendancy
   - Popularity percentage
   - Tier (S/A/B/C)
   - Primary skill
   - Archetype (melee_attack, ranged_attack, spell, minion, etc.)
   - Key gear slots and their required affixes
   - Key unique items and usage %
   - Desired affixes with weights

4. **Update JSON Files**
   - Update `last_updated` to today's date
   - Add/remove/modify builds based on current meta
   - Update `affix_meta_weights` based on what's popular
   - Archive old data to `history/` folder if significant

5. **Update Generated Weights**
   After updating build data, regenerate `affix_weights.json`:
   ```
   python -c "from core.meta_analyzer import MetaAnalyzer; m = MetaAnalyzer(); m.load_cache(); m.generate_dynamic_weights()"
   ```

## Data Sources

### Primary (Authoritative)
- **poe.ninja/builds** - Real ladder data, percentage breakdowns
- **poe2.ninja/builds** - PoE2 equivalent

### Secondary (Curated Analysis)
- **Maxroll.gg** - Tier lists and guides
- **Mobalytics** - Build tier lists

### Tertiary (Community Pulse)
- **Reddit r/pathofexile** - Community discussions
- **Major streamers** - Zizaran, Mathil, etc.

## Affix Priority Guidelines

| Priority | When to Use |
|----------|-------------|
| `required` | Build literally doesn't work without it |
| `high` | Major DPS/defense increase (10%+) |
| `medium` | Nice improvement (5-10%) |
| `low` | Minor optimization (<5%) |

## Tier Definitions

| Tier | Popularity | Price Weight |
|------|------------|--------------|
| S | 15%+ of ladder | +50% |
| A | 8-15% | +30% |
| B | 4-8% | +15% |
| C | 2-4% | +0% |
| D | <2% | -10% |

## Example Update Workflow

```
1. Open poe.ninja/poe1/builds
2. Note: "Lightning Strike Champion at 12.3%, moved to A tier"
3. Update current_league.json with new popularity
4. Check if gear requirements changed
5. Update affix_meta_weights if attack speed more popular
6. Commit: "meta: Update PoE1 builds for week 3"
```

## Output

After update, provide summary:
```
## Meta Update Summary - [Date]

### PoE1 (3.27 Keepers of the Flame)
- Builds updated: 5
- New additions: SRS Necromancer (S tier, 12.5%)
- Removed: Spectral Helix (dropped below 2%)
- Affix changes: +minion_damage weight increased

### PoE2 (0.4.0 Fate of the Vaal)
- Builds updated: 6
- New additions: Bear Druid (A tier, 6.5%)
- Removed: None
- Affix changes: +talisman items now tracked
```
