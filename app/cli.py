#!/usr/bin/env python3
"""
CLI interface for the Basketball Stats Tracker application.
Provides commands for database initialization, maintenance, and reporting.
"""

import typer

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
    """
    # pylint: disable=import-outside-toplevel
    from app.services.database_admin_service import DatabaseAdminService

    db_url = settings.DATABASE_URL
    admin_service = DatabaseAdminService(db_url)
    admin_service.initialize_schema(force=force, make_migration=make_migration)


@cli.command("health-check")
def check_database_health():
    """
    Check if the database is properly set up and accessible.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.database_admin_service import DatabaseAdminService

    db_url = settings.DATABASE_URL
    admin_service = DatabaseAdminService(db_url)
    if admin_service.check_connection():
        typer.echo("Database connection successful!")
        return True
    else:
        typer.echo("Database connection test failed!")
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


@cli.command("import-roster")
def import_roster(
    roster_file: str = typer.Option(
        ...,  # Makes this parameter required
        "--roster-file",
        "-r",
        help="Path to the CSV file containing the roster (team names, player names, jersey numbers)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview what would be imported without making any changes to the database",
    ),
):
    """
    Import teams and players from a CSV file.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.csv_import_service import import_roster_from_csv

    return import_roster_from_csv(roster_file, dry_run)


@cli.command("import-game")
def import_game_stats(
    game_stats_file: str = typer.Option(
        ...,  # Makes this parameter required
        "--game-stats-file",
        "-g",
        help="Path to the CSV file containing the game statistics",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Preview what would be imported without making any changes to the database",
    ),
):
    """
    Import game statistics from a CSV file.
    """
    # pylint: disable=import-outside-toplevel
    from app.services.csv_import_service import import_game_stats_from_csv

    return import_game_stats_from_csv(game_stats_file, dry_run)


if __name__ == "__main__":
    cli()
