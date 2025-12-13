"""
Base repository class for thread-safe database operations.

Provides common execution helpers used by all domain-specific repositories.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator, List, Optional, Tuple, Union, cast

logger = logging.getLogger(__name__)

# Type alias for SQL parameters
SqlParams = Union[Tuple[()], Tuple[object, ...]]


class BaseRepository:
    """
    Base class for all database repositories.

    Provides thread-safe execution helpers and transaction management.
    Each repository receives a shared connection and lock from the
    parent Database instance.
    """

    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        """
        Initialize the repository with shared connection and lock.

        Args:
            conn: SQLite connection (shared across all repositories)
            lock: Threading lock for thread-safe operations
        """
        self._conn = conn
        self._lock = lock

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Provide a transaction scope with thread safety.

        Usage:
            with repo.transaction() as conn:
                conn.execute(...)
                conn.execute(...)
            # Commits on success, rolls back on error

        Yields:
            The SQLite connection within the transaction
        """
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception as exc:
                self._conn.rollback()
                logger.error(f"Transaction failed: {exc}")
                raise

    def _execute(
        self, sql: str, params: SqlParams = (), commit: bool = True
    ) -> sqlite3.Cursor:
        """
        Thread-safe execute helper for single operations.

        Args:
            sql: SQL statement to execute
            params: Parameters for the SQL statement
            commit: Whether to commit after execution (default True)

        Returns:
            The cursor from the execute call
        """
        with self._lock:
            cursor = self._conn.execute(sql, params)
            if commit:
                self._conn.commit()
            return cursor

    def _execute_fetchone(
        self, sql: str, params: SqlParams = ()
    ) -> Optional[sqlite3.Row]:
        """
        Thread-safe fetchone helper.

        Args:
            sql: SQL query to execute
            params: Parameters for the SQL query

        Returns:
            Single row result, or None if no rows
        """
        with self._lock:
            cursor = self._conn.execute(sql, params)
            result = cursor.fetchone()
            return cast(Optional[sqlite3.Row], result)

    def _execute_fetchall(
        self, sql: str, params: SqlParams = ()
    ) -> List[sqlite3.Row]:
        """
        Thread-safe fetchall helper.

        Args:
            sql: SQL query to execute
            params: Parameters for the SQL query

        Returns:
            List of all matching rows
        """
        with self._lock:
            cursor = self._conn.execute(sql, params)
            return cursor.fetchall()
