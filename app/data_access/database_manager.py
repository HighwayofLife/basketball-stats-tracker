# app/data_access/database_manager.py
"""Database connection and session management for the basketball stats application.

Provides SQLAlchemy database utilities for engine creation, session management,
and table operations to ensure consistent database access throughout the application.
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.data_access.models import Base


class DatabaseManager:
    """
    Manages database connections and sessions for the application.

    This class centralizes SQLAlchemy operations and provides a consistent
    interface for database interaction throughout the application.
    """

    def __init__(self):
        """Initialize the database manager with no engine or session factory."""
        self._engine = None
        self._session_local = None

    def get_engine(self, db_url: str | None = None) -> Engine:
        """
        Creates and returns a SQLAlchemy engine instance.

        Args:
            db_url: The database URL to connect to. If None, uses DATABASE_URL from settings.

        Returns:
            SQLAlchemy Engine instance.
        """
        if db_url is None:
            # Use the DATABASE_URL from our Settings instance
            db_url = settings.DATABASE_URL
        return create_engine(db_url)

    def get_session_local(self, engine=None):
        """
        Returns a sessionmaker instance (SessionLocal).
        Initializes it if it hasn't been already.

        Args:
            engine: SQLAlchemy engine to bind the session to. If None, uses the default engine.

        Returns:
            SQLAlchemy sessionmaker factory configured with the appropriate engine.
        """
        if self._session_local is None:
            self._engine = self.get_engine() if engine is None else engine
            self._session_local = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
        return self._session_local

    def create_tables(self, engine=None):
        """
        Creates all tables in the database.

        Args:
            engine: The SQLAlchemy engine instance to bind to. If None, uses the default engine.
        """
        engine_to_use = engine if engine is not None else (self._engine or self.get_engine())
        Base.metadata.create_all(bind=engine_to_use)

    @contextmanager
    def get_db_session(self):
        """
        Provides a transactional scope around a series of operations.
        Manages the lifecycle of a database session.

        Yields:
            SQLAlchemy Session: A session for database operations.
        """
        # Get the engine, default or configured
        current_engine = self._engine if self._engine is not None else self.get_engine()

        # Get the SessionLocal factory, initializing it if necessary
        current_session_local = self.get_session_local(current_engine)

        db = None
        try:
            db = current_session_local()
            yield db
        finally:
            if db is not None:
                db.close()


# Create a singleton instance for the application to use
db_manager = DatabaseManager()


# Example of how to initialize and use for the main app:
# You might call this once at app startup or within a CLI command
# main_engine = db_manager.get_engine(settings.DATABASE_URL)
# db_manager.create_tables(main_engine) # To create tables
# session_factory = db_manager.get_session_local(main_engine) # To get the configured sessionmaker

# And in your app (e.g., Flask request or service):
# def some_service_function():
#     with db_manager.get_db_session() as db:
#         # use db for queries
#         pass
