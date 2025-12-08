"""Tests for core/price_estimation.py - Display policy and rounding helpers."""

import pytest

from core.price_estimation import (
    DisplayPolicy,
    DEFAULT_POLICY,
    get_active_policy,
    set_active_policy,
    set_active_policy_from_dict,
    round_to_step,
)


class TestDisplayPolicy:
    """Tests for DisplayPolicy dataclass."""

    def test_default_policy_values(self):
        """Default policy should have sensible thresholds."""
        policy = DisplayPolicy()
        # Confidence thresholds
        assert policy.high_count == 20
        assert policy.medium_count == 8
        # Spread thresholds
        assert policy.high_spread == 0.35
        assert policy.medium_spread == 0.6
        assert policy.low_conf_spread == 0.8
        # Rounding steps
        assert policy.step_ge_100 == 5.0
        assert policy.step_ge_10 == 1.0

    def test_custom_policy_values(self):
        """Can create policy with custom values."""
        policy = DisplayPolicy(
            high_count=30,
            medium_count=15,
            high_spread=0.25,
        )
        assert policy.high_count == 30
        assert policy.medium_count == 15
        assert policy.high_spread == 0.25
        # Defaults for unspecified
        assert policy.step_ge_100 == 5.0

    def test_policy_is_frozen(self):
        """DisplayPolicy should be immutable."""
        policy = DisplayPolicy()
        with pytest.raises(AttributeError):
            policy.high_count = 100  # Should fail - frozen dataclass

    def test_policy_equality(self):
        """Policies with same values should be equal."""
        policy1 = DisplayPolicy(high_count=10)
        policy2 = DisplayPolicy(high_count=10)
        assert policy1 == policy2

    def test_policy_inequality(self):
        """Policies with different values should not be equal."""
        policy1 = DisplayPolicy(high_count=10)
        policy2 = DisplayPolicy(high_count=20)
        assert policy1 != policy2


class TestActivePolicy:
    """Tests for get/set active policy."""

    def setup_method(self):
        """Reset to default policy before each test."""
        set_active_policy(DEFAULT_POLICY)

    def teardown_method(self):
        """Reset to default policy after each test."""
        set_active_policy(DEFAULT_POLICY)

    def test_get_active_policy_returns_default(self):
        """get_active_policy should return default when not customized."""
        policy = get_active_policy()
        assert policy == DEFAULT_POLICY

    def test_set_active_policy(self):
        """set_active_policy should change the active policy."""
        custom = DisplayPolicy(high_count=100)
        set_active_policy(custom)
        assert get_active_policy() == custom
        assert get_active_policy().high_count == 100

    def test_active_policy_persists(self):
        """Active policy should persist until changed."""
        custom = DisplayPolicy(medium_count=50)
        set_active_policy(custom)

        # Multiple calls should return the same custom policy
        assert get_active_policy().medium_count == 50
        assert get_active_policy().medium_count == 50


class TestSetActivePolicyFromDict:
    """Tests for set_active_policy_from_dict function."""

    def setup_method(self):
        """Reset to default policy before each test."""
        set_active_policy(DEFAULT_POLICY)

    def teardown_method(self):
        """Reset to default policy after each test."""
        set_active_policy(DEFAULT_POLICY)

    def test_set_from_complete_dict(self):
        """Should set all values from complete dict."""
        data = {
            "high_count": 25,
            "medium_count": 10,
            "high_spread": 0.3,
            "medium_spread": 0.5,
            "low_conf_spread": 0.7,
            "step_ge_100": 10.0,
            "step_ge_10": 2.0,
        }
        set_active_policy_from_dict(data)
        policy = get_active_policy()

        assert policy.high_count == 25
        assert policy.medium_count == 10
        assert policy.high_spread == 0.3
        assert policy.medium_spread == 0.5
        assert policy.low_conf_spread == 0.7
        assert policy.step_ge_100 == 10.0
        assert policy.step_ge_10 == 2.0

    def test_set_from_partial_dict(self):
        """Should use defaults for missing keys."""
        data = {"high_count": 30}
        set_active_policy_from_dict(data)
        policy = get_active_policy()

        assert policy.high_count == 30
        # Other values should be defaults
        assert policy.medium_count == DEFAULT_POLICY.medium_count
        assert policy.high_spread == DEFAULT_POLICY.high_spread

    def test_set_from_empty_dict_resets_to_default(self):
        """Empty dict should reset to defaults."""
        # First customize
        set_active_policy(DisplayPolicy(high_count=999))
        # Then reset with empty dict
        set_active_policy_from_dict({})
        policy = get_active_policy()

        assert policy == DEFAULT_POLICY

    def test_set_from_non_dict_does_nothing(self):
        """Non-dict input should not change policy."""
        custom = DisplayPolicy(high_count=100)
        set_active_policy(custom)

        set_active_policy_from_dict(None)  # type: ignore
        assert get_active_policy().high_count == 100

        set_active_policy_from_dict([1, 2, 3])  # type: ignore
        assert get_active_policy().high_count == 100

        set_active_policy_from_dict("invalid")  # type: ignore
        assert get_active_policy().high_count == 100

    def test_set_from_dict_with_invalid_values(self):
        """Invalid values should not change policy."""
        custom = DisplayPolicy(high_count=100)
        set_active_policy(custom)

        # Invalid type that can't be cast to int
        set_active_policy_from_dict({"high_count": "not_a_number"})
        # Policy should remain unchanged
        assert get_active_policy().high_count == 100

    def test_set_from_dict_with_string_numbers(self):
        """String numbers should be converted."""
        set_active_policy_from_dict({"high_count": "50", "high_spread": "0.25"})
        policy = get_active_policy()

        assert policy.high_count == 50
        assert policy.high_spread == 0.25


class TestRoundToStep:
    """Tests for round_to_step function."""

    def test_round_to_5(self):
        """Should round to nearest 5 (uses banker's rounding at midpoint)."""
        assert round_to_step(123.4, 5.0) == 125.0
        assert round_to_step(121.0, 5.0) == 120.0
        assert round_to_step(122.5, 5.0) == 120.0  # 24.5 rounds to 24 (even)
        assert round_to_step(117.5, 5.0) == 120.0  # 23.5 rounds to 24 (even)
        assert round_to_step(117.4, 5.0) == 115.0

    def test_round_to_1(self):
        """Should round to nearest 1."""
        assert round_to_step(12.4, 1.0) == 12.0
        assert round_to_step(12.5, 1.0) == 12.0  # Python rounds .5 to even
        assert round_to_step(12.6, 1.0) == 13.0
        assert round_to_step(12.51, 1.0) == 13.0

    def test_round_to_10(self):
        """Should round to nearest 10 (uses banker's rounding)."""
        assert round_to_step(123.0, 10.0) == 120.0
        assert round_to_step(125.0, 10.0) == 120.0  # 12.5 rounds to 12 (even)
        assert round_to_step(135.0, 10.0) == 140.0  # 13.5 rounds to 14 (even)
        assert round_to_step(127.0, 10.0) == 130.0

    def test_round_to_fractional_step(self):
        """Should handle fractional steps."""
        assert round_to_step(1.23, 0.5) == 1.0
        assert round_to_step(1.26, 0.5) == 1.5
        assert round_to_step(1.75, 0.5) == 2.0

    def test_round_zero(self):
        """Zero should remain zero."""
        assert round_to_step(0.0, 5.0) == 0.0
        assert round_to_step(0.0, 1.0) == 0.0

    def test_round_negative(self):
        """Should handle negative values."""
        assert round_to_step(-12.4, 5.0) == -10.0
        assert round_to_step(-13.0, 5.0) == -15.0

    def test_zero_step_returns_original(self):
        """Zero step should return original value."""
        assert round_to_step(123.456, 0.0) == 123.456

    def test_negative_step_returns_original(self):
        """Negative step should return original value."""
        assert round_to_step(123.456, -5.0) == 123.456

    def test_very_small_step(self):
        """Should handle very small steps."""
        result = round_to_step(1.234567, 0.01)
        assert abs(result - 1.23) < 0.001

    def test_large_value(self):
        """Should handle large values."""
        assert round_to_step(12345.0, 100.0) == 12300.0
        assert round_to_step(12350.0, 100.0) == 12400.0


class TestPolicyRoundingIntegration:
    """Integration tests for policy-based rounding."""

    def test_round_high_value_with_default_policy(self):
        """High values (>=100) should round to step_ge_100."""
        policy = DEFAULT_POLICY
        value = 123.4
        step = policy.step_ge_100  # 5.0

        result = round_to_step(value, step)
        assert result == 125.0

    def test_round_medium_value_with_default_policy(self):
        """Medium values (>=10) should round to step_ge_10."""
        policy = DEFAULT_POLICY
        value = 12.4
        step = policy.step_ge_10  # 1.0

        result = round_to_step(value, step)
        assert result == 12.0

    def test_custom_policy_rounding_steps(self):
        """Custom policy should use custom rounding steps."""
        policy = DisplayPolicy(step_ge_100=10.0, step_ge_10=2.0)

        # High value with step 10
        assert round_to_step(123.0, policy.step_ge_100) == 120.0

        # Medium value with step 2 (13/2 = 6.5 rounds to 6 (even))
        assert round_to_step(13.0, policy.step_ge_10) == 12.0
        # Value that doesn't hit midpoint
        assert round_to_step(15.0, policy.step_ge_10) == 16.0  # 7.5 rounds to 8
