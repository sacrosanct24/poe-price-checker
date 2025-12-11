"""
Database Package.

This package provides SQLite-backed persistence for the PoE Price Checker.

Public API:
- Database: Main database class for all persistence operations
- SCHEMA_VERSION: Current schema version number

Example:
    from core.database import Database
    db = Database()
    db.add_checked_item(...)
"""
from core.database.base import Database
from core.database.schema import SCHEMA_VERSION

__all__ = [
    "Database",
    "SCHEMA_VERSION",
]
