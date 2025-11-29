"""
Result type for consistent error handling.

Provides a Rust-inspired Result pattern to standardize error handling
across the codebase, replacing inconsistent patterns like:
- Return None on error
- Raise exceptions
- Return (data, error) tuples

Usage:
    from core.result import Result, Ok, Err

    def get_price(item: str) -> Result[float, str]:
        try:
            price = fetch_price(item)
            return Ok(price)
        except APIError as e:
            return Err(f"API error: {e}")

    # Caller:
    result = get_price("Headhunter")
    if result.is_ok():
        print(f"Price: {result.unwrap()}")
    else:
        print(f"Error: {result.error}")

    # Or with map/match:
    price = result.unwrap_or(0.0)
    price = result.map(lambda p: p * 1.1).unwrap_or(0.0)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generic,
    NoReturn,
    TypeVar,
    Union,
    overload,
)

T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Mapped success type
F = TypeVar("F")  # Mapped error type


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Represents a successful result containing a value.

    Attributes:
        value: The success value.

    Example:
        >>> result = Ok(42)
        >>> result.is_ok()
        True
        >>> result.unwrap()
        42
    """

    value: T

    def is_ok(self) -> bool:
        """Check if this is a success result.

        Returns:
            True (always, since this is Ok).
        """
        return True

    def is_err(self) -> bool:
        """Check if this is an error result.

        Returns:
            False (always, since this is Ok).
        """
        return False

    def unwrap(self) -> T:
        """Get the success value.

        Returns:
            The contained value.
        """
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get the value or a default if error.

        Args:
            default: Ignored for Ok results.

        Returns:
            The contained value.
        """
        return self.value

    def unwrap_or_else(self, func: Callable[[Any], T]) -> T:
        """Get the value or compute from error.

        Args:
            func: Ignored for Ok results.

        Returns:
            The contained value.
        """
        return self.value

    def map(self, func: Callable[[T], U]) -> Ok[U]:
        """Transform the success value.

        Args:
            func: Function to apply to the value.

        Returns:
            Ok with the transformed value.

        Example:
            >>> Ok(5).map(lambda x: x * 2)
            Ok(value=10)
        """
        return Ok(func(self.value))

    def map_err(self, func: Callable[[Any], F]) -> Ok[T]:
        """Transform the error (no-op for Ok).

        Args:
            func: Ignored for Ok results.

        Returns:
            Self unchanged.
        """
        return self

    def and_then(self, func: Callable[[T], "Result[U, Any]"]) -> "Result[U, Any]":
        """Chain another Result-returning operation.

        Args:
            func: Function that returns a Result.

        Returns:
            The result of applying func to the value.

        Example:
            >>> Ok(5).and_then(lambda x: Ok(x * 2) if x > 0 else Err("negative"))
            Ok(value=10)
        """
        return func(self.value)

    @property
    def error(self) -> None:
        """Get the error value (None for Ok).

        Returns:
            None (Ok has no error).
        """
        return None

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Represents a failed result containing an error.

    Attributes:
        error: The error value (typically a string or exception info).

    Example:
        >>> result = Err("Not found")
        >>> result.is_err()
        True
        >>> result.error
        'Not found'
    """

    error: E

    def is_ok(self) -> bool:
        """Check if this is a success result.

        Returns:
            False (always, since this is Err).
        """
        return False

    def is_err(self) -> bool:
        """Check if this is an error result.

        Returns:
            True (always, since this is Err).
        """
        return True

    def unwrap(self) -> NoReturn:
        """Attempt to get the success value (raises for Err).

        Raises:
            ValueError: Always, since Err has no success value.
        """
        raise ValueError(f"Called unwrap on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Get the value or a default if error.

        Args:
            default: The value to return.

        Returns:
            The default value.
        """
        return default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Get the value or compute from error.

        Args:
            func: Function to compute value from error.

        Returns:
            Result of func(self.error).
        """
        return func(self.error)

    def map(self, func: Callable[[Any], U]) -> "Err[E]":
        """Transform the success value (no-op for Err).

        Args:
            func: Ignored for Err results.

        Returns:
            Self unchanged.
        """
        return self

    def map_err(self, func: Callable[[E], F]) -> "Err[F]":
        """Transform the error value.

        Args:
            func: Function to apply to the error.

        Returns:
            Err with the transformed error.

        Example:
            >>> Err("fail").map_err(lambda e: f"Error: {e}")
            Err(error='Error: fail')
        """
        return Err(func(self.error))

    def and_then(self, func: Callable[[Any], "Result[U, E]"]) -> "Err[E]":
        """Chain another Result-returning operation (no-op for Err).

        Args:
            func: Ignored for Err results.

        Returns:
            Self unchanged.
        """
        return self

    @property
    def value(self) -> None:
        """Get the success value (None for Err).

        Returns:
            None (Err has no value).
        """
        return None

    def __repr__(self) -> str:
        return f"Err({self.error!r})"


# Type alias for Result
Result = Union[Ok[T], Err[E]]


def try_result(func: Callable[[], T]) -> Result[T, str]:
    """Execute a function and wrap result/exception as Result.

    Args:
        func: A callable that might raise an exception.

    Returns:
        Ok with the return value, or Err with the exception message.

    Example:
        >>> result = try_result(lambda: int("42"))
        >>> result.unwrap()
        42
        >>> result = try_result(lambda: int("not a number"))
        >>> result.is_err()
        True
    """
    try:
        return Ok(func())
    except Exception as e:
        return Err(str(e))


def try_result_with_exception(
    func: Callable[[], T]
) -> Result[T, tuple[str, Exception]]:
    """Execute a function and wrap result/exception as Result.

    Like try_result but preserves the original exception.

    Args:
        func: A callable that might raise an exception.

    Returns:
        Ok with the return value, or Err with (message, exception) tuple.

    Example:
        >>> result = try_result_with_exception(lambda: 1/0)
        >>> msg, exc = result.error
        >>> isinstance(exc, ZeroDivisionError)
        True
    """
    try:
        return Ok(func())
    except Exception as e:
        return Err((str(e), e))
