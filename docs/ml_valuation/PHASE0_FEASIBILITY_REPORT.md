# Phase 0 Feasibility Gate Report

Date: 2026-01-16T03:49:08Z
Status: BLOCKED (insufficient data window and missing affix data)

## Gate Criteria

- 2 weeks of collection for target base types
- 3+ known-valuable affixes show statistically significant positive price correlation (p < 0.05)

## Data Coverage

- Collection runs recorded: 650 (last run 2026-01-10T05:42:47+00:00, errors=10)
- Listings in `ml_listings`: 1106
- First seen: 2025-12-25T03:51:17+00:00
- Last seen: 2025-12-25T04:01:20+00:00
- Coverage window: 0:10:03
- Listing states: DISAPPEARED_FAST (1106)

## Base Types Collected

| Base type | Count | Median price (chaos) |
| --- | --- | --- |
| Amethyst Ring | 153 | 1.0 |
| Diamond Ring | 129 | 1.0 |
| Dragonscale Boots | 107 | 3.0 |
| Prismatic Ring | 115 | 3.0 |
| Slink Boots | 98 | 5.0 |
| Sorcerer Boots | 105 | 5.0 |
| Titan Greaves | 110 | 3.0 |
| Two-Stone Ring | 79 | 1.0 |
| Two-Toned Boots | 100 | 10.0 |
| Vermillion Ring | 110 | 15.0 |

## Affix Data Availability

- Non-empty affix rows: 0 / 1106
- `data/mods.db` contained 0 mods at evaluation time
- Result: affix signal sanity check cannot be computed

## Baseline Model (Median by base type)

- MAE: 2.53
- RMSLE: 0.488
- Notes: computed on all `ml_listings` for the base types above

## Decision

FAIL / BLOCKED. The collection window is far below the 2-week minimum and the
affix data needed for the signal sanity check is missing.

## Remediation Status

- 2026-01-16T03:54:37Z: Mod database updated (24072 mods for league Keepers).
- 2026-01-16T03:54:37Z: ML collector restarted after thread-safety fix.

## Required Actions to Re-run Gate

1. Re-run data collection for 2+ weeks with boots/rings base types.
2. Re-run signal sanity check and document p-values.
