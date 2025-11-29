"""
Test utility functions for CodeRabbit review demo.
"""


def calculate_item_value(base_price, multiplier, bonus=0):
    """Calculate the total value of an item."""
    # TODO: Add input validation
    result = base_price * multiplier + bonus
    return result


def format_currency(amount):
    """Format a currency amount for display."""
    if amount >= 1000:
        return f"{amount/1000:.1f}k"
    else:
        return str(int(amount))


def parse_item_name(raw_name):
    """Parse and clean an item name."""
    name = raw_name.strip()
    name = name.replace("  ", " ")
    # Potential issue: doesn't handle None input
    return name.title()
