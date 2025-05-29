"""
Service for database initialization, migration, and health checks.
Handles Alembic migrations, table management, and connection tests.
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

import app.data_access.database_manager as db_manager
from app.data_access.models import Base


class DatabaseAdminService:
    """
    Service class for handling database administration tasks.

    This class provides methods for database initialization, schema migration,
    connection testing, and other administrative database operations.
    It encapsulates Alembic migration handling and SQLAlchemy schema operations.
    """

    def __init__(self, db_url: str, alembic_ini_path: str = "alembic.ini"):
        self.db_url = db_url
        self.alembic_ini_path = alembic_ini_path
        self.engine = db_manager.db_manager.get_engine()
        self.alembic_cfg = Config(self.alembic_ini_path)

    def ensure_data_dir(self):
        """
        Ensure the directory for SQLite database file exists.

        For SQLite databases, creates the parent directory if it doesn't exist.
        Returns the directory path for SQLite or None for other database types.

        Returns:
            str or None: The data directory path for SQLite or None for other databases.
        """
        if self.db_url.startswith("sqlite:///"):
            db_path = self.db_url.replace("sqlite:///", "")
            data_dir = os.path.dirname(os.path.abspath(db_path))
            os.makedirs(data_dir, exist_ok=True)
            return data_dir
        return None

    def drop_all_tables(self):
        """
        Drop all tables defined in the SQLAlchemy models and alembic version table.

        Uses SQLAlchemy's metadata to identify and drop all tables,
        including the alembic_version table to ensure clean reset.
        """
        # Drop all model tables
        Base.metadata.drop_all(bind=self.engine)

        # Also drop alembic_version table to ensure clean state for migrations
        try:
            with self.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                conn.commit()
        except Exception:
            # Ignore errors if table doesn't exist or in test environments
            pass

    def create_migration(self, message: str = "Update database schema"):
        """
        Create a new Alembic migration based on model changes.

        Ensures the migrations directory exists and generates a new migration script
        that auto-detects changes between the current database schema and models.

        Args:
            message: Description message for the migration
        """
        Path("migrations/versions").mkdir(parents=True, exist_ok=True)
        command.revision(self.alembic_cfg, message=message, autogenerate=True)

    def upgrade_to_head(self):
        """
        Apply all migrations to update database to the latest schema version.

        Uses Alembic to upgrade the database to the most recent (head) version.
        """
        command.upgrade(self.alembic_cfg, "head")

    def initialize_schema(self, force: bool = False, make_migration: bool = False, migration_message: str = ""):
        """
        Initialize or update the database schema.

        This method handles the complete database initialization process:
        1. Ensures the data directory exists (for SQLite)
        2. Optionally drops all tables if force=True
        3. Optionally creates a new migration if make_migration=True
        4. Applies all pending migrations to update the schema

        Args:
            force: If True, drop all existing tables before migrating
            make_migration: If True, create a new migration
            migration_message: Optional message for the migration if created
        """
        data_dir = self.ensure_data_dir()
        if data_dir:
            print(f"Ensuring data directory exists: {data_dir}")
        if force:
            print("Force flag specified. Dropping all existing tables...")
            self.drop_all_tables()
            print("Tables dropped successfully.")
        if make_migration:
            print("Creating new migration based on model changes...")
            msg = (
                migration_message
                if migration_message
                else ("Initial database schema" if force else "Update database schema")
            )
            self.create_migration(msg)
            print("Migration created successfully.")
        print(f"Applying migrations to database at {self.db_url}")
        self.upgrade_to_head()
        print("Database schema updated successfully.")

    def check_connection(self):
        """
        Test if the database connection is working properly.

        Executes a simple query to verify that the database is accessible
        and the connection is functioning.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                return result == 1
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError, ConnectionError, OSError):
            return False
