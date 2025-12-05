"""
Feedback Package - User-friendly error handling and feedback collection.

Provides utilities for displaying friendly error messages,
collecting user feedback, and visualizing API rate limits.

Modules:
    error_display: Friendly error messages with recovery options
    feedback_collector: In-app feedback submission form
    rate_limit_indicator: Visual rate limit status indicator
"""

from gui_qt.feedback.error_display import (
    FriendlyError,
    ErrorDisplay,
    ErrorDialog,
    show_error,
    show_warning,
    show_info,
)
from gui_qt.feedback.feedback_collector import (
    FeedbackCollector,
    FeedbackDialog,
    FeedbackType,
)
from gui_qt.feedback.rate_limit_indicator import (
    RateLimitIndicator,
    RateLimitStatus,
)

__all__ = [
    # Error display
    "FriendlyError",
    "ErrorDisplay",
    "ErrorDialog",
    "show_error",
    "show_warning",
    "show_info",
    # Feedback collector
    "FeedbackCollector",
    "FeedbackDialog",
    "FeedbackType",
    # Rate limit indicator
    "RateLimitIndicator",
    "RateLimitStatus",
]
