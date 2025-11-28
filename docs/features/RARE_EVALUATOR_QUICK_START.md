---
title: Rare Item Evaluator Quick Start
status: current
stability: stable
last_reviewed: 2025-11-28
review_frequency: quarterly
related_code:
  - core/rare_item_evaluator.py
  - test_rare_evaluator.py
---

# Rare Item Evaluator - Quick Start

## Test It Now

```bash
python test_rare_evaluator.py
```

## Use In Code

```python
from core.item_parser import ItemParser
from core.rare_item_evaluator import RareItemEvaluator

parser = ItemParser()
evaluator = RareItemEvaluator()

item = parser.parse(your_item_text)
evaluation = evaluator.evaluate(item)

print(f"Tier: {evaluation.tier}")
print(f"Value: {evaluation.estimated_value}")
print(f"Score: {evaluation.total_score}/100")
```

## Add Your Build

```python
from core.build_matcher import BuildMatcher

matcher = BuildMatcher()
matcher.add_manual_build(
    build_name="Lightning Strike Raider",
    required_life=4000,
    resistances={"fire": 75, "cold": 75, "lightning": 75},
    desired_affixes=["Movement Speed", "Suppression"],
    key_uniques=["Perseverance"]
)
```

## Customize Affixes

Edit `data/valuable_affixes.json` to add more patterns.

## Files
- `data/valuable_affixes.json` - Affix patterns
- `data/valuable_bases.json` - Base types
- `core/rare_item_evaluator.py` - Evaluator
- `core/build_matcher.py` - Build matching

## Next Steps
1. Test with your items
2. Add your builds
3. Integrate into GUI
4. Add more affix patterns

**Status: ✅ Working**
