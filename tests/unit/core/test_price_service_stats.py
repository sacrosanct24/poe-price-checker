from __future__ import annotations
import pytest

from core.price_service import PriceService


def test_stats_no_listings():
    stats = {"count": 0}
    out = PriceService.compute_display_price(stats)
    assert out["rounded_price"] is None
    assert out["confidence"] == "none"


def test_stats_prefers_trimmed_mean():
    stats = {
        "count": 15,
        "trimmed_mean": 10.3,
        "median": 5,
        "mean": 7,
        "p25": 9,
        "p75": 11,
        "stddev": 1,
    }
    out = PriceService.compute_display_price(stats)
    assert out["rounded_price"] == 10   # nearest 1c for ≥10
    assert out["confidence"] in {"medium", "high"}


def test_stats_small_sample_uses_median():
    stats = {
        "count": 6,
        "median": 8.2,
        "mean": 9,
        "p25": 7,
        "p75": 9,
        "stddev": 0.5,
        "trimmed_mean": None,
    }
    out = PriceService.compute_display_price(stats)
    assert out["rounded_price"] == 8.2  # 1 decimal


def test_stats_rounding_small_values():
    stats = {
        "count": 10,
        "median": 0.83,
        "p25": 0.7,
        "p75": 1.0,
        "stddev": 0.2,
    }
    out = PriceService.compute_display_price(stats)
    assert out["rounded_price"] == 0.83  # 2 decimals
