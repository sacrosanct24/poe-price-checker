import math

import pytest

from core.pricing import PriceService
from core.price_estimation import set_active_policy_from_dict


@pytest.fixture(autouse=True)
def reset_policy():
    # Reset to defaults before each test to avoid cross-test leakage
    set_active_policy_from_dict({})
    yield
    set_active_policy_from_dict({})


def test_policy_override_changes_confidence_thresholds():
    # Baseline stats that would normally be medium with defaults (count=10)
    stats = {
        "count": 10,
        "mean": 20.0,
        "median": 20.0,
        "p25": 15.0,
        "p75": 25.0,
        "trimmed_mean": None,
        "stddev": 9.0,  # cv=0.45
    }

    out_default = PriceService.compute_display_price(stats)
    assert out_default["confidence"] == "medium"

    # Tighten high_count and spreads so the same stats become "high"
    set_active_policy_from_dict({
        "high_count": 10,
        "high_spread": 0.6,   # looser than defaults to upgrade to high
        "medium_spread": 0.7,
    })

    out_overridden = PriceService.compute_display_price(stats)
    assert out_overridden["confidence"] == "high"


def test_policy_override_changes_rounding_steps():
    # With defaults: >=100c rounds to nearest 5c; we'll change to 10c
    stats = {
        "count": 30,
        "mean": 104.9,
        "median": 104.9,
        "p25": 100.0,
        "p75": 110.0,
        "trimmed_mean": 104.9,
        "stddev": 3.0,
    }

    out_default = PriceService.compute_display_price(stats)
    # 104.9 to nearest 5 -> 105.0
    assert math.isclose(out_default["rounded_price"], 105.0)

    set_active_policy_from_dict({
        "step_ge_100": 10.0,
    })

    out_step10 = PriceService.compute_display_price(stats)
    # 104.9 to nearest 10 -> 100.0
    assert math.isclose(out_step10["rounded_price"], 100.0)


def test_policy_partial_invalid_dict_is_ignored():
    # Provide an invalid value; policy should remain default behavior
    set_active_policy_from_dict({"high_count": "not-an-int"})

    stats = {
        "count": 0,
    }
    out = PriceService.compute_display_price(stats)
    assert out["confidence"] == "none"
