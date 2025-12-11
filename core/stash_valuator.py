"""
Stash Valuation Module.

Prices items from stash tabs using multiple pricing sources:
- poe.ninja for bulk items (currency, uniques, maps, etc.)
- poeprices.info for rare items

Provides sorted, filterable results for the Stash Viewer window.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.item_parser import ParsedItem
from core.rare_evaluation import RareItemEvaluator
from data_sources.poe_ninja_client import (
    NinjaPriceDatabase,
    get_ninja_client,
)
from data_sources.poe_stash_api import (
    PoEStashClient,
    StashSnapshot,
    StashTab,
)

logger = logging.getLogger(__name__)


class PriceSource(Enum):
    """Source of price data."""
    POE_NINJA = "poe.ninja"
    POE_PRICES = "poeprices.info"
    RARE_EVALUATED = "rare_eval"  # RareItemEvaluator score-based estimation
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass
class PricedItem:
    """An item with pricing information."""
    # Item data from stash API
    name: str
    type_line: str
    base_type: str
    item_class: str
    stack_size: int = 1
    ilvl: int = 0
    rarity: str = "Normal"
    identified: bool = True
    corrupted: bool = False
    links: int = 0
    sockets: str = ""
    icon: str = ""
    raw_item: Dict[str, Any] = field(default_factory=dict)

    # Pricing
    unit_price: float = 0.0
    total_price: float = 0.0
    price_source: PriceSource = PriceSource.UNKNOWN
    confidence: str = ""  # For poeprices.info
    price_min: float = 0.0
    price_max: float = 0.0

    # Rare item evaluation data (populated when price_source == RARE_EVALUATED)
    eval_score: int = 0  # Total score from RareItemEvaluator
    eval_tier: str = ""  # Tier: "excellent", "good", "decent", "low", etc.
    eval_summary: str = ""  # Brief explanation for tooltip/display

    # Tab info
    tab_name: str = ""
    tab_index: int = 0
    x: int = 0
    y: int = 0

    @property
    def display_name(self) -> str:
        """Get display name (name or typeLine)."""
        if self.name and self.name != self.type_line:
            return f"{self.name} {self.type_line}"
        return self.type_line or self.name

    @property
    def display_price(self) -> str:
        """Format price for display."""
        if self.total_price >= 100:
            return f"{self.total_price:.0f}c"
        elif self.total_price >= 1:
            return f"{self.total_price:.1f}c"
        elif self.total_price > 0:
            return f"{self.total_price:.2f}c"
        # For evaluated rares without market price, show tier
        if self.price_source == PriceSource.RARE_EVALUATED and self.eval_tier:
            return f"[{self.eval_tier}]"
        return "?"

    @property
    def is_valuable(self) -> bool:
        """Check if item has significant value."""
        if self.total_price >= 1.0:
            return True
        # Evaluated rares with good scores are also valuable
        if self.price_source == PriceSource.RARE_EVALUATED:
            return self.eval_tier in ("excellent", "good")
        return False


@dataclass
class PricedTab:
    """A stash tab with priced items."""
    id: str
    name: str
    index: int
    tab_type: str
    items: List[PricedItem] = field(default_factory=list)
    total_value: float = 0.0
    valuable_count: int = 0

    @property
    def display_value(self) -> str:
        """Format total value for display."""
        if self.total_value >= 1000:
            return f"{self.total_value/1000:.1f}k c"
        elif self.total_value >= 100:
            return f"{self.total_value:.0f}c"
        elif self.total_value >= 1:
            return f"{self.total_value:.1f}c"
        return f"{self.total_value:.2f}c"


@dataclass
class ValuationResult:
    """Result of stash valuation."""
    league: str
    account_name: str
    tabs: List[PricedTab] = field(default_factory=list)
    total_value: float = 0.0
    total_items: int = 0
    priced_items: int = 0
    unpriced_items: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def display_total(self) -> str:
        """Format total value for display."""
        if self.total_value >= 1000:
            return f"{self.total_value/1000:.1f}k c"
        return f"{self.total_value:.0f}c"


class StashValuator:
    """
    Prices items from stash tabs.

    Uses poe.ninja for bulk items and can integrate with
    poeprices.info for rares.
    """

    # Item class to ninja category mapping
    NINJA_CATEGORIES = {
        "currency": "currency",
        "stackablecurrency": "currency",
        "divinationcards": "div_cards",
        "divination card": "div_cards",
        "maps": "maps",
        "map": "maps",
        "unique": "uniques",
        "gem": "skill_gems",
        "jewel": "uniques",
        "flask": "uniques",
        "scarab": "scarabs",
        "essence": "essences",
        "oil": "oils",
        "fossil": "fossils",
        "resonator": "resonators",
        "incubator": "incubators",
        "fragment": "fragments",
        "beast": "beasts",
    }

    def __init__(self, evaluate_rares: bool = True):
        """
        Initialize stash valuator.

        Args:
            evaluate_rares: If True, use RareItemEvaluator for unpriced rare items
        """
        self.ninja_client = get_ninja_client()
        self.price_db: Optional[NinjaPriceDatabase] = None
        self._current_league: str = ""
        self._evaluate_rares = evaluate_rares
        self._rare_evaluator: Optional[RareItemEvaluator] = None

    def _get_rare_evaluator(self) -> RareItemEvaluator:
        """Lazy-load the rare item evaluator."""
        if self._rare_evaluator is None:
            self._rare_evaluator = RareItemEvaluator()
        return self._rare_evaluator

    def load_prices(
        self,
        league: str,
        progress_callback: Optional[Callable[[int, int, str], Any]] = None
    ) -> None:
        """
        Load prices from poe.ninja for a league.

        Args:
            league: League name
            progress_callback: Optional callback(current, total, type_name)
        """
        if self.price_db and self._current_league == league:
            logger.info(f"Using cached prices for {league}")
            return

        logger.info(f"Loading poe.ninja prices for {league}...")
        self.price_db = self.ninja_client.build_price_database(
            league,
            progress_callback=progress_callback
        )
        self._current_league = league
        logger.info(f"Loaded prices for {league}")

    def _classify_item(self, item: Dict[str, Any]) -> str:
        """Determine item category for pricing."""
        frame_type = item.get("frameType", 0)
        type_line = item.get("typeLine", "").lower()
        _base_type = item.get("baseType", "").lower()  # Reserved for future classification
        icon = item.get("icon", "").lower()

        # Currency/stackable
        if frame_type == 5:  # Currency
            return "currency"

        # Divination cards
        if frame_type == 6:
            return "divination card"

        # Maps
        if "map" in icon or item.get("properties", []):
            for prop in item.get("properties", []):
                if prop.get("name") == "Map Tier":
                    return "map"

        # Unique items
        if frame_type == 3:  # Unique
            return "unique"

        # Gems
        if frame_type == 4:  # Gem
            return "gem"

        # Scarabs
        if "scarab" in type_line:
            return "scarab"

        # Essences
        if type_line.startswith("essence of") or type_line.startswith("deafening essence"):
            return "essence"

        # Oils
        if "oil" in type_line and "oiled" not in type_line:
            return "oil"

        # Fossils
        if "fossil" in type_line:
            return "fossil"

        # Resonators
        if "resonator" in type_line:
            return "resonator"

        # Fragments
        if "fragment" in type_line or "splinter" in type_line:
            return "fragment"

        # Rares
        if frame_type == 2:  # Rare
            return "rare"

        # Magic
        if frame_type == 1:
            return "magic"

        return "normal"

    def _get_item_links(self, item: Dict[str, Any]) -> int:
        """Get number of links for an item."""
        sockets = item.get("sockets", [])
        if not sockets:
            return 0

        # Count max linked group
        groups: Dict[int, int] = {}
        for s in sockets:
            group = s.get("group", 0)
            groups[group] = groups.get(group, 0) + 1

        return max(groups.values()) if groups else 0

    def _price_item(self, item: Dict[str, Any], tab: StashTab) -> PricedItem:
        """Price a single item."""
        name = item.get("name", "").replace("<<set:MS>><<set:M>><<set:S>>", "")
        type_line = item.get("typeLine", "")
        base_type = item.get("baseType", type_line)
        stack_size = item.get("stackSize", 1)
        frame_type = item.get("frameType", 0)
        links = self._get_item_links(item)

        # Build socket string
        sockets = item.get("sockets", [])
        socket_str = ""
        if sockets:
            groups: Dict[int, List[str]] = {}
            for s in sockets:
                g = s.get("group", 0)
                if g not in groups:
                    groups[g] = []
                groups[g].append(s.get("sColour", "?")[0])
            socket_str = "-".join("".join(g) for g in groups.values())

        # Classify and price
        item_class = self._classify_item(item)
        unit_price = 0.0
        price_source = PriceSource.UNKNOWN

        # Try poe.ninja pricing
        if self.price_db:
            # Build lookup name
            lookup_name = type_line.lower()
            if name and frame_type == 3:  # Unique - use name
                lookup_name = name.lower()
            elif frame_type == 6:  # Div card
                lookup_name = type_line.lower()

            # Try to find price
            ninja_price = self.price_db.get_price(lookup_name, item_class)

            # For uniques, also try with base type
            if not ninja_price and name and frame_type == 3:
                ninja_price = self.price_db.get_price(f"{name.lower()} {base_type.lower()}")

            if ninja_price:
                unit_price = ninja_price.chaos_value
                price_source = PriceSource.POE_NINJA

        # Calculate total price
        total_price = unit_price * stack_size

        # Determine rarity string
        rarity_map = {0: "Normal", 1: "Magic", 2: "Rare", 3: "Unique", 4: "Gem", 5: "Currency", 6: "Divination"}
        rarity = rarity_map.get(frame_type, "Unknown")

        # For unpriced rare items, run evaluation
        eval_score = 0
        eval_tier = ""
        eval_summary = ""

        if (
            price_source == PriceSource.UNKNOWN
            and item_class == "rare"
            and self._evaluate_rares
            and item.get("identified", True)  # Only evaluate identified items
        ):
            try:
                parsed_item = ParsedItem.from_stash_item(item)
                evaluator = self._get_rare_evaluator()
                evaluation = evaluator.evaluate(parsed_item)

                eval_score = evaluation.total_score
                eval_tier = evaluation.tier
                eval_summary = evaluator.get_summary(evaluation)
                price_source = PriceSource.RARE_EVALUATED

                logger.debug(
                    "Evaluated rare '%s': score=%d, tier=%s",
                    type_line, eval_score, eval_tier
                )
            except Exception as e:
                logger.warning("Failed to evaluate rare item '%s': %s", type_line, e)

        return PricedItem(
            name=name,
            type_line=type_line,
            base_type=base_type,
            item_class=item_class,
            stack_size=stack_size,
            ilvl=item.get("ilvl", 0),
            rarity=rarity,
            identified=item.get("identified", True),
            corrupted=item.get("corrupted", False),
            links=links,
            sockets=socket_str,
            icon=item.get("icon", ""),
            raw_item=item,
            unit_price=unit_price,
            total_price=total_price,
            price_source=price_source,
            eval_score=eval_score,
            eval_tier=eval_tier,
            eval_summary=eval_summary,
            tab_name=tab.name,
            tab_index=tab.index,
            x=item.get("x", 0),
            y=item.get("y", 0),
        )

    def valuate_tab(self, tab: StashTab) -> PricedTab:
        """
        Price all items in a stash tab.

        Args:
            tab: StashTab to price

        Returns:
            PricedTab with all priced items
        """
        items = []
        total_value = 0.0
        valuable_count = 0

        for item_data in tab.items:
            priced = self._price_item(item_data, tab)
            items.append(priced)
            total_value += priced.total_price
            if priced.is_valuable:
                valuable_count += 1

        # Sort by value descending, with evaluated items sorted by score after priced items
        def sort_key(x: PricedItem) -> tuple:
            # Primary: actual chaos value (priced items first)
            # Secondary: evaluation score for unpriced rares
            # This places priced items first, then evaluated rares by score, then unknowns
            if x.total_price > 0:
                return (1, x.total_price, 0)  # Priced items: sort by price
            elif x.eval_score > 0:
                return (0, 0, x.eval_score)  # Evaluated: sort by score after priced
            return (-1, 0, 0)  # Unknown: last

        items.sort(key=sort_key, reverse=True)

        return PricedTab(
            id=tab.id,
            name=tab.name,
            index=tab.index,
            tab_type=tab.type,
            items=items,
            total_value=total_value,
            valuable_count=valuable_count,
        )

    def valuate_tab_incremental(
        self,
        tab: StashTab,
        batch_size: int = 50,
        on_batch: Optional[Callable[[List[PricedItem], int, int], Any]] = None,
    ) -> PricedTab:
        """
        Price all items in a stash tab incrementally with batch callbacks.

        This method prices items in batches and calls the callback after each
        batch, allowing the UI to update progressively.

        Args:
            tab: StashTab to price
            batch_size: Number of items to process per batch
            on_batch: Callback(priced_items, processed_count, total_count)

        Returns:
            PricedTab with all priced items
        """
        items: List[PricedItem] = []
        total_value = 0.0
        valuable_count = 0
        total_items = len(tab.items)

        for i, item_data in enumerate(tab.items):
            priced = self._price_item(item_data, tab)
            items.append(priced)
            total_value += priced.total_price
            if priced.is_valuable:
                valuable_count += 1

            # Emit batch callback every batch_size items
            if on_batch and ((i + 1) % batch_size == 0 or i == total_items - 1):
                # Send only the new items in this batch
                batch_start = (i // batch_size) * batch_size
                batch_items = items[batch_start:i + 1]
                on_batch(batch_items, i + 1, total_items)

        # Sort by value descending
        def sort_key(x: PricedItem) -> tuple:
            if x.total_price > 0:
                return (1, x.total_price, 0)
            elif x.eval_score > 0:
                return (0, 0, x.eval_score)
            return (-1, 0, 0)

        items.sort(key=sort_key, reverse=True)

        return PricedTab(
            id=tab.id,
            name=tab.name,
            index=tab.index,
            tab_type=tab.type,
            items=items,
            total_value=total_value,
            valuable_count=valuable_count,
        )

    def valuate_snapshot(
        self,
        snapshot: StashSnapshot,
        progress_callback: Optional[Callable[[int, int, str], Any]] = None,
    ) -> ValuationResult:
        """
        Price all items in a stash snapshot.

        Args:
            snapshot: StashSnapshot to price
            progress_callback: Optional callback(current, total, tab_name)

        Returns:
            ValuationResult with all priced tabs
        """
        result = ValuationResult(
            league=snapshot.league,
            account_name=snapshot.account_name,
        )

        total_tabs = len(snapshot.tabs)

        for i, tab in enumerate(snapshot.tabs):
            if progress_callback:
                progress_callback(i + 1, total_tabs, tab.name)

            priced_tab = self.valuate_tab(tab)
            result.tabs.append(priced_tab)

            result.total_value += priced_tab.total_value
            result.total_items += len(priced_tab.items)
            result.priced_items += sum(1 for item in priced_tab.items if item.price_source != PriceSource.UNKNOWN)
            result.unpriced_items += sum(1 for item in priced_tab.items if item.price_source == PriceSource.UNKNOWN)

            # Handle children (nested tabs)
            for child in tab.children:
                child_priced = self.valuate_tab(child)
                result.tabs.append(child_priced)
                result.total_value += child_priced.total_value
                result.total_items += len(child_priced.items)

        # Sort tabs by value
        result.tabs.sort(key=lambda x: x.total_value, reverse=True)

        logger.info(
            f"Valuated {result.total_items} items across {len(result.tabs)} tabs. "
            f"Total: {result.display_total}"
        )

        return result


# Convenience functions
_valuator: Optional[StashValuator] = None


def get_valuator() -> StashValuator:
    """Get or create singleton valuator."""
    global _valuator
    if _valuator is None:
        _valuator = StashValuator()
    return _valuator


def valuate_stash(
    poesessid: str,
    account_name: str,
    league: str,
    max_tabs: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str], Any]] = None,
) -> ValuationResult:
    """
    Fetch and valuate stash.

    Args:
        poesessid: POESESSID cookie
        account_name: PoE account name
        league: League name
        max_tabs: Maximum tabs to fetch
        progress_callback: Callback for progress updates

    Returns:
        ValuationResult with all priced items
    """
    valuator = get_valuator()

    # Load prices first
    if progress_callback:
        progress_callback(0, 0, "Loading prices...")
    valuator.load_prices(league)

    # Fetch stash
    if progress_callback:
        progress_callback(0, 0, "Connecting to PoE...")
    client = PoEStashClient(poesessid)

    def stash_progress(cur, total):
        if progress_callback:
            progress_callback(cur, total, f"Fetching tab {cur}/{total}...")

    snapshot = client.fetch_all_stashes(
        account_name,
        league,
        max_tabs=max_tabs,
        progress_callback=stash_progress,
    )

    # Valuate
    def val_progress(cur, total, name):
        if progress_callback:
            progress_callback(cur, total, f"Pricing {name}...")

    return valuator.valuate_snapshot(snapshot, progress_callback=val_progress)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 3:
        print("Usage: python stash_valuator.py <POESESSID> <account_name> [league]")
        sys.exit(1)

    poesessid = sys.argv[1]
    account_name = sys.argv[2]
    league = sys.argv[3] if len(sys.argv) > 3 else "Phrecia"

    def progress(cur, total, msg):
        if total > 0:
            print(f"  [{cur}/{total}] {msg}")
        else:
            print(f"  {msg}")

    print(f"\n=== Stash Valuation ({league}) ===\n")

    result = valuate_stash(
        poesessid,
        account_name,
        league,
        max_tabs=5,  # Limit for testing
        progress_callback=progress,
    )

    print(f"\n=== Results ===")
    print(f"Total Value: {result.display_total}")
    print(f"Items: {result.total_items} ({result.priced_items} priced)")
    print(f"\nTop Tabs:")
    for tab in result.tabs[:5]:
        print(f"  {tab.name}: {tab.display_value} ({tab.valuable_count} valuable)")

    print(f"\nTop Items:")
    all_items = []
    for tab in result.tabs:
        all_items.extend(tab.items)
    all_items.sort(key=lambda x: x.total_price, reverse=True)

    for item in all_items[:10]:
        print(f"  {item.display_name}: {item.display_price} ({item.tab_name})")
