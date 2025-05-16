#!/usr/bin/env python3
"""
CLI interface for the Basketball Stats Tracker application.
Provides commands for database initialization, maintenance, and reporting.
"""

import os

import typer
from sqlalchemy import text

import app.data_access.database_manager as db_manager
from app.config import settings

cli = typer.Typer(help="Basketball Stats Tracker CLI")


@cli.command("init-db")
def initialize_database(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force recreation of tables even if they already exist (WARNING: This will delete all data)",
    ),
    make_migration: bool = typer.Option(
        False,
        "--migration",
        "-m",
        help="Create a new migration based on model changes",
    ),
):
    """
    Initialize or upgrade the database schema using Alembic migrations.

    This command is idempotent - it will apply any pending migrations to bring the database
    schema up to date. If --force is specified, it will drop all tables first.
    """
    # Ensure the data directory exists
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        # Extract the path from the SQLite URL
        db_path = db_url.replace("sqlite:///", "")
        data_dir = os.path.dirname(os.path.abspath(db_path))

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        typer.echo(f"Ensuring data directory exists: {data_dir}")

    # Import here to avoid circular imports
    # pylint: disable=wrong-import-position
    # pylint: disable=import-outside-toplevel
    from alembic import command
    from alembic.config import Config

    # Get the database engine
    engine = db_manager.db_manager.get_engine()

    if force:
        # Drop all tables if force is specified
        typer.echo("Force flag specified. Dropping all existing tables...")
        from app.data_access.models import Base

        Base.metadata.drop_all(bind=engine)
        typer.echo("Tables dropped successfully.")

    # Get Alembic configuration
    alembic_cfg = Config("alembic.ini")

    if make_migration:
        # Create a new migration based on the current models
        typer.echo("Creating new migration based on model changes...")

        # Check if versions directory exists, if not create it
        from pathlib import Path

        Path("migrations/versions").mkdir(parents=True, exist_ok=True)

        # Create a new migration
        migration_message = "Initial database schema" if force else "Update database schema"
        command.revision(alembic_cfg, message=migration_message, autogenerate=True)
        typer.echo("Migration created successfully.")

    # Run the migrations to upgrade the database to the latest version
    typer.echo(f"Applying migrations to database at {db_url}")
    command.upgrade(alembic_cfg, "head")
    typer.echo("Database schema updated successfully.")


@cli.command("health-check")
def check_database_health():
    """
    Check if the database is properly set up and accessible.
    """
    try:
        engine = db_manager.db_manager.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            if result == 1:
                typer.echo("Database connection successful!")
                return True
            else:
                typer.echo("Database connection test failed!")
                return False
    # pylint: disable=broad-except
    except Exception as e:
        typer.echo(f"Error connecting to database: {e}")
        return False


@cli.command("seed-db")
def seed_database():
    """
    Seed the database with initial data for development and testing.

    This will add teams, players, and sample games to the database.
    """
    typer.echo("Seeding database with development data...")

    # Import the seed script
    # pylint: disable=wrong-import-position
    # pylint: disable=import-outside-toplevel
    from seed import seed_all

    # Run the seed function
    seed_all()

    typer.echo("Database seeding completed.")


if __name__ == "__main__":
    cli()
