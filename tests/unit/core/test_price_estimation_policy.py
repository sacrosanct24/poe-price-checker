import math

from core.price_service import PriceService


def test_compute_display_price_no_listings():
    stats = {"count": 0}
    out = PriceService.compute_display_price(stats)
    assert out["display_price"] is None
    assert out["rounded_price"] is None
    assert out["confidence"] == "none"


def test_compute_display_price_high_confidence_and_rounding_ge_100():
    # Tight spread, large sample
    stats = {
        "count": 25,
        "mean": 100.0,
        "median": 100.0,
        "p25": 90.0,
        "p75": 110.0,
        "trimmed_mean": 100.2,
        "stddev": 10.0,
    }
    out = PriceService.compute_display_price(stats)
    assert out["confidence"] == "high"
    # trimmed_mean chosen with count>=12
    assert math.isclose(out["display_price"], 100.2, rel_tol=0, abs_tol=1e-9)
    # Rounded to nearest 5c (100.2 -> 100.0)
    assert out["rounded_price"] == 100.0
    assert "center=trimmed_mean" in out["reason"]


def test_compute_display_price_medium_confidence_and_rounding_ge_10():
    stats = {
        "count": 10,
        "mean": 20.0,
        "median": 20.0,
        "p25": 12.0,
        "p75": 28.0,  # IQR=16, IQR/median=0.8 -> borderline; make cv lower
        "trimmed_mean": None,
        "stddev": 10.0,  # cv=0.5
    }
    # Adjust p25/p75 to get medium spread: set to 15 and 25 (IQR=10, ratio=0.5)
    stats["p25"] = 15.0
    stats["p75"] = 25.0

    out = PriceService.compute_display_price(stats)
    assert out["confidence"] == "medium"
    # median chosen (count>=4 and trimmed_mean None)
    assert out["display_price"] == 20.0
    # Rounded to nearest 1c for >=10c
    assert out["rounded_price"] == 20.0
    assert "center=median" in out["reason"]


def test_compute_display_price_low_confidence_due_to_spread():
    stats = {
        "count": 12,
        "mean": 50.0,
        "median": 50.0,
        "p25": 10.0,
        "p75": 90.0,  # IQR=80, ratio=1.6
        "trimmed_mean": 50.0,
        "stddev": 45.0,  # cv=0.9
    }
    out = PriceService.compute_display_price(stats)
    assert out["confidence"] == "low"
    assert out["rounded_price"] == 50.0  # step 1c leaves it unchanged


def test_compute_display_price_rounding_bands_small_values():
    # <1c: 2 decimals
    stats_small = {
        "count": 4,
        "mean": 0.456,
        "median": 0.456,
        "p25": 0.45,
        "p75": 0.46,
        "trimmed_mean": None,
        "stddev": 0.01,
    }
    out_small = PriceService.compute_display_price(stats_small)
    assert out_small["rounded_price"] == 0.46

    # 1–10c: 1 decimal
    stats_mid = {
        "count": 5,
        "mean": 1.44,
        "median": 1.44,
        "p25": 1.2,
        "p75": 1.6,
        "trimmed_mean": None,
        "stddev": 0.2,
    }
    out_mid = PriceService.compute_display_price(stats_mid)
    assert out_mid["rounded_price"] == 1.4

    # >=10c and <100c: nearest 1c
    stats_ge10 = {
        "count": 6,
        "mean": 15.2,
        "median": 15.2,
        "p25": 14.0,
        "p75": 16.0,
        "trimmed_mean": None,
        "stddev": 0.5,
    }
    out_ge10 = PriceService.compute_display_price(stats_ge10)
    assert out_ge10["rounded_price"] == 15.0

    # >=100c: nearest 5c
    stats_ge100 = {
        "count": 20,
        "mean": 102.6,
        "median": 102.6,
        "p25": 100.0,
        "p75": 105.0,
        "trimmed_mean": 102.6,
        "stddev": 1.5,
    }
    out_ge100 = PriceService.compute_display_price(stats_ge100)
    assert out_ge100["rounded_price"] == 105.0
