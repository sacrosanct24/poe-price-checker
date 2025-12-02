from __future__ import annotations

import time
import pytest

from core.item_parser import ItemParser


pytestmark = pytest.mark.unit


def test_item_parser_basic_throughput_smoke():
    """
    Very lenient, deterministic throughput smoke test for ItemParser.

    Parses a simple, common item many times to guard against accidental
    performance regressions in hot regex paths. Threshold is generous to
    be stable across CI runners and OS.
    """
    parser = ItemParser()

    sample = (
        "Rarity: RARE\n"
        "Doom Visor\n"
        "Hubris Circlet\n"
        "--------\n"
        "Quality: +20%\n"
        "Item Level: 86\n"
        "--------\n"
        "+95 to maximum Energy Shield\n"
        "+42% to Fire Resistance\n"
    )

    # Warm up any caches/regex engines
    for _ in range(50):
        assert parser.parse(sample) is not None

    iterations = 2000
    start = time.perf_counter()
    for _ in range(iterations):
        item = parser.parse(sample)
        assert item is not None
        # A couple of cheap sanity accesses that touch parsed fields
        _ = item.quality, item.item_level, item.get_display_name()
    elapsed = time.perf_counter() - start

    # Generous threshold (in seconds) to keep this stable on CI.
    # This primarily guards against O(N^2) mistakes or re-compiling regexes per line.
    assert elapsed < 1.5, f"Parsing {iterations} items took too long: {elapsed:.3f}s"
