# ADR-003: Multi-Source Price Aggregation

## Status
Accepted

## Context

Path of Exile items can be priced through multiple sources:
- **PoE Ninja**: Aggregated economy data, great for unique items
- **poe.watch**: Alternative aggregation with different methodology
- **Official Trade API**: Live listings, best for rare items
- **User database**: Historical prices from past checks

Each source has strengths and weaknesses:
- PoE Ninja may lag behind market changes
- Trade API has rate limits
- poe.watch may have different item coverage
- User data reflects actual sale prices but limited sample size

Relying on a single source gave inconsistent results.

## Decision

Implement a multi-source pricing system with three layers:

1. **Pricing Source Adapters** (`data_sources/pricing/`)
   - Each source implements `BasePricingSource` interface
   - Handles API calls, rate limiting, caching
   - Returns normalized `PriceResult` objects

2. **Price Integrator** (`core/price_integrator.py`)
   - Queries multiple sources in parallel
   - Combines results with configurable weights
   - Handles source failures gracefully

3. **Price Arbitration** (`core/price_arbitration.py`)
   - Selects "best" price from multiple sources
   - Configurable arbitration strategies:
     - Lowest price (for buyers)
     - Median (most stable)
     - Weighted average (confidence-based)

```python
class PriceIntegrator:
    def get_price(self, item: ParsedItem) -> IntegratedPrice:
        results = self._query_sources_parallel(item)
        return self._arbitrate(results)
```

## Consequences

### Positive
- **More accurate prices**: Multiple sources reduce outlier impact
- **Redundancy**: One source down doesn't break pricing
- **Flexibility**: Users can configure preferred sources
- **Transparency**: Show price from each source in UI

### Negative
- **Complexity**: More code to maintain
- **Latency**: Multiple API calls (mitigated by parallel requests)
- **Disagreement**: Sources may give very different prices (shows as range)

### Neutral
- Source weights stored in user config
- Failed sources logged but don't block results

## References
- `core/price_integrator.py`
- `core/price_arbitration.py`
- `data_sources/pricing/`
- `docs/MULTI_SOURCE_PRICING.md`
