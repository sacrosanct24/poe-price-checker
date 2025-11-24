# Rare Item Evaluator & Build Matcher

## ✅ Complete and Working!

Your PoE Price Checker now has a **rare item evaluator** that assesses potential value based on:
- Valuable base types (Hubris Circlet, Opal Ring, etc.)
- Item level (ilvl 84+ for top mods)
- "Evergreen" valuable affixes (life, resistances, ES, movement speed, etc.)
- Build matching (optional - match items to popular builds)

---

## 🎯 Features

### 1. Rare Item Evaluation
- **Scores items 0-100** based on base + affixes + ilvl
- **Tiering system**: Excellent (1div+), Good (50c+), Average (10c+), Vendor
- **Affix matching**: Detects valuable mods like +Life, Resistances, ES, Movement Speed
- **Minimum thresholds**: Only counts high-tier rolls (e.g., 70+ life, 40+ resist)

### 2. Build Matcher
- **Manual build entry**: Define your build requirements
- **PoB import**: Import Path of Building codes (foundation ready)
- **Match scoring**: Items are scored against build needs
- **Multiple builds**: Track league starters, meta builds, etc.

---

## 📊 Test Results

```
TEST 1: Excellent Rare - Hubris Circlet (ilvl 86)
  +78 Life, +42% Fire Res, +85 ES
  Result: EXCELLENT (1div+) - Score 77/100
  
TEST 2: Good Rare - Two-Toned Boots (ilvl 84)
  +72 Life, +25% Movement Speed
  Result: GOOD (50c+) - Score 71/100
  
TEST 3: Vendor - Opal Ring
  +58 Life, +8-14 Phys Damage, +32% Fire Res
  Result: VENDOR (<10c) - Score 25/100
  (Life too low for threshold, phys damage too low)
```

---

## 🚀 How to Use

### Quick Test
```bash
python test_rare_evaluator.py
```

### In Your Code
```python
from core.item_parser import ItemParser
from core.rare_item_evaluator import RareItemEvaluator

parser = ItemParser()
evaluator = RareItemEvaluator()

item = parser.parse(item_text)
evaluation = evaluator.evaluate(item)

print(evaluator.get_summary(evaluation))
# Shows: tier, estimated value, matched affixes
```

---

## 📁 Files Created

1. **data/valuable_affixes.json** - Evergreen valuable mods
2. **data/valuable_bases.json** - High-tier base types  
3. **core/rare_item_evaluator.py** - Main evaluator (350 lines)
4. **core/build_matcher.py** - Build matching system (280 lines)
5. **test_rare_evaluator.py** - Comprehensive tests

---

## 🎨 Customization

### Add More Valuable Affixes

Edit `data/valuable_affixes.json`:
```json
{
  "your_affix_type": {
    "tier1": ["+#% to Maximum Resistances"],
    "weight": 10,
    "min_value": 1,
    "categories": ["helmet", "amulet"]
  }
}
```

### Add Your Build

```python
from core.build_matcher import BuildMatcher

matcher = BuildMatcher()
matcher.add_manual_build(
    build_name="Your Build Name",
    required_life=4000,
    resistances={"fire": 75, "cold": 75, "lightning": 75},
    desired_affixes=["Movement Speed", "Attack Speed"],
    key_uniques=["Unique Name 1", "Unique Name 2"]
)
```

---

## 🔮 Next Steps

### Integration Options

**Option 1: Add to GUI**
- Show rare evaluation when item is pasted
- Display tier + estimated value
- Highlight valuable affixes

**Option 2: Stash Scanner Enhancement**
- Scan stash for valuable rares
- Filter by tier (Excellent/Good only)
- Export results

**Option 3: Build-Specific Scanning**
- Import your build
- Highlight items matching your needs
- Shopping list generation

---

## 💡 How It Works

### Scoring Algorithm

```
Base Score (0-50):
  - Valuable base (Hubris, Opal, etc.): 50
  - Average base: 10
  
Affix Score (0-100):
  - Each valuable affix adds weighted points
  - 3+ high-weight affixes: 90+
  - 2 high-weight affixes: 70+
  - 1 high-weight affix: 50+

Total Score = (Base * 0.3) + (Affixes * 0.6) + (ilvl84+ * 10)

Tiers:
  - 75+: Excellent (1div+)
  - 60+: Good (50c+)
  - 40+: Average (10c+)
  - <40: Vendor (<10c)
```

---

## 📚 Valuable Affixes Included

Currently tracking:
- **Life**: 70+ (weight 10)
- **Resistances**: 40+ each (weight 8)
- **Chaos Res**: 25+ (weight 7)
- **Energy Shield**: 50+ (weight 9)
- **Spell Suppression**: 15+ (weight 10)
- **Crit Multi**: 25+ (weight 9)
- **Movement Speed**: 25+ (weight 9)
- **Cooldown Recovery**: 15+ (weight 8)

You can add more in `data/valuable_affixes.json`!

---

## ✅ Status

- ✅ Rare item evaluation working
- ✅ Base type checking working
- ✅ Affix matching working
- ✅ Tiering system working
- ✅ Build matcher foundation ready
- ✅ Manual build entry working
- ⏳ PoB import (foundation ready, needs testing)
- ⏳ GUI integration (pending)

---

## 🎯 Recommendations

### Immediate Use
1. Run `python test_rare_evaluator.py` to see it in action
2. Add your own builds with `build_matcher.add_manual_build()`
3. Test with your actual rare items

### Future Enhancements
1. Integrate into GUI (show evaluation on paste)
2. Add more affix patterns for complex mods
3. Weight affixes by item slot (e.g., movement speed only on boots)
4. Add fractured/synthesized item detection
5. Influence-specific valuable mods

---

**Your rare item evaluator is ready to use!** 🎉

Test it: `python test_rare_evaluator.py`
