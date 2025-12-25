# ML Rare Item Valuation — Evaluation Plan

## Purpose

Define two evaluation stages:
1. **Feasibility Gate (Phase 0):** Can this approach work? Answered before committing to full implementation.
2. **Ongoing Evaluation (Post-MVP):** Is it working? Measured continuously after deployment.

---

## Phase 0 Gate (Feasibility)

### Data Collection MVP

| Parameter | Value |
|-----------|-------|
| Scope | Top 10 base types for Boots and Rings |
| Frequency | Every 30 minutes |
| Duration | 2 weeks minimum |
| Store | listing_id, price_chaos, timestamps, full affix details, seller |

### Listing Lifecycle Tracking

Compare snapshots to detect when listings disappear:

- **DISAPPEARED_FAST:** Gone within 24 hours of first observation (likely sold/sniped)
- **DISAPPEARED_SLOW:** Persisted 24+ hours before disappearing (typical sale/delist)

Track `time_to_disappear` for each listing.

### Listing Freshness (for comps)

| State | Age | Usage |
|-------|-----|-------|
| LIVE | < 7 days | Eligible, full weight |
| STALE | 7–14 days | Eligible, down-weighted |
| EXCLUDED | > 14 days | Not used |

### Signal Sanity Check

Test 3–5 known-valuable affixes to confirm price signal exists:

**Boots:**
- Movement speed
- Life
- Resist trifecta (fire + cold + lightning)
- Spell suppression

**Rings:**
- Life
- Resists
- Attributes

**Method:**
- Compare median price with-affix vs. without-affix
- Require statistical significance (p < 0.05)

### Baseline Model

- **Naive model:** Median price by base type
- **Metrics:** MAE, RMSLE
- This is the bar any ML model must beat

### Go/No-Go Criteria

| Outcome | Condition | Action |
|---------|-----------|--------|
| **PASS** | 3+ known-valuable affixes show statistically significant positive price correlation | Proceed to Phase 1 |
| **FAIL** | No discernible signal | Revisit approach or abandon |

Decision must be documented before proceeding.

---

## Ongoing Evaluation (Post-MVP)

### Model Metrics

- **Primary:** RMSLE on held-out test set
- **Secondary:** MAE, median absolute error

### Slice Analysis

Evaluate model performance segmented by:
- Base type
- League age bucket
- Price band (Vendor / Consider / Sell / Big Ticket)

### Value Bucket Accuracy

| Question | Metric |
|----------|--------|
| What % of Big Ticket predictions actually sold high? | Precision at top tier |
| What % of Vendor predictions were correctly low-value? | Precision at bottom tier |
| How often does confidence gate trigger? | Unknown rate |

### Comp Quality

- **Human review:** Are returned comps intuitively similar?
- **Similarity score distribution:** Should cluster tightly for good matches
- **Comp price dispersion:** Tight cluster = high confidence

### Regression Tests

- Golden items with expected price bands
- Run on each model update
- Fail the build if golden items fall outside expected bands

---

## Data Requirements Note

- **No historical data exists.** Collection must precede feasibility check.
- **Existing infrastructure:** Trade API integration and rate limiting can be extended.
- **Gaps to fill:** Background polling, lifecycle tracking, affix-indexed storage.

See the [data investigation report](../../governance/audits/) for current state details.
