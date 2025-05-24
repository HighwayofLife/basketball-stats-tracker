"""Database-related CLI command handlers."""

import typer

from app.config import settings
from app.services.database_admin_service import DatabaseAdminService


class DatabaseCommands:
    """Handles database-related CLI commands."""

    @staticmethod
    def initialize_database(force: bool = False, make_migration: bool = False) -> None:
        """
        Initialize or upgrade the database schema using Alembic migrations.

        Args:
            force: Force recreation of tables even if they already exist
            make_migration: Create a new migration based on model changes
        """
        db_url = settings.DATABASE_URL
        admin_service = DatabaseAdminService(db_url)
        admin_service.initialize_schema(force=force, make_migration=make_migration)

    @staticmethod
    def check_database_health() -> bool:
        """
        Check if the database is properly set up and accessible.

        Returns:
            bool: True if database connection is successful, False otherwise
        """
        db_url = settings.DATABASE_URL
        admin_service = DatabaseAdminService(db_url)
        if admin_service.check_connection():
            typer.echo("Database connection successful!")
            return True

        typer.echo("Database connection test failed!")
        return False

    @staticmethod
    def seed_database() -> None:
        """
        Seed the database with initial data for development and testing.
        This will add teams, players, and sample games to the database.
        """
        typer.echo("Seeding database with development data...")

        # Import the seed script
        # pylint: disable=import-outside-toplevel
        from seed import seed_all

        # Run the seed function
        seed_all()

        typer.echo("Database seeding completed.")
