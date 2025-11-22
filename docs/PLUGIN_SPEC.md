Here’s a concrete, repo-ready **Plugin Interface Specification** that fits your current architecture (AppContext, MultiSourcePriceService, plugin_state table, etc.). You can drop this into `docs/PLUGIN_SPEC.md` or append to `DEVELOPMENT_GUIDE.md`.

---

# PoE Price Checker – Plugin Interface Specification

*Last updated: 2025-11-22*

## 1. Goals

The plugin system lets third-party code extend PoE Price Checker without modifying the core:

* Add **new pricing sources** (e.g., alternate APIs, static spreadsheets, personal price models).
* Add **post-parse item hooks** (e.g., tagging, alerts, custom value rules).
* Optionally add **post-pricing hooks** (e.g., logging, analytics).

Design constraints:

* **Simple:** pure Python modules in a `plugins/` folder.
* **Safe:** no direct DB fiddling; plugins interact through well-defined interfaces.
* **Declarative:** plugins declare capabilities via a registration function.
* **Configurable:** per-plugin config/state persisted in the `plugin_state` table.

---

## 2. Plugin Discovery Rules

### 2.1 Plugin Locations

* All first-party and user plugins live in the `plugins/` package.
* Recommended structure:

```text
poe_price_checker/
    core/
    data_sources/
    gui/
    plugins/
        __init__.py
        examples/
            __init__.py
            my_first_plugin.py
        my_custom_pricing_plugin.py
        my_item_tagging_plugin.py
```

### 2.2 Discovery Algorithm

At startup, **AppContext** (or a dedicated `core/plugins.py`) will:

1. Import the `poe_price_checker.plugins` package.
2. Recursively scan for submodules using `pkgutil.iter_modules` or similar.
3. For each module:

   * Import it.
   * Check for a top-level function `register_plugin(...)`.
   * If found, call it.

Pseudo-code:

```python
# core/plugins.py

import importlib
import logging
import pkgutil
from types import ModuleType
from typing import Callable

from poe_price_checker.core.app_context import AppContext

LOG = logging.getLogger(__name__)

RegisterFn = Callable[['PluginRegistry', 'AppContext'], None]


def discover_and_register_plugins(app_context: AppContext, registry: 'PluginRegistry') -> None:
    import poe_price_checker.plugins as plugins_pkg

    for finder, name, ispkg in pkgutil.walk_packages(plugins_pkg.__path__, plugins_pkg.__name__ + "."):
        try:
            module = importlib.import_module(name)
        except Exception:
            LOG.exception("Failed to import plugin module %s", name)
            continue

        register: RegisterFn | None = getattr(module, "register_plugin", None)
        if register is None:
            continue

        try:
            LOG.info("Registering plugin from module %s", name)
            register(registry, app_context)
        except Exception:
            LOG.exception("Plugin registration failed for module %s", name)
```

### 2.3 Module-Level Metadata (Optional but Recommended)

Plugins may define these module-level constants:

```python
PLUGIN_ID = "my_custom_pricing"
PLUGIN_NAME = "My Custom Pricing Source"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Uses my personal spreadsheet for pricing."
```

They are **not required** for discovery, but are used for:

* Display in plugin management UI.
* Versioned config handling.
* Debug logging.

---

## 3. Core Interfaces

We introduce three core interfaces:

1. `PluginRegistry` – **what the core exposes to plugins**.
2. `PricingSource` – a **new pricing source** implementation.
3. `ItemHook` – a **post-parse / post-price hook**.

These live under `core/plugins.py` (or `core/plugin_api.py`).

### 3.1 Types Used by Plugins

The plugin API is built on types you already have or can easily add:

* `AppContext` – the root dependency container.
* `ParsedItem` – output of `ItemParser`.
* `PricingContext` – small struct describing league, game version, and config.
* `PriceQuote` – normalized price result.

Example definitions (spec-level; adjust to match actual code):

```python
# core/plugin_api.py (new file, or inside core/plugins.py)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from poe_price_checker.core.item_parser import ParsedItem
from poe_price_checker.core.game_version import GameVersion


@dataclass(slots=True)
class PricingContext:
    league: str
    game_version: GameVersion
    # Convenience for plugins:
    config: Any            # core.config.Config
    app_context: Any       # core.app_context.AppContext


@dataclass(slots=True)
class PriceQuote:
    source_id: str           # e.g. "poe_ninja", "my_custom_pricing"
    source_name: str         # Human-friendly name

    item_name: str
    base_type: str | None

    chaos_value: float       # Normalized to chaos
    currency: str | None     # Optional, if plugin is in non-chaos terms

    details: str | None = None     # Optional long text
    trade_url: str | None = None   # Optional trade link
```

> Note: `ParsedItem` already exists; `GameVersion` exists. `PricingContext` and `PriceQuote` are new glue types.

---

## 4. PluginRegistry Interface

`PluginRegistry` is how plugins register capabilities and access config.

```python
# core/plugin_api.py (or core/plugins.py)

from __future__ import annotations

from typing import Protocol, Any, Iterable


class PricingSource(Protocol):
    """
    A pricing source produces one or more PriceQuote objects for a parsed item.
    """
    id: str                # stable identifier, e.g., "my_custom_pricing"
    display_name: str      # user-friendly name

    def get_quotes(self, item: ParsedItem, ctx: PricingContext) -> list[PriceQuote]:
        """
        Return a list of price quotes for this item in the given context.
        Should be fast enough to be called on the GUI thread or else manage its own async.
        """
        ...


class ItemHook(Protocol):
    """
    A hook that runs after an item is parsed,
    and optionally after pricing is performed.
    """

    id: str
    description: str

    def on_item_parsed(self, item: ParsedItem, ctx: PricingContext) -> None:
        """
        Called after the item is successfully parsed, before pricing.

        Can mutate the ParsedItem (e.g., adding tags) or attach metadata
        via app_context/database if needed.
        """
        ...

    def on_pricing_completed(
        self,
        item: ParsedItem,
        ctx: PricingContext,
        quotes: list[PriceQuote],
    ) -> None:
        """
        Called after all pricing sources have run for this item.

        Can be used for logging, analytics, alerts, etc.
        """
        ...


class PluginConfigStore(Protocol):
    """
    Abstracts access to the underlying plugin_state table.
    Plugins should use this interface instead of hitting DB directly.
    """
    def load_config(self, plugin_id: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        ...

    def save_config(self, plugin_id: str, config: dict[str, Any]) -> None:
        ...


class PluginRegistry(Protocol):
    """
    Interface exposed by the core to plugins during registration.
    """
    config_store: PluginConfigStore

    def register_pricing_source(self, source: PricingSource) -> None:
        """
        Register a new pricing source. It will appear in the MultiSourcePriceService.
        """
        ...

    def register_item_hook(self, hook: ItemHook) -> None:
        """
        Register a new item hook for parse and pricing events.
        """
        ...

    def get_registered_pricing_sources(self) -> Iterable[PricingSource]:
        ...
```

---

## 5. Plugin Registration Function

Every plugin module that wants to participate must define:

```python
def register_plugin(registry: PluginRegistry, app_context: AppContext) -> None:
    ...
```

This function:

* Creates plugin objects (pricing sources, hooks).
* Registers them via the `registry`.

Example skeleton:

```python
# plugins/my_custom_pricing_plugin.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from poe_price_checker.core.plugin_api import (
    PricingSource,
    PriceQuote,
    PricingContext,
    ParsedItem,
    PluginRegistry,
)
from poe_price_checker.core.app_context import AppContext

PLUGIN_ID = "my_custom_pricing"
PLUGIN_NAME = "My Custom Pricing Source"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Example plugin that returns a fixed value for testing."


@dataclass(slots=True)
class MyCustomPricingSource:
    id: str = PLUGIN_ID
    display_name: str = PLUGIN_NAME

    def get_quotes(self, item: ParsedItem, ctx: PricingContext) -> List[PriceQuote]:
        # In reality, you might:
        # - look up item.base_type in a local CSV
        # - hit an external API
        # - use a personal pricing formula
        chaos_value = 42.0

        return [
            PriceQuote(
                source_id=self.id,
                source_name=self.display_name,
                item_name=item.name,
                base_type=item.base_type,
                chaos_value=chaos_value,
                currency="chaos",
                details="Example plugin always returns 42c.",
                trade_url=None,
            )
        ]


def register_plugin(registry: PluginRegistry, app_context: AppContext) -> None:
    """
    Entry point called by the core at startup.
    """
    source = MyCustomPricingSource()
    registry.register_pricing_source(source)

    # Optional: use config store
    config = registry.config_store.load_config(PLUGIN_ID, default={"enabled": True})
    if not config.get("enabled", True):
        # If disabled, you could choose not to register at all
        return
```

---

## 6. How Core Uses Registered Plugins

### 6.1 MultiSourcePriceService Integration

`MultiSourcePriceService` (or equivalent) will be extended to:

* Hold a list of `PricingSource` implementations from:

  * Core (PoE Ninja, built-in undercut source).
  * Plugins.

Pseudo-flow:

```python
class MultiSourcePriceService:
    def __init__(self, ..., plugin_registry: PluginRegistry):
        self._core_sources = [poe_ninja_source, undercut_source]
        self._plugin_sources = list(plugin_registry.get_registered_pricing_sources())

    def get_prices_for_item(self, item_text: str, ctx: PricingContext) -> list[PriceQuote]:
        item = self._item_parser.parse(item_text)
        quotes: list[PriceQuote] = []

        # Run hooks: on_item_parsed
        for hook in self._plugin_hooks:
            hook.on_item_parsed(item, ctx)

        # Core sources
        for source in self._core_sources:
            quotes.extend(source.get_quotes(item, ctx))

        # Plugin sources
        for source in self._plugin_sources:
            quotes.extend(source.get_quotes(item, ctx))

        # Run hooks: on_pricing_completed
        for hook in self._plugin_hooks:
            hook.on_pricing_completed(item, ctx, quotes)

        # ... existing sorting/aggregation logic ...
        return quotes
```

### 6.2 PluginConfigStore and `plugin_state` Table

`PluginConfigStore` will be a thin wrapper around the existing `plugin_state` table in `core/database.py`.

Possible concrete implementation:

```python
# core/plugin_config_store.py

from __future__ import annotations

import json
from typing import Any

from poe_price_checker.core.database import Database


class SQLitePluginConfigStore:
    def __init__(self, db: Database) -> None:
        self._db = db

    def load_config(self, plugin_id: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        row = self._db.get_plugin_state(plugin_id)  # hypothetical DB method
        if row is None or not row.get("config_json"):
            return default or {}
        try:
            return json.loads(row["config_json"])
        except json.JSONDecodeError:
            return default or {}

    def save_config(self, plugin_id: str, config: dict[str, Any]) -> None:
        payload = json.dumps(config)
        self._db.upsert_plugin_state(plugin_id, payload)  # hypothetical DB method
```

Plugins **must not** touch the DB directly; they should always go through `PluginConfigStore`.

---

## 7. Minimal “Hello World” Plugin Examples

### 7.1 Pricing Source Only

```python
# plugins/examples/hello_pricing.py

from dataclasses import dataclass

from poe_price_checker.core.plugin_api import (
    PricingSource,
    PriceQuote,
    PricingContext,
    ParsedItem,
    PluginRegistry,
)
from poe_price_checker.core.app_context import AppContext

PLUGIN_ID = "hello_pricing"
PLUGIN_NAME = "Hello Pricing"


@dataclass(slots=True)
class HelloPricingSource:
    id: str = PLUGIN_ID
    display_name: str = PLUGIN_NAME

    def get_quotes(self, item: ParsedItem, ctx: PricingContext) -> list[PriceQuote]:
        return [
            PriceQuote(
                source_id=self.id,
                source_name=self.display_name,
                item_name=item.name,
                base_type=item.base_type,
                chaos_value=1.0,
                currency="chaos",
                details="Always 1c, for testing.",
            )
        ]


def register_plugin(registry: PluginRegistry, app_context: AppContext) -> None:
    registry.register_pricing_source(HelloPricingSource())
```

### 7.2 Item Hook Only

```python
# plugins/examples/hello_hook.py

from dataclasses import dataclass

from poe_price_checker.core.plugin_api import (
    ItemHook,
    ParsedItem,
    PricingContext,
    PluginRegistry,
)
from poe_price_checker.core.app_context import AppContext

PLUGIN_ID = "hello_hook"


@dataclass(slots=True)
class HelloHook:
    id: str = PLUGIN_ID
    description: str = "Logs item names after parsing."

    def on_item_parsed(self, item: ParsedItem, ctx: PricingContext) -> None:
        ctx.app_context.logger.info("[hello_hook] Parsed item: %s", item.name)

    def on_pricing_completed(self, item: ParsedItem, ctx: PricingContext, quotes):
        ctx.app_context.logger.info("[hello_hook] Got %d quotes.", len(quotes))


def register_plugin(registry: PluginRegistry, app_context: AppContext) -> None:
    registry.register_item_hook(HelloHook())
```

---
