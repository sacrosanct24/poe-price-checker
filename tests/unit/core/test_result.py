"""Tests for the Result type (Ok/Err pattern)."""

import pytest

from core.result import Ok, Err, try_result, try_result_with_exception


class TestOk:
    """Tests for Ok result type."""

    def test_is_ok_returns_true(self):
        """Ok.is_ok() should return True."""
        result = Ok(42)
        assert result.is_ok() is True

    def test_is_err_returns_false(self):
        """Ok.is_err() should return False."""
        result = Ok(42)
        assert result.is_err() is False

    def test_unwrap_returns_value(self):
        """Ok.unwrap() should return the contained value."""
        result = Ok("hello")
        assert result.unwrap() == "hello"

    def test_unwrap_or_returns_value(self):
        """Ok.unwrap_or() should return the contained value, ignoring default."""
        result = Ok(42)
        assert result.unwrap_or(0) == 42

    def test_unwrap_or_else_returns_value(self):
        """Ok.unwrap_or_else() should return value, ignoring func."""
        result = Ok(42)
        assert result.unwrap_or_else(lambda e: 0) == 42

    def test_map_transforms_value(self):
        """Ok.map() should transform the contained value."""
        result = Ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped.unwrap() == 10
        assert isinstance(mapped, Ok)

    def test_map_err_is_no_op(self):
        """Ok.map_err() should return self unchanged."""
        result = Ok(42)
        mapped = result.map_err(lambda e: f"Error: {e}")
        assert mapped is result

    def test_and_then_chains_operations(self):
        """Ok.and_then() should chain Result-returning functions."""
        result = Ok(5)
        chained = result.and_then(lambda x: Ok(x * 2))
        assert chained.unwrap() == 10

    def test_and_then_can_return_err(self):
        """Ok.and_then() can return Err from the chained function."""
        result = Ok(-5)
        chained = result.and_then(
            lambda x: Ok(x) if x > 0 else Err("must be positive")
        )
        assert chained.is_err()
        assert chained.error == "must be positive"

    def test_error_property_returns_none(self):
        """Ok.error should return None."""
        result = Ok(42)
        assert result.error is None

    def test_repr(self):
        """Ok should have a readable repr."""
        result = Ok(42)
        assert repr(result) == "Ok(42)"

    def test_ok_with_none_value(self):
        """Ok can contain None as a valid value."""
        result = Ok(None)
        assert result.is_ok()
        assert result.unwrap() is None


class TestErr:
    """Tests for Err result type."""

    def test_is_ok_returns_false(self):
        """Err.is_ok() should return False."""
        result = Err("error message")
        assert result.is_ok() is False

    def test_is_err_returns_true(self):
        """Err.is_err() should return True."""
        result = Err("error message")
        assert result.is_err() is True

    def test_unwrap_raises(self):
        """Err.unwrap() should raise ValueError."""
        result = Err("something went wrong")
        with pytest.raises(ValueError, match="Called unwrap on Err"):
            result.unwrap()

    def test_unwrap_or_returns_default(self):
        """Err.unwrap_or() should return the default value."""
        result = Err("error")
        assert result.unwrap_or(42) == 42

    def test_unwrap_or_else_calls_func(self):
        """Err.unwrap_or_else() should call func with error."""
        result = Err("error")
        value = result.unwrap_or_else(lambda e: len(e))
        assert value == 5

    def test_map_is_no_op(self):
        """Err.map() should return self unchanged."""
        result = Err("error")
        mapped = result.map(lambda x: x * 2)
        assert mapped is result

    def test_map_err_transforms_error(self):
        """Err.map_err() should transform the error."""
        result = Err("fail")
        mapped = result.map_err(lambda e: f"Error: {e}")
        assert mapped.error == "Error: fail"
        assert isinstance(mapped, Err)

    def test_and_then_is_no_op(self):
        """Err.and_then() should return self unchanged."""
        result = Err("error")
        chained = result.and_then(lambda x: Ok(x * 2))
        assert chained is result

    def test_value_property_returns_none(self):
        """Err.value should return None."""
        result = Err("error")
        assert result.value is None

    def test_error_property_returns_error(self):
        """Err.error should return the error value."""
        result = Err("something failed")
        assert result.error == "something failed"

    def test_repr(self):
        """Err should have a readable repr."""
        result = Err("failed")
        assert repr(result) == "Err('failed')"

    def test_err_with_complex_error(self):
        """Err can contain complex error types."""
        error_info = {"code": 404, "message": "Not found"}
        result = Err(error_info)
        assert result.error == {"code": 404, "message": "Not found"}


class TestTryResult:
    """Tests for try_result helper function."""

    def test_returns_ok_on_success(self):
        """try_result should return Ok when function succeeds."""
        result = try_result(lambda: 42)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_returns_err_on_exception(self):
        """try_result should return Err when function raises."""
        result = try_result(lambda: int("not a number"))
        assert result.is_err()
        assert "invalid literal" in result.error

    def test_preserves_return_value_type(self):
        """try_result should preserve the return value type."""
        result = try_result(lambda: {"key": "value"})
        assert result.unwrap() == {"key": "value"}


class TestTryResultWithException:
    """Tests for try_result_with_exception helper function."""

    def test_returns_ok_on_success(self):
        """try_result_with_exception should return Ok when function succeeds."""
        result = try_result_with_exception(lambda: 42)
        assert result.is_ok()
        assert result.unwrap() == 42

    def test_returns_err_with_exception_on_failure(self):
        """try_result_with_exception should return Err with (message, exception)."""
        result = try_result_with_exception(lambda: 1 / 0)
        assert result.is_err()
        msg, exc = result.error
        assert "division by zero" in msg
        assert isinstance(exc, ZeroDivisionError)


class TestResultPatterns:
    """Tests for common usage patterns."""

    def test_chaining_multiple_operations(self):
        """Chain multiple Result operations."""
        result = (
            Ok(5)
            .map(lambda x: x * 2)
            .and_then(lambda x: Ok(x + 1) if x > 0 else Err("negative"))
            .map(lambda x: f"Result: {x}")
        )
        assert result.unwrap() == "Result: 11"

    def test_early_error_stops_chain(self):
        """Error short-circuits the chain."""
        result = (
            Ok(-5)
            .and_then(lambda x: Ok(x) if x > 0 else Err("must be positive"))
            .map(lambda x: x * 2)
            .map(lambda x: x + 1)
        )
        assert result.is_err()
        assert result.error == "must be positive"

    def test_match_style_handling(self):
        """Pattern matching style handling."""

        def process(result):
            if result.is_ok():
                return f"Success: {result.unwrap()}"
            else:
                return f"Error: {result.error}"

        assert process(Ok(42)) == "Success: 42"
        assert process(Err("failed")) == "Error: failed"

    def test_default_value_pattern(self):
        """Using unwrap_or for default values."""
        results = [Ok(10), Err("missing"), Ok(20), Err("invalid")]
        values = [r.unwrap_or(0) for r in results]
        assert values == [10, 0, 20, 0]
        assert sum(values) == 30
