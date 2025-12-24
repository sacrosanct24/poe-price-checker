# ML Rare Item Valuation — Goals

## Purpose

Provide ballpark pricing that buckets items into actionable tiers. The goal is not exact price prediction—it's helping players make quick vendor/sell/hold decisions with appropriate confidence signaling.

## MVP Success Criteria

### Output Contract

The model produces:
- **Price estimate** (chaos equivalent)
- **Confidence score** (0–1)

### Tier System

Tiers are derived from tunable thresholds, not hardcoded model output. The application applies thresholds to model output at runtime.

**Default Thresholds (PoE1):**

| Tier | Price Range |
|------|-------------|
| Vendor | < 5c |
| Consider | 5–20c |
| Sell | 20–100c |
| Big Ticket | > 100c |

### Confidence Gating

A tier is only assigned when **both** conditions are met:
- Confidence score meets minimum threshold
- Comparable item count meets minimum threshold

If either check fails → **Unknown** tier.

This combined gate ensures we never present a confident-looking tier based on insufficient evidence.

## MVP Scope

- **Item classes:** Boots, Rings
- **Game:** PoE1 only
- **PoE2:** Thresholds and tuning deferred to post-MVP

## Non-Goals

- Perfect price prediction
- Deep neural networks / end-to-end LLM pricing
- Sale-only ground truth requirement (listings are acceptable noise)
- PoE2 support

## Design Principle

**Trustworthy first, impressive second.**

A wrong high-confidence call is worse than "Unknown." The system should feel reliable before it feels clever.
