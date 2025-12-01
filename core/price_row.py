from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


LinksType = Union[str, int, None]


@dataclass
class PriceRow:
    """Normalized price result row across sources.

    This is a typed shape to help API/GUI layers and future refactors.
    Existing call sites may still pass dictionaries; adapters in
    MultiSourcePriceService will normalize objects to dicts for output.
    """

    source: str
    item_name: str = ""
    variant: str = ""
    links: LinksType = None
    chaos_value: Optional[float] = None
    divine_value: Optional[float] = None
    listing_count: Optional[int] = None
    confidence: str = ""
    explanation: str = ""
