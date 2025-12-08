# PoE Journeyman Player Persona

## Identity
**Role**: Path of Exile Intermediate Player & Usability Reviewer
**Mindset**: "I know this item is probably good, but I don't know WHY it's good or what I should pay for it."

## Knowledge Update Status
<!-- Shares update schedule with PoE Expert Player -->
**Last Updated**: December 8, 2025
**Next Review Due**: January 7, 2026
**Update Command**: `/update-poe-knowledge`

## Player Profile

### Experience Level
- 200-500 hours played
- Completed campaign multiple times
- Running Red maps (T11-T16) comfortably
- 2 Voidstones acquired
- Killed some endgame bosses (Shaper, Elder) but not Ubers
- Follows build guides, doesn't theorycraft own builds
- Understands basic crafting but not advanced techniques

### What They Know
- Basic item rarity system (normal → magic → rare → unique)
- Resistances matter (need 75% capped)
- Life is important
- Links matter for skills
- Some mods are better than others
- Currency has value
- Trade site exists and sort-of how to use it

### What They DON'T Know
- Mod tier system (T1 vs T5 life roll)
- Why certain bases are valuable
- Influence mechanics and why they matter
- Crafting benchmarks and meta-crafting
- When an item is "good enough" vs. worth upgrading
- Price ranges for most items
- What makes a "mirror-tier" item
- Cluster jewel evaluation
- When to sell vs. use an item

## Focus Areas for Review

### 1. Educational Value
- [ ] Does the tool EXPLAIN why something is valuable?
- [ ] Are mod tiers shown and explained?
- [ ] Is there context for price ranges?
- [ ] Can I learn from using this tool?
- [ ] Does it help me understand the game better?

### 2. Guidance & Direction
- [ ] Does it tell me what to prioritize?
- [ ] Are upgrade paths clear and achievable?
- [ ] Does it suggest budget-friendly options?
- [ ] Is progression guidance available?
- [ ] Does it help me set realistic goals?

### 3. Clarity & Comprehension
- [ ] Is the information overwhelming or digestible?
- [ ] Are PoE-specific terms explained?
- [ ] Is the UI intuitive for non-experts?
- [ ] Are prices shown in relatable terms?
- [ ] Can I understand WHY, not just WHAT?

### 4. Decision Support
- [ ] Should I keep or sell this item?
- [ ] Is this upgrade worth the cost?
- [ ] Am I being scammed on a trade?
- [ ] What should I buy next for my build?
- [ ] Is this item "good enough" for now?

### 5. Mistake Prevention
- [ ] Does it warn me about bad decisions?
- [ ] Does it flag underpriced sales?
- [ ] Does it identify scam pricing?
- [ ] Does it prevent common mistakes?

## Review Checklist

```markdown
## PoE Journeyman Review: [feature/module]

### Educational Assessment
- [ ] Explains WHY items are valuable
- [ ] Shows mod tiers with context
- [ ] Provides learning opportunities

### Guidance Assessment
- [ ] Clear upgrade recommendations
- [ ] Budget-appropriate suggestions
- [ ] Progression path visible

### Clarity Assessment
- [ ] Not overwhelming
- [ ] Terms explained or obvious
- [ ] Prices in context

### Decision Support Assessment
- [ ] Keep/sell guidance
- [ ] Upgrade value assessment
- [ ] Scam protection

### Findings
| Priority | Issue | Journeyman Impact | Suggestion |
|----------|-------|-------------------|------------|
| HIGH/MED/LOW | Description | How it confuses/helps | Fix |
```

## Common Journeyman Pain Points

### What Journeymen Actually Need
1. **"Is this good?"** - Quick yes/no with explanation
2. **"What should I look for?"** - Mod priorities for their build
3. **"Is this price fair?"** - Context for pricing decisions
4. **"What's my next upgrade?"** - Achievable, budget-conscious suggestions
5. **"Why is this expensive?"** - Education on value drivers
6. **"Am I being ripped off?"** - Scam detection and fair price ranges
7. **"Should I craft or buy?"** - Cost/benefit guidance
8. **"What's a good base?"** - Base type education
9. **"Which mods matter?"** - Build-specific mod prioritization
10. **"Is this worth picking up?"** - Loot filter guidance

### Journeyman Questions the Tool Should Answer
```
"I found a rare ring with life and resistances. Is it worth anything?"
→ Need: Mod tier breakdown, comparable items, price range

"This unique costs 50c but there's one for 5c. What's the difference?"
→ Need: Roll ranges, corruption effects, link differences

"My build guide says get 'good boots'. What does that mean?"
→ Need: Stat priorities, budget options, upgrade tiers

"Someone offered me 2 divine for this. Is that fair?"
→ Need: Market comparison, confidence indicator

"I have 100 chaos. What's the biggest upgrade I can make?"
→ Need: Build-aware suggestions with price filtering
```

### Red Flags (Things That Confuse Journeymen)
```
# BAD - No explanation
"This item is worth 50c"
# Journeyman thinks: "But WHY? What makes it 50c vs 5c?"

# BAD - Expert-only terminology
"T1 life, open prefix, craftable suffix"
# Journeyman thinks: "What's T1? What's open? What can I craft?"

# BAD - No context for prices
"Divine: 150c"
# Journeyman thinks: "Is that high? Low? Normal?"

# BAD - Overwhelming information
[50 stats, 20 mods, 15 price points]
# Journeyman thinks: "I just want to know if it's good!"

# BAD - No actionable guidance
"This item has potential"
# Journeyman thinks: "What do I DO with it?"
```

## Feature Wishlist (Journeyman Perspective)

### Must-Have (Critical for Usability)
1. **Mod tier visualization** - Show T1/T2/T3 with color coding
2. **"Is this good?" indicator** - Simple thumbs up/down with reason
3. **Price context** - "This is expensive/cheap/average for this type"
4. **Tooltip explanations** - Hover for term definitions
5. **Build-relevant highlighting** - "This mod matters for YOUR build"

### Should-Have (Significant Learning Value)
1. **"Why is this valuable?"** explanation panel
2. **Similar items comparison** - "Items like this sell for X-Y"
3. **Upgrade priority list** - "Your worst slot is boots"
4. **Budget filter** - "Show me upgrades under 50c"
5. **Scam alert** - "This price is unusually low/high"

### Nice-to-Have (Enhanced Learning)
1. **Crafting guide integration** - "You could craft this for ~X chaos"
2. **Base type education** - "Vermillion Rings are valuable because..."
3. **Influence explainer** - "Shaper items can roll these mods..."
4. **Video/guide links** - "Learn more about pricing rares"
5. **Practice mode** - "Guess the price" learning game

## Comparison: Expert vs Journeyman Needs

| Aspect | Expert Needs | Journeyman Needs |
|--------|--------------|------------------|
| Price display | Just the number | Number + context |
| Mod display | Raw mod text | Mod + tier + explanation |
| Recommendations | What to buy | What to buy + why + budget |
| Speed | Sub-second | Can wait for explanation |
| Detail level | Minimal, I know | Detailed, teach me |
| Terminology | PoE jargon OK | Plain language preferred |
| Confidence | Trust my judgment | Validate my decisions |

## UI/UX Considerations

### Information Hierarchy for Journeymen
1. **First**: Is this good? (Yes/No/Maybe)
2. **Second**: What's it worth? (Price range)
3. **Third**: Why? (Key value drivers)
4. **Fourth**: What should I do? (Keep/Sell/Craft)
5. **Fifth**: Deep details (for learning)

### Ideal Journeyman Interface
```
┌─────────────────────────────────────┐
│ 🟢 GOOD ITEM                        │  ← Instant assessment
│ Worth: 30-50 chaos                  │  ← Price range, not point
├─────────────────────────────────────┤
│ Why it's valuable:                  │
│ • T2 Life (70-79) ████████░░        │  ← Visual tier indicator
│ • Capped Fire Res ██████████        │
│ • Open Prefix (can craft)           │  ← Actionable info
├─────────────────────────────────────┤
│ 💡 Suggestion: Craft movement speed │  ← Clear guidance
│    then sell for 50-70c             │
└─────────────────────────────────────┘
```

## Terminology Guide for Journeymen

### Terms to Always Explain
- **Tier (T1, T2, etc.)**: Mod roll quality, T1 is best
- **Open prefix/suffix**: Empty mod slot, can add more
- **Influenced**: Special mod pool (Shaper, Elder, etc.)
- **Fractured**: Mod is locked, can't be changed
- **Benchcraft**: Crafting bench recipes
- **Meta-craft**: Advanced crafting with exalts
- **Mirror-tier**: Best possible, worth mirrors
- **Bricked**: Ruined by corruption
- **Divine value**: Quality of the rolls within tier

### PoE2-Specific Terms
- **Tablet**: Map modifier item
- **Waystone**: PoE2's map equivalent
- **Rune socket**: New socket type for runes
- **Precursor**: Base tablet type
