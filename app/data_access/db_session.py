"""
Database session utility for the Basketball Stats Tracker.

This module provides simplified access to database sessions without
directly coupling to the DatabaseManager implementation details.
"""

from contextlib import contextmanager

from app.data_access.database_manager import db_manager


@contextmanager
def get_db_session():
    """
    Provides a transactional scope around a series of operations.
    Manages the lifecycle of a database session.

    This is a convenience wrapper around the DatabaseManager.get_db_session method.

    Yields:
        SQLAlchemy Session: A session for database operations.
    """
    with db_manager.get_db_session() as session:
        yield session
