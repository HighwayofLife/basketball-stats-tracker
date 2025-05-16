#!/usr/bin/env python3
"""
CLI interface for the Basketball Stats Tracker application.
Provides commands for database initialization, maintenance, and reporting.
"""

import csv
import os
from pathlib import Path

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

    The CSV file should have headers and the following columns:
    - team_name: The name of the team
    - player_name: The name of the player
    - jersey_number: The player's jersey number

    Example CSV format:
    team_name,player_name,jersey_number
    Warriors,Stephen Curry,30
    Warriors,Klay Thompson,11
    Lakers,LeBron James,23
    """
    # Check if the file exists
    roster_path = Path(roster_file)
    if not roster_path.exists():
        typer.echo(f"Error: File '{roster_file}' not found.")
        return False

    # Import here to avoid circular imports
    # pylint: disable=wrong-import-position
    # pylint: disable=import-outside-toplevel
    from app.data_access.models import Player, Team

    # Read the CSV file
    try:
        with open(roster_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            # Check required headers
            required_fields = ["team_name", "player_name", "jersey_number"]
            missing_fields = [field for field in required_fields if field not in (reader.fieldnames or [])]

            if missing_fields:
                typer.echo(f"Error: CSV file missing required headers: {', '.join(missing_fields)}")
                return False

            # Process data
            team_data = {}
            player_data = []

            for row in reader:
                team_name = row["team_name"].strip()
                player_name = row["player_name"].strip()

                try:
                    jersey_number = int(row["jersey_number"])
                except (ValueError, TypeError):
                    typer.echo(
                        f"Warning: Invalid jersey number '{row['jersey_number']}' for player '{player_name}'. Skipping."
                    )
                    continue

                # Add team to set of unique team names
                if team_name not in team_data:
                    team_data[team_name] = {"count": 0}
                team_data[team_name]["count"] += 1

                # Add player to list
                player_data.append(
                    {
                        "team_name": team_name,
                        "name": player_name,
                        "jersey_number": jersey_number,
                    }
                )

        # Print summary of what will be imported
        typer.echo(f"\nRoster import summary from {roster_file}:")
        typer.echo(f"Found {len(team_data)} teams and {len(player_data)} players.\n")

        for team_name, info in team_data.items():
            typer.echo(f"Team: {team_name} - {info['count']} players")

        if dry_run:
            typer.echo("\nDry run mode: No changes were made to the database.")
            return True

        # Import data to database
        with db_manager.db_manager.get_db_session() as db:
            teams_added = 0
            teams_existing = 0
            players_added = 0
            players_existing = 0
            players_error = 0

            # First, ensure all teams exist
            team_name_to_id = {}
            for team_name in team_data:
                # Check if team exists
                existing_team = db.query(Team).filter(Team.name == team_name).first()

                if existing_team:
                    team_name_to_id[team_name] = existing_team.id
                    teams_existing += 1
                else:
                    # Create new team
                    new_team = Team(name=team_name)
                    db.add(new_team)
                    db.flush()  # Need to flush to get the ID
                    team_name_to_id[team_name] = new_team.id
                    teams_added += 1

            # Now add all players
            for player in player_data:
                team_id = team_name_to_id[player["team_name"]]

                # Check if player already exists (by name and team or by jersey number and team)
                existing_player = (
                    db.query(Player)
                    .filter(
                        (Player.team_id == team_id)
                        & ((Player.name == player["name"]) | (Player.jersey_number == player["jersey_number"]))
                    )
                    .first()
                )

                if existing_player:
                    if (
                        existing_player.name == player["name"]
                        and existing_player.jersey_number == player["jersey_number"]
                    ):
                        # Exact match - skip
                        players_existing += 1
                    else:
                        # Conflict - either same name but different jersey, or same jersey but different name
                        conflict_type = "name" if existing_player.name == player["name"] else "jersey number"
                        typer.echo(
                            f"Warning: Player conflict for team '{player['team_name']}': "
                            f"'{player['name']}' (#{player['jersey_number']}) - "
                            f"A player with the same {conflict_type} already exists. Skipping."
                        )
                        players_error += 1
                else:
                    # Create new player
                    new_player = Player(
                        team_id=team_id,
                        name=player["name"],
                        jersey_number=player["jersey_number"],
                    )
                    db.add(new_player)
                    players_added += 1

            # Commit changes
            db.commit()

            typer.echo("\nRoster import completed:")
            typer.echo(f"Teams: {teams_added} added, {teams_existing} already existed")
            typer.echo(
                f"Players: {players_added} added, {players_existing} already existed, {players_error} errors/conflicts"
            )

            return True

    except (FileNotFoundError, PermissionError) as e:
        typer.echo(f"File error: {e}")
        return False
    except csv.Error as e:
        typer.echo(f"CSV parsing error: {e}")
        return False
    except ValueError as e:
        typer.echo(f"Data validation error: {e}")
        return False
    except OSError as e:
        typer.echo(f"I/O error: {e}")
        return False
    except Exception as e:  # pylint: disable=broad-except
        typer.echo(f"Unexpected error importing roster: {e}")
        return False


if __name__ == "__main__":
    cli()
