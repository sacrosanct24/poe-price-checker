# ML Rare Item Valuation – Architecture & Implementation Roadmap

> **Living Document Notice**
>
> This document captures the output of an initial brainstorming session (December 2024). Core architectural ideas are directionally sound, but implementation details, phase sequencing, and specific decisions remain open. Treat this as a working design document, not a locked specification.

---

## Purpose

Design, implement, and validate an ML-backed rare-item valuation system that:

- Learns affix-driven value signals that are directionally consistent across leagues
- Produces a calibrated price estimate for the current league
- Surfaces comparable items (comps) for transparency and trust

This system augments (not replaces) existing pricing sources and is designed to be incremental, explainable, and testable.

## Non-Goals (MVP)

- Perfect price prediction
- Deep neural networks / end-to-end LLM pricing
- Sale-only ground truth requirement (listings are acceptable noise)

## High-Level Architecture

```
Parsed Item
   │
   ▼
ItemFeatures  ──────────────┐
   │                         │
   ▼                         ▼
Price Model (GBDT)     Vector Similarity (ANN)
   │                         │
   └─────────┬───────────────┘
             ▼
        Blended Estimate
             │
             ▼
   Price + Confidence + Drivers + Comps
```

## PoE1 vs PoE2 Considerations (Addendum)

This roadmap must support two related but potentially divergent ecosystems that now both include asynchronous trade:

- **Path of Exile 1 (PoE1):** As of Keepers of the Flame, async trade via Merchant's Tabs is live alongside legacy whisper trade.
- **Path of Exile 2 (PoE2):** Async trade is foundational and expected to evolve faster.

### Key Implications

**Async trade is now the dominant price-discovery path**

- Listings are closer to executable orders, but subject to cooldowns and race conditions.
- Lowest-price listings are more volatile and should not be treated as stable signals.

**Dual-market reality (PoE1)**

- PoE1 has two concurrent markets:
  - Async market (Merchant Tabs)
  - Legacy whisper/manual trade (especially high-end rares)
- Data ingestion and modeling must track `trade_channel` explicitly.

**Feature schema must encode async metadata**

Required fields (where available):

- `trade_channel` (async | legacy)
- `listing_created_at`
- `listing_first_visible_at`
- `last_seen_at`
- `listing_age_seconds`
- `buyer_fee_estimate` (async)

**Normalization strategy must be channel-aware**

Prices should be normalized per:

- `game_id` (poe1, poe2)
- `trade_channel`
- league age bucket

**Model strategy must account for async dynamics**

- Prefer trimmed medians, depth-weighted comps, and time-decay.
- Ranking models are more stable than raw regression in fast-moving async markets.
- Confidence scoring must penalize sparse or highly dispersed async comps.

**Activation gates are stricter under async trade**

- Require minimum live comp count (post-cooldown).
- Filter obvious undercuts/snipes (bottom X% of local cluster).
- Fall back to heuristic or legacy-only pricing when async coverage is thin.

### Required Design Rule

Everything ML-related must be parameterized by:

- `game_id`
- `trade_channel`
- `schema_version`

---

## Phase 0 — Guardrails & Contracts

### Deliverables

- `docs/ml_valuation/GOALS.md`
- `docs/ml_valuation/DATA_CONTRACT.md`
- `docs/ml_valuation/EVAL_PLAN.md`

### Decisions

- MVP item classes (recommend starting with Boots + Rings)
- Output contract:
  - `predicted_price_chaos`
  - `confidence_score`
  - `top_value_drivers[]`
  - `comps[]`

### Acceptance Criteria

- Clear definition of success metrics
- Explicit scope boundaries documented

---

## Async Listing Lifecycle (Refinement)

### Purpose

Asynchronous trade introduces cooldowns, rapid purchases, and stale visibility. To avoid poisoning comps and training data, represent listings with an explicit lifecycle.

### Listing State Model

Define a normalized listing record with a derived `listing_state`:

- **PENDING** — created but not yet visible to buyers (cooldown / propagation window)
- **LIVE** — visible and purchasable (eligible for comps)
- **STALE** — still visible but older than a recency threshold; down-weighted for comps
- **DISAPPEARED_FAST** — observed live then removed quickly (likely purchased/sniped)
- **DISAPPEARED_SLOW** — removed after a longer window (more typical sale / delist)
- **INVALID** — failed validation, bad currency, incomplete data, etc.

### Required Timestamps / Observations

Capture where possible:

- `listing_created_at` (source time)
- `listing_first_visible_at` (first observation as visible)
- `last_seen_at`
- `observed_visible_count`

Derived:

- `listing_age_seconds = now - listing_first_visible_at`
- `time_to_disappear = disappeared_at - listing_first_visible_at` (if measurable)

### Eligibility Rules

**Comps (Similarity Search)**

- Include: LIVE, optionally STALE with time-decay weighting
- Exclude: PENDING, INVALID
- Handle: DISAPPEARED_FAST as a warning signal (undercut/sniping), not a comp

**Training Labels (Supervised Model)**

- Prefer:
  - DISAPPEARED_SLOW as a proxy for "reasonable sale/delist behavior"
  - LIVE listings above the bottom-X% of the local price cluster
- Down-weight or exclude:
  - DISAPPEARED_FAST (snipes / race artifacts)
  - PENDING (not market-valid yet)

### Confidence Impacts

Confidence should penalize:

- low effective comp count after eligibility filtering
- high dispersion among eligible comps
- dominance of DISAPPEARED_FAST signals near the queried item

### Tests Required

- Unit: state derivation from timestamps + observation counts
- Integration: comps query excludes PENDING/INVALID and applies time decay
- Regression: golden fixtures for each state + expected eligibility outcomes

---

## Phase 1 — Data & Feature Layer (Foundational)

### 1.1 Canonical Item Feature Representation

**Goal:** One stable, testable representation of a rare item.

**Deliverables**

- `ml/features/item_features.py`
- `tests/unit/ml/test_item_features.py`

**Includes**

- Item metadata: class, base, ilvl, influences, flags
- Affixes: affix_id, tier, roll percentile
- Derived flags (optional, documented)

**Done When**

- Same item text always produces identical features
- Feature spec is versioned

### 1.2 Training Dataset Builder

**Goal:** Convert historical data into ML-ready datasets.

**Deliverables**

- `ml/datasets/build_training_set.py`
- `ml/datasets/schema.py`
- Output: Parquet files in `data/ml/`

**Responsibilities**

- Snapshot prices normalized to chaos
- Attach league, league age, timestamp
- Optional relative-price normalization per base

**Done When**

- Dataset builds reproducibly
- Schema validated via tests

### 1.3 Cleaning & Labeling

**Goal:** Reduce noise without hiding signal.

**Deliverables**

- `ml/datasets/cleaning.py`
- `tests/unit/ml/test_cleaning.py`

**Rules**

- Remove extreme outliers per base type
- Deduplicate identical listings
- Drop records missing critical fields

**Done When**

- Dataset statistics are stable across runs

---

## Phase 2 — Price Model (Affix Signal Learning)

### 2.1 Baseline Model (Regression)

**Model**

- Gradient Boosted Trees (LightGBM / XGBoost / CatBoost)

**Target**

`log(price_chaos)`

**Deliverables**

- `ml/models/train_gbdt.py`
- `ml/models/model_io.py`
- Saved model artifact

**Done When**

- Model trains deterministically
- Beats naive baseline (median by base)

### 2.2 League-Agnostic Affix Trend Analysis

**Goal:** Identify affixes with consistent directional value.

**Deliverables**

- `ml/analysis/affix_stability.py`
- `docs/ml_valuation/AFFIX_SIGNALS.md`

**Method**

- Pooled training with league context
- Measure sign consistency across leagues

**Done When**

- Stable positive/negative affix sets identified

### 2.3 Evaluation Harness

**Deliverables**

- `ml/eval/eval_regression.py`
- `ml/eval/slices.py`
- CI-safe smoke evaluation

**Metrics**

- RMSLE / MAE(log)
- Slice analysis by base, league age

**Done When**

- Evaluation is automated and repeatable

---

## Phase 3 — Vector Comps (Similarity Search)

### 3.1 Embedding Strategy (MVP)

**Approach**

- Deterministic numeric vectors (no LLM embeddings initially)

**Deliverables**

- `ml/vector/embedding.py`

**Done When**

- Identical items embed identically

### 3.2 ANN Index & Query API

**Deliverables**

- `ml/vector/build_index.py`
- `ml/vector/query.py`

**Capabilities**

- Hard filters (league, base, class)
- Top-K nearest comps

**Done When**

- Query latency acceptable
- Returned comps are intuitively similar

### 3.3 Blend Strategy

**Deliverables**

- `ml/inference/rare_pricer.py`
- `ml/inference/blend.py`

**Logic**

- Combine model estimate + comp median
- Weight by comp density and dispersion
- Emit confidence score

**Done When**

- Estimates degrade gracefully with sparse comps

---

## Phase 4 — Product Integration

### 4.1 Pricing Source Integration

**Deliverables**

- `data_sources/pricing/rare_affix_model.py`

**Behavior**

- Feature-flagged activation
- Limited to supported item classes

### 4.2 GUI Integration

**Deliverables**

- Rare Valuation panel

**Displays**

- Estimated price + confidence
- Top value drivers
- Comparable listings

---

## Phase 5 — Testing Strategy

### Unit Tests

- Feature extraction
- Cleaning rules
- Embedding stability
- Blend math edge cases

### Integration Tests

- End-to-end: dataset → model → inference
- ANN index build + query

### Regression Tests

- Golden items with expected price bands

---

## Phase 6 — Hardening (Post-MVP)

- Pairwise ranking model
- Multi-task league calibration
- Higher weight for recorded sales
- Better outlier detection

---

## Suggested Task Breakdown (Agent-Friendly)

### Milestone 1 — Foundations

- ItemFeatures spec + tests
- Dataset builder + cleaning

### Milestone 2 — Price Model

- GBDT training pipeline
- Evaluation harness
- Affix stability analysis

### Milestone 3 — Comps & Blending

- Embedding + ANN index
- Blend logic + confidence

### Milestone 4 — Integration

- Pricing source hookup
- GUI panel

### Milestone 5 — Validation

- Regression tests
- Calibration review

---

## Secure Weekly "Learnings" Distribution (GitHub Releases + Signature Verification)

### Goal

Enable the app to download vetted learnings (signals/config) and optional model updates so users don't repeat experiments. Updates publish on a weekly cadence and are delivered securely.

### Hosting

- GitHub Releases as the distribution channel
- One release per week (or per version bump) containing:
  - `manifest.json`
  - `manifest.sig`
  - artifacts (knowledge/model packs)
  - release notes

### Security Requirements (MVP)

**Signed updates (required)**

- Verify Ed25519 signatures in-app using a pinned public key.

**Integrity checks**

- Every artifact hashed with SHA-256 and verified after download.

**Schema compatibility gates**

- Manifest includes `schema_version` and `feature_schema_version`.
- App refuses incompatible packs.

**Rollback safety**

- Keep last-known-good pack and roll back on activation failures.

### Update Pack Layers

**Knowledge Pack (weekly, lightweight)**

- `AFFIX_SIGNALS.json` (by game_id, item_class)
- `BASELINES.json`
- `NOTES.md`

**Model Pack (optional)**

- `rare_value_gbdt_<game_id>_vX` (and/or ranking models)
- `model_manifest.json` (training window, metrics, schema)

**Comp Index Pack (optional/heavy)**

- Only if sliced and justified; otherwise rebuild locally.

### Mandatory Parameterization

All downloaded artifacts must be keyed by:

- `game_id` (poe1, poe2)
- `schema_version`
- `feature_schema_version`
- `created_at`

### Manifest Format

**manifest.json (signed)**

- `release_tag`, `created_at`
- `schema_version`, `feature_schema_version`
- `packs[]` with `name`, `game_id`, `kind`, `url`, `sha256`, `bytes`, `requires:{min_app_version}`

**manifest.sig**

- Ed25519 signature over the exact bytes of `manifest.json`

### Client Behavior

**Config:**

- `update_channel`: stable|beta|off
- `auto_update`: true|false
- `update_check_interval_hours`

**Steps:**

1. Download `manifest.json` + `manifest.sig`
2. Verify signature
3. Validate schema + compatibility
4. Download artifacts
5. Verify SHA-256
6. Install into `~/.poe_price_checker/updates/<game_id>/<release_tag>/...`
7. Atomically switch `current.json` pointer
8. Roll back if activation fails

### Publisher Pipeline (Weekly)

1. Build datasets/train (if needed)
2. Run eval + slice regressions
3. Generate knowledge pack + notes
4. Generate `manifest.json`
5. Sign → `manifest.sig`
6. Publish GitHub Release

### Acceptance Criteria

- Bad signature or hash => update is rejected
- Incompatible schema => update is rejected
- Rollback proven via integration test

---

## Final Notes

This roadmap intentionally biases toward:

- **Interpretability** over novelty
- **Incremental delivery**
- **Strong test contracts**

The system should feel trustworthy first, impressive second.
