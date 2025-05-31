"""Common dependency injection for the application."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.data_access.db_session import get_db_session


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency.

    Yields:
        Database session
    """
    with get_db_session() as session:
        yield session
