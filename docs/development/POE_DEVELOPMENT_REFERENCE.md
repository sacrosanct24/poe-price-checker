# Path of Exile Development Reference

A comprehensive reference for developing PoE/PoE2 tools, compiled from analysis of the community ecosystem. This document captures best practices, API access patterns, and proven techniques from successful projects.

**Last Updated**: December 8, 2025
**Sources**: 20+ analyzed GitHub projects, official GGG documentation

---

## Table of Contents

1. [API Access Patterns](#api-access-patterns)
2. [Item Parsing Techniques](#item-parsing-techniques)
3. [Price Checking Architecture](#price-checking-architecture)
4. [Path of Building Integration](#path-of-building-integration)
5. [Clipboard & Hotkey Detection](#clipboard--hotkey-detection)
6. [Rate Limiting Best Practices](#rate-limiting-best-practices)
7. [Caching Strategies](#caching-strategies)
8. [Desktop Overlay Techniques](#desktop-overlay-techniques)
9. [Community Libraries](#community-libraries)
10. [Project Documentation Index](#project-documentation-index)

---

## API Access Patterns

### Official GGG APIs

#### Trade API
- **Base URL**: `https://www.pathofexile.com/api/trade`
- **Search Endpoint**: `POST /search/{league}`
- **Fetch Endpoint**: `GET /fetch/{ids}?query={queryId}`
- **Rate Limit**: 5 requests/second, check `X-Rate-Limit-*` headers

**Live Search WebSocket**:
```
wss://www.pathofexile.com/api/trade/live/{league}/{queryId}
```
- Maximum 20 simultaneous connections
- One connection per IP for third-party alternatives (poe.trade)

**Required Headers**:
```http
User-Agent: OAuth {clientId}/{version} (contact: {email})
Authorization: Bearer {access_token}  # If authenticated
```

#### Public Stash Tab API
- **Endpoint**: `GET /public-stash-tabs`
- **Required Scope**: `service:psapi`
- **5-minute delay** on all data
- Use `next_change_id` for pagination

#### OAuth 2.1 Authentication

**Client Types**:
| Type | Token Lifetime | Redirect | Use Case |
|------|---------------|----------|----------|
| Confidential | 28 days | HTTPS only | Server apps |
| Public | 10 hours | localhost OK | Desktop apps |

**PKCE Flow** (for public clients):
```python
import hashlib
import secrets
import base64

def generate_pkce():
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip('=')
    return verifier, challenge
```

### Third-Party APIs

#### poe.ninja (Primary Pricing)
- **Base URL**: `https://poe.ninja/api/data`
- **Rate Limit**: ~60 requests/minute (soft limit)
- **No authentication required**

**Endpoints**:
```
Currency:  /currencyoverview?league={league}&type=Currency
Items:     /itemoverview?league={league}&type={type}
```

**Item Types**: Oil, Incubator, Scarab, Fossil, Resonator, Essence, DivinationCard, SkillGem, BaseType, UniqueMap, Map, UniqueJewel, UniqueFlask, UniqueWeapon, UniqueArmour, UniqueAccessory, Beast

**PoE2**: Use `https://poe2.ninja/api/data` with same endpoints

#### poe.watch (Secondary/Validation)
- **Base URL**: `https://api.poe.watch`
- **No authentication required**
- **Unique features**: Historical data, enchantments, corruptions, low-confidence flags

**Key Endpoints**:
```
GET /get?league={league}&category={category}
GET /search?league={league}&q={query}
GET /history?league={league}&id={item_id}
GET /corruptions?league={league}&id={item_id}
GET /compact?league={league}  # Bulk data
```

### API Response Parsing

**Standard Item Price Object** (poe.ninja):
```json
{
  "id": 123,
  "name": "Item Name",
  "chaosValue": 420.5,
  "exaltedValue": 2.8,
  "divineValue": 2.1,
  "sparkline": {"data": [...]},
  "lowConfidenceSparkline": {"data": [...]}
}
```

**Pro Tip**: Check `lowConfidenceSparkline` presence to detect unreliable prices

---

## Item Parsing Techniques

### Clipboard Item Format

When user presses Ctrl+C on item in PoE, clipboard contains structured text:

```
Item Class: Body Armours
Rarity: Rare
Doom Salvation
Vaal Regalia
--------
Energy Shield: 387 (augmented)
--------
Requirements:
Level: 68
Int: 194
--------
Sockets: B-B-B-B-B-B
--------
Item Level: 86
--------
+46 to maximum Energy Shield
+89 to maximum Life
+45% to Cold Resistance
+38% to Lightning Resistance
8% increased maximum Energy Shield
--------
Shaper Item
```

### Parsing Strategy (From Awakened PoE Trade)

1. **Split by `--------`** - Creates sections
2. **First section** - Rarity + Name + Base Type
3. **Properties section** - Stats like ES, Armour, DPS
4. **Requirements section** - Level, Str/Dex/Int
5. **Mods section** - Implicits (before first `--------` after requirements), then Explicits
6. **Flags** - "Corrupted", "Mirrored", "Shaper Item", etc.

**Key Patterns**:
```python
RARITY_PATTERN = r"^Rarity:\s*(\w+)"
ITEM_LEVEL_PATTERN = r"Item Level:\s*(\d+)"
QUALITY_PATTERN = r"Quality:\s*\+?(\d+)%"
SOCKET_PATTERN = r"Sockets:\s*([RGB-WSA ]+)"
INFLUENCE_KEYWORDS = ["Shaper", "Elder", "Crusader", "Hunter",
                       "Redeemer", "Warlord", "Searing Exarch", "Eater of Worlds"]
```

### PoE2 Differences

- **Rune Sockets**: Separate from link sockets
- **Spirit**: New stat on items
- **Talismans**: New weapon type for shapeshifting
- **Sanctified/Unmodifiable**: New item states

### Reference Implementation

See our parser: `core/item_parser.py`

Community parsers:
- `klayveR/poe-itemtext-parser` (TypeScript)
- `PathOfExileClipboardListener` (C#)

---

## Price Checking Architecture

### Multi-Source Strategy

```
┌─────────────────────────────────────────────────────────┐
│                     Price Request                        │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  poe.ninja  │ │  poe.watch  │ │ Trade API   │
    │  (Primary)  │ │ (Secondary) │ │ (Live data) │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┴───────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Price Aggregation   │
                │ - Confidence score  │
                │ - Source weighting  │
                │ - Outlier detection │
                └─────────────────────┘
```

### Confidence Scoring (From PoE Overlay)

```python
def calculate_confidence(sources):
    """
    High confidence: 3+ sources within 10% of each other
    Medium confidence: 2 sources within 20%
    Low confidence: Single source or high variance
    """
    if len(sources) < 2:
        return "low"

    prices = [s['price'] for s in sources]
    variance = max(prices) / min(prices) - 1

    if variance < 0.1 and len(sources) >= 3:
        return "high"
    elif variance < 0.2:
        return "medium"
    return "low"
```

### Currency Conversion

**Current Ratios** (varies by league):
- PoE1: 1 Divine ≈ 150-200 Chaos
- PoE2: 1 Divine ≈ 70-100 Exalts, 1 Chaos ≈ 7 Exalts

Always fetch current rates from poe.ninja `/currencyoverview`

---

## Path of Building Integration

### PoB Code Format

PoB codes are Base64-encoded, zlib-compressed XML:

```python
import base64
import zlib

def decode_pob(code):
    """Decode a Path of Building share code."""
    # Remove URL prefix if present
    if code.startswith("https://"):
        code = code.split("/")[-1]

    # Base64 decode
    decoded = base64.urlsafe_b64decode(code + "==")

    # Decompress
    xml_string = zlib.decompress(decoded).decode('utf-8')
    return xml_string
```

### PoB XML Structure

Key elements:
```xml
<PathOfBuilding>
    <Build
        level="100"
        className="Ranger"
        ascendClassName="Deadeye"
        mainSocketGroup="1">
        <PlayerStat stat="Life" value="5234"/>
        <PlayerStat stat="Str" value="155"/>
        ...
    </Build>
    <Items>
        <Item id="1">
            Rarity: RARE
            Doom Salvation
            ...
        </Item>
    </Items>
    <Skills>
        <Skill mainActiveSkill="1" enabled="true">
            <Gem skillId="LightningArrow" level="21" quality="20"/>
        </Skill>
    </Skills>
    <Tree activeSpec="1">
        <Spec treeVersion="3_27">
            <URL>https://www.pathofexile.com/passive-skill-tree/...</URL>
        </Spec>
    </Tree>
</PathOfBuilding>
```

### PoB2 (Path of Exile 2)

- Repository: `PathOfBuildingCommunity/PathOfBuilding-PoE2`
- Same XML structure, different `treeVersion`
- Talismans handled as weapon type
- Spirit stat supported

### Item Format in PoB

Items in PoB use modified clipboard format:
```
Rarity: RARE
Item Name
Base Type
Implicits: 1
{implicit mod}
{explicit mod 1}
{explicit mod 2}
Shaper Item
```

Note: "Implicits: N" line indicates implicit count

---

## Clipboard & Hotkey Detection

### Cross-Platform Clipboard Monitoring

**Python (pyperclip + threading)**:
```python
import pyperclip
import threading

class ClipboardWatcher:
    def __init__(self, callback):
        self._callback = callback
        self._running = False
        self._last_value = ""

    def start(self):
        self._running = True
        threading.Thread(target=self._watch, daemon=True).start()

    def _watch(self):
        while self._running:
            try:
                value = pyperclip.paste()
                if value != self._last_value:
                    self._last_value = value
                    if self._is_poe_item(value):
                        self._callback(value)
            except:
                pass
            time.sleep(0.1)

    def _is_poe_item(self, text):
        return text.startswith("Item Class:") or text.startswith("Rarity:")
```

### Global Hotkey Registration

**PyQt6**:
```python
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QAbstractNativeEventFilter

# Use pynput for cross-platform global hotkeys
from pynput import keyboard

def on_hotkey():
    clipboard_text = QApplication.clipboard().text()
    process_item(clipboard_text)

# Register Ctrl+D for price check
listener = keyboard.GlobalHotKeys({
    '<ctrl>+d': on_hotkey
})
listener.start()
```

### Terms of Service Compliance

⚠️ **Important**: GGG prohibits:
- Reading game memory
- Injecting into game process
- Sending input to game

✅ **Allowed**:
- Reading clipboard (Ctrl+C is user action)
- Overlay windows
- API access
- Global hotkeys (that don't automate game input)

---

## Rate Limiting Best Practices

### Official API Headers

```python
def parse_rate_limit_headers(headers):
    """Parse GGG API rate limit headers."""
    rules = headers.get('X-Rate-Limit-Rules', '').split(',')

    limits = {}
    for rule in rules:
        key = f'X-Rate-Limit-{rule.capitalize()}'
        state_key = f'X-Rate-Limit-{rule.capitalize()}-State'

        if key in headers:
            # Format: "requests:period:timeout"
            limit = headers[key].split(':')
            state = headers[state_key].split(':')

            limits[rule] = {
                'max_requests': int(limit[0]),
                'period_seconds': int(limit[1]),
                'timeout_seconds': int(limit[2]),
                'current_requests': int(state[0]),
                'time_in_period': int(state[1]),
                'in_timeout': int(state[2]) > 0
            }

    return limits
```

### Exponential Backoff

```python
import time
import random

def exponential_backoff(attempt, base_delay=1, max_delay=60):
    """Calculate delay with jitter."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter

def fetch_with_retry(url, max_retries=4):
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 10))
                time.sleep(retry_after)
                continue
            return response
        except requests.RequestException:
            if attempt < max_retries - 1:
                time.sleep(exponential_backoff(attempt))
    return None
```

### Request Queuing

```python
from collections import deque
import threading

class RateLimitedQueue:
    def __init__(self, requests_per_second=5):
        self._queue = deque()
        self._lock = threading.Lock()
        self._min_interval = 1.0 / requests_per_second
        self._last_request = 0

    def add(self, request_func):
        with self._lock:
            now = time.time()
            wait_time = max(0, self._min_interval - (now - self._last_request))
            if wait_time > 0:
                time.sleep(wait_time)
            result = request_func()
            self._last_request = time.time()
            return result
```

---

## Caching Strategies

### Multi-Level Cache

```python
from functools import lru_cache
from datetime import datetime, timedelta
import json

class PriceCache:
    """
    L1: In-memory (lru_cache) - 5 minutes
    L2: SQLite/disk - 1 hour
    L3: API fetch - always fresh
    """

    L1_TTL = timedelta(minutes=5)
    L2_TTL = timedelta(hours=1)

    def __init__(self, db_path):
        self._db = sqlite3.connect(db_path)
        self._memory = {}
        self._memory_timestamps = {}

    def get(self, item_key, league):
        # L1: Memory
        cache_key = f"{league}:{item_key}"
        if cache_key in self._memory:
            if datetime.now() - self._memory_timestamps[cache_key] < self.L1_TTL:
                return self._memory[cache_key]

        # L2: Disk
        row = self._db.execute(
            "SELECT price, updated_at FROM price_cache WHERE key = ?",
            (cache_key,)
        ).fetchone()

        if row and datetime.now() - row[1] < self.L2_TTL:
            self._memory[cache_key] = row[0]
            self._memory_timestamps[cache_key] = datetime.now()
            return row[0]

        # L3: API
        return None  # Caller should fetch

    def set(self, item_key, league, price):
        cache_key = f"{league}:{item_key}"
        self._memory[cache_key] = price
        self._memory_timestamps[cache_key] = datetime.now()

        self._db.execute(
            "INSERT OR REPLACE INTO price_cache (key, price, updated_at) VALUES (?, ?, ?)",
            (cache_key, price, datetime.now())
        )
        self._db.commit()
```

### Cache Invalidation

- **Currency rates**: Refresh every 15-30 minutes
- **Unique prices**: Refresh every 1-6 hours
- **Rare evaluations**: Cache based on mod combination hash
- **Build data**: Cache until user refreshes

---

## Desktop Overlay Techniques

### Electron (Awakened PoE Trade)

**Architecture**:
```
main/           # Node.js main process
├── index.ts    # Entry point, window management
├── shortcuts.ts # Global hotkey registration
└── overlay.ts  # Overlay window positioning

renderer/       # Vue.js frontend
├── App.vue     # Main component
├── price-check/ # Price check UI
└── settings/   # Configuration UI
```

**Key Techniques**:
- Transparent, always-on-top window
- Click-through when not focused
- Position overlay near cursor

### PyQt6 Overlay

```python
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Frameless, transparent, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Don't steal focus
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def show_at_cursor(self):
        from PyQt6.QtGui import QCursor
        pos = QCursor.pos()
        self.move(pos.x() + 10, pos.y() + 10)
        self.show()
```

---

## Community Libraries

### JavaScript/TypeScript
| Library | Purpose | Status |
|---------|---------|--------|
| [poe-api-ts](https://github.com/moepmoep12/poe-api-ts) | Official + third-party API access | Active |
| [poe-api-wrappers](https://github.com/klayveR/poe-api-wrappers) | API wrappers | Deprecated |
| [poe-itemtext-parser](https://github.com/klayveR/poe-itemtext-parser) | Clipboard item parsing | Active |

### Python
| Library | Purpose | Status |
|---------|---------|--------|
| [pathofexile](https://github.com/willroberts/pathofexile) | API framework | Active |
| [poe-trade-parser](https://github.com/vlameiras/poe-trade-parser) | Trade site parser | Active |

### Go
| Library | Purpose | Status |
|---------|---------|--------|
| [poeapi](https://pkg.go.dev/github.com/willroberts/poeapi) | API client with caching | Active |

---

## Project Documentation Index

Our project has extensive documentation. Don't reinvent:

### API References
| Document | Contents |
|----------|----------|
| `docs/POE_API_REFERENCE.md` | Official GGG OAuth, endpoints, rate limits |
| `docs/POEWATCH_API_REFERENCE.md` | poe.watch endpoints, item structure |
| `docs/development/DATA_SOURCES_GUIDE.md` | Data source hierarchy, integration patterns |

### Implementation Guides
| Document | Contents |
|----------|----------|
| `docs/development/DEVELOPMENT_GUIDE.md` | Project setup, architecture |
| `docs/RARE_ITEM_VALUATION.md` | Rare item evaluation logic |
| `docs/features/INTEGRATION_GUIDE.md` | Component integration |

### Troubleshooting
| Document | Contents |
|----------|----------|
| `docs/troubleshooting/PARSER_ISSUES.md` | Item parsing edge cases |
| `docs/troubleshooting/ITEM_CLASS_BUG.md` | Known parsing issues |

### MCP Integration
| Document | Contents |
|----------|----------|
| `docs/mcp/SETUP_GUIDE.md` | MCP server setup |
| `docs/mcp/MCP_INTEGRATION.md` | Tool integration |

---

## Quick Reference: Common Tasks

### Get Current Divine:Chaos Ratio
```python
from data_sources.pricing.poe_ninja import PoeNinjaAPI
api = PoeNinjaAPI()
currency_data = api.get_currency_overview("Keepers")
divine = next(c for c in currency_data if c['currencyTypeName'] == 'Divine Orb')
ratio = divine['chaosEquivalent']
```

### Parse PoB Code
```python
from core.pob_integration import PoBDecoder
decoder = PoBDecoder()
build = decoder.decode(pob_code)
```

### Price Check Item
```python
from core.price_integrator import PriceIntegrator
integrator = PriceIntegrator()
result = integrator.get_integrated_price(parsed_item, "Keepers")
```

### Evaluate Rare Item
```python
from core.rare_item_evaluator import RareItemEvaluator
evaluator = RareItemEvaluator()
score = evaluator.evaluate(parsed_item)
```

---

## Sources

- [GGG Developer Docs](https://www.pathofexile.com/developer/docs)
- [poe.ninja API](https://github.com/ayberkgezer/poe.ninja-API-Document)
- [Awakened PoE Trade](https://github.com/SnosMe/awakened-poe-trade)
- [Path of Building Community](https://github.com/PathOfBuildingCommunity)
- [poe-api-ts](https://github.com/moepmoep12/poe-api-ts)
- [Exilence Next](https://github.com/viktorgullmark/exilence-next)
- [PoE Wiki](https://www.poewiki.net/)
