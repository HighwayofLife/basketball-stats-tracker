#!/usr/bin/env python3
"""
CLI interface for the Basketball Stats Tracker application.
Provides commands for database initialization, maintenance, and reporting.
"""

import csv

import typer
from tabulate import tabulate  # type: ignore

from app.config import settings
from app.data_access.database_manager import db_manager  # Corrected import
from app.reports.report_generator import ReportGenerator
from app.utils import stats_calculator

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
    file: str = typer.Option(
        ...,  # Makes this parameter required
        "--file",
        "-f",
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

    return import_roster_from_csv(file, dry_run)


@cli.command("import-game")
def import_game_stats(
    file: str = typer.Option(
        ...,  # Makes this parameter required
        "--file",
        "-f",
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

    return import_game_stats_from_csv(file, dry_run)


@cli.command("report")
def generate_report(
    game_id: int = typer.Option(..., "--id", "-i", help="ID of the game to generate the report for"),
    output_format: str = typer.Option("console", "--format", "-f", help="Output format: console or csv"),
    output_file: str = typer.Option(
        None,
        "--output",
        "-o",
        help="File path for output when using csv format",
    ),
):
    """
    Generate a box score report for a specific game.
    """
    with db_manager.get_db_session() as db_session:  # Use the imported db_manager
        try:
            report_generator = ReportGenerator(db_session, stats_calculator)
            player_stats, game_summary = report_generator.get_game_box_score_data(game_id)

            if not player_stats:
                typer.echo(f"No data found for game ID: {game_id}")
                return

            if output_format == "console":
                typer.echo(f"Box Score for Game ID: {game_id}")
                typer.echo("\nPlayer Stats:")
                typer.echo(tabulate(player_stats, headers="keys", tablefmt="grid"))

                if game_summary:
                    typer.echo("\nGame Summary:")
                    for key, value in game_summary.items():
                        typer.echo(f"{key.replace('_', ' ').title()}: {value}")

            elif output_format == "csv":
                csv_file_name = output_file if output_file else f"game_{game_id}_box_score.csv"
                with open(csv_file_name, "w", newline="", encoding="utf-8") as csvfile:
                    if player_stats:
                        writer = csv.DictWriter(csvfile, fieldnames=player_stats[0].keys())
                        writer.writeheader()
                        writer.writerows(player_stats)
                typer.echo(f"Report generated: {csv_file_name}")
            else:
                typer.echo(f"Unsupported format: {output_format}. Choose 'console' or 'csv'.")

        except (ValueError, KeyError, TypeError) as e:
            typer.echo(f"Data error occurred: {e}")
        except FileNotFoundError as e:
            typer.echo(f"File error: {e}")
        except ImportError as e:
            typer.echo(f"Module import error: {e}")
        except Exception as e:  # pylint: disable=broad-except
            typer.echo(f"Unexpected error: {e}")
            typer.echo("Please report this issue with the steps to reproduce it")


@cli.command("mcp-server")
def start_mcp_server():
    """
    Start the Model Context Protocol (MCP) server for SQL queries and natural language processing.

    This server provides API access to the basketball stats database via HTTP endpoints.
    """
    typer.echo("Starting MCP Server...")
    # pylint: disable=import-outside-toplevel
    from app.mcp_server import start

    start()


if __name__ == "__main__":
    cli()
