# How to See Multi-Source Pricing in Action

Your PoE Price Checker now uses **two pricing sources** (poe.ninja + poe.watch) to validate prices and provide confidence levels!

---

## 🚀 Quick Test

### Option 1: Run the Test Script

```bash
python simple_runtime_test.py
```

This will:
1. Initialize both APIs
2. Look up Divine Orb pricing
3. Show you both prices
4. Display the validation decision
5. Show you exactly what logs to look for

### Option 2: Use the Main App

```bash
python poe_price_checker.py
```

Then:
1. Copy a currency item (like Divine Orb) from PoE
2. Paste it into the app
3. Check the logs in your terminal
4. Look for `[MULTI-SOURCE]` messages

---

## 📋 What to Look For

### In the Logs

When you check an item, you'll see:

```
INFO:[MULTI-SOURCE] Looking up price for 'Divine Orb' (rarity: CURRENCY)
INFO:[MULTI-SOURCE] Available sources: poe.ninja=True, poe.watch=True
INFO:[MULTI-SOURCE] Querying poe.ninja...
INFO:[MULTI-SOURCE]   poe.ninja result: 150.8c (count: 0)
INFO:[MULTI-SOURCE] Querying poe.watch...
INFO:[poe.watch] API Request #1: search (params: {'league': 'Keepers', 'q': 'Divine Orb'})
INFO:[poe.watch] Using first result for 'Divine Orb': 157.32c
INFO:[MULTI-SOURCE]   poe.watch result: 157.3c (daily: 1948, confidence: high)
INFO:[MULTI-SOURCE] Making pricing decision...
INFO:[MULTI-SOURCE] Both sources available - price difference: 4.1%
INFO:[MULTI-SOURCE] ✓ Decision: Using poe.ninja 150.8c (validated by poe.watch, high confidence)
```

### In the GUI Results

The **Source** column will show:
- `poe.ninja (validated by poe.watch)` - Both agree (high confidence)
- `averaged (ninja: 150c, watch: 160c)` - Prices diverged, averaged
- `poe.ninja (poe.watch: low confidence)` - watch flagged as unreliable
- `poe.ninja only` - Only ninja available
- `poe.watch only` - Only watch available

---

## 🎯 Test Different Scenarios

### Scenario 1: Both Sources Agree (High Confidence)

**Test with:** Divine Orb, Exalted Orb, Mirror of Kalandra

**Expected:**
```
poe.ninja:  150.8c
poe.watch:  157.3c
Difference: 4.1%
Decision:   Using poe.ninja (validated by poe.watch) - HIGH CONFIDENCE
```

### Scenario 2: Sources Diverge (Medium Confidence)

**Test with:** Obscure unique items or niche gems

**Expected:**
```
poe.ninja:  100.0c
poe.watch:  150.0c
Difference: 33%
Decision:   Using average 125.0c - MEDIUM CONFIDENCE
```

### Scenario 3: One Source Only

**Test with:** Very new items (current league uniques)

**Expected:**
```
poe.ninja:  80.0c
poe.watch:  No data
Decision:   Using poe.ninja only - MEDIUM CONFIDENCE
```

### Scenario 4: Low Confidence Flag

**Test with:** Rarely traded items

**Expected:**
```
poe.ninja:  50.0c
poe.watch:  45.0c (flagged low confidence)
Decision:   Using poe.ninja (poe.watch: low confidence) - MEDIUM CONFIDENCE
```

---

## 🔍 Understanding Confidence Levels

### HIGH Confidence
- Both sources available
- Prices agree (within 20%)
- poe.watch has good data (not flagged)
- **You can trust this price**

### MEDIUM Confidence
- Only one source available, OR
- Prices diverge 20-50%, OR
- poe.watch flagged as low confidence
- **Price is likely correct but be cautious**

### LOW Confidence
- Both sources flag as unreliable
- Very few listings
- **Double-check before buying/selling**

---

## 🛠️ Debugging / Troubleshooting

### If You Don't See Multi-Source Logs

**Problem:** Logs only show poe.ninja, no poe.watch

**Cause:** poe.watch might not have initialized

**Check:**
```bash
python -c "from core.app_context import create_app_context; ctx = create_app_context(); print(f'poe.watch available: {ctx.poe_watch is not None}')"
```

**Expected:** `poe.watch available: True`

### If poe.watch Fails to Initialize

**Symptoms:**
```
WARNING: Failed to initialize poe.watch API; continuing with poe.ninja only
```

**Possible Causes:**
1. Network issue (can't reach api.poe.watch)
2. API is down
3. League name is invalid

**Solution:**
- Check your internet connection
- Verify league name in config: `config.json` → `games.poe1.league`
- Try Standard league if current league fails

### If Prices Look Wrong

**Check the logs:**
- Are both APIs being queried? ✓
- What prices are each returning?
- What's the decision logic saying?

**Compare manually:**
- Check poe.ninja: https://poe.ninja/
- Check poe.watch: https://poe.watch/
- See if they match what the app shows

---

## 📊 Performance Tips

### First Check (Slow)
- Both APIs queried over network
- Takes ~500ms
- Normal behavior

### Second Check (Fast)
- Results cached for 1 hour
- Takes ~1ms
- Much faster!

### Clear Cache
If you need fresh data:
```bash
# Restart the app
python poe_price_checker.py
```

Cache automatically expires after 1 hour.

---

## 🎨 GUI Enhancements (Future)

Currently, multi-source validation is visible in:
- ✅ Source column (shows validation status)
- ✅ Logs (detailed decision reasoning)

Future enhancements could add:
- 🎯 Confidence indicator (color or icon)
- 📈 Price history chart (using poe.watch 1800-day history)
- ⚡ Price divergence warning
- 🎭 Show both prices side-by-side

---

## 📖 Learn More

### Documentation
- `RUNTIME_VERIFICATION_COMPLETE.md` - Full verification report
- `docs/POEWATCH_INTEGRATION_SUMMARY.md` - Integration guide
- `docs/POEWATCH_API_REFERENCE.md` - API details

### Code
- `core/price_service.py` - Multi-source logic
- `data_sources/pricing/poe_watch.py` - API client

### Tests
- `simple_runtime_test.py` - Quick test
- `tests/test_price_service_multi_source.py` - Unit tests

---

## 💡 Pro Tips

### 1. Watch the Logs
Enable verbose logging to see everything:
```bash
python poe_price_checker.py --log-level DEBUG
```

### 2. Check Request Counts
Monitor API usage:
```python
from core.app_context import create_app_context

ctx = create_app_context()
print(f"poe.watch requests: {ctx.poe_watch.request_count}")
print(f"Cache size: {ctx.poe_watch.get_cache_size()}")
```

### 3. Test Edge Cases
Try items that might be tricky:
- Very cheap items (<1c)
- Very expensive items (>1000c)
- Newly released uniques
- Corrupted gems with quality

### 4. Compare Results
Cross-check a few items manually:
1. Check in app
2. Check on poe.ninja website
3. Check on poe.watch website
4. Verify they all agree

---

## ✅ Success Checklist

When testing, you should see:

- [x] App starts successfully
- [x] Both APIs initialized (check logs)
- [x] `[MULTI-SOURCE]` appears in logs
- [x] Both poe.ninja and poe.watch queried
- [x] Price comparison shown
- [x] Decision logged with reasoning
- [x] Confidence level displayed
- [x] Source column shows validation status
- [x] Request count increases
- [x] Cache size increases

If all checkboxes ✅, it's working perfectly!

---

## 🎉 Enjoy!

You now have **dual-source price validation** with confidence levels!

This means:
- ✅ More reliable prices
- ✅ Better confidence in valuations
- ✅ Protection against data errors
- ✅ Access to historical data
- ✅ Enchantment and corruption pricing

Happy trading, Exile! 🏹

---

**Questions?**
Check the docs or run `python simple_runtime_test.py` to see it in action!
