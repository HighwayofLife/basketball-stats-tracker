from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterable
from typing import Any

from sqlalchemy.orm import Session


@contextmanager
def transaction(session: Session, refresh: Iterable[Any] | None = None):
    """Context manager for wrapping database transactions.

    Commits the session on success and rolls back on error. Optionally
    refreshes provided objects after committing.

    Args:
        session: Active database session.
        refresh: Optional iterable of objects to refresh after commit.
    """
    try:
        yield session
        session.commit()
        if refresh:
            for obj in refresh:
                session.refresh(obj)
    except Exception:
        session.rollback()
        raise
