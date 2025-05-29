"""Orchestrates the CSV import process."""

import typer
from sqlalchemy.exc import SQLAlchemyError

import app.data_access.database_manager as db_manager
from app.schemas.csv_schemas import GameStatsCSVInputSchema

from .csv_parser import CSVParser
from .data_validator import DataValidator
from .import_processor import ImportProcessor


class ImportOrchestrator:
    """Orchestrates CSV import operations."""

    def import_roster_from_csv(self, roster_file: str, dry_run: bool = False) -> bool:
        """Import teams and players from a CSV file.

        Args:
            roster_file: Path to the roster CSV file
            dry_run: If True, validate but don't commit changes

        Returns:
            True on success, False on error
        """
        # Check if file exists
        roster_path = CSVParser.check_file_exists(roster_file)
        if not roster_path:
            return False

        try:
            # Parse CSV file
            team_data, player_data = CSVParser.read_roster_csv(roster_path)
            if not team_data or not player_data:
                return False

            # Display summary
            self._display_roster_import_summary(roster_file, team_data, player_data)

            if dry_run:
                typer.echo("\nDry run mode: No changes were made to the database.")
                return True

            # Process import
            return self._process_roster_import(team_data, player_data)

        except (FileNotFoundError, PermissionError) as e:
            typer.echo(f"File error: {e}")
            return False
        except ValueError as e:
            typer.echo(f"Data validation error: {e}")
            return False
        except Exception as e:  # pylint: disable=broad-except
            typer.echo(f"Unexpected error importing roster: {e}")
            return False

    def import_game_stats_from_csv(self, game_stats_file: str, dry_run: bool = False) -> bool:
        """Import game statistics from a CSV file.

        Args:
            game_stats_file: Path to the game stats CSV file
            dry_run: If True, validate but don't commit changes

        Returns:
            True on success, False on error
        """
        # Check if file exists
        game_stats_path = CSVParser.check_file_exists(game_stats_file)
        if not game_stats_path:
            return False

        try:
            # Parse CSV file
            csv_sections = CSVParser.read_game_stats_csv(game_stats_path)
            if not csv_sections:
                return False

            game_info_data, player_stats_header, player_stats_rows = csv_sections

            # Validate data
            validated_data = DataValidator.validate_game_stats_data(
                game_info_data, player_stats_header, player_stats_rows
            )
            if not validated_data:
                return False

            # Display summary
            self._display_game_stats_import_summary(game_stats_file, validated_data)

            if dry_run:
                typer.echo("\nDry run mode: No changes were made to the database.")
                return True

            # Process import
            return self._process_game_stats_import(validated_data)

        except (FileNotFoundError, PermissionError) as e:
            typer.echo(f"File error: {e}")
            return False
        except ValueError as e:
            typer.echo(f"Data validation error: {e}")
            return False
        except Exception as e:  # pylint: disable=broad-except
            typer.echo(f"Unexpected error importing game stats: {e}")
            return False

    def _display_roster_import_summary(self, roster_file: str, team_data: dict, player_data: list) -> None:
        """Display summary of roster import data."""
        typer.echo(f"\nParsed roster data from '{roster_file}':")
        typer.echo(f"  - Found {len(team_data)} teams")
        typer.echo(f"  - Found {len(player_data)} players")
        typer.echo("\nTeams:")
        for team_name, data in team_data.items():
            typer.echo(f"  - {team_name}: {data['player_count']} players")

    def _display_game_stats_import_summary(self, game_stats_file: str, validated_data: GameStatsCSVInputSchema) -> None:
        """Display summary of game stats import data."""
        typer.echo(f"\nParsed game data from '{game_stats_file}':")
        typer.echo(f"  - Home Team: {validated_data.game_info.Home}")
        typer.echo(f"  - Visitor Team: {validated_data.game_info.Visitor}")
        typer.echo(f"  - Date: {validated_data.game_info.Date}")
        typer.echo(f"  - Players with stats: {len(validated_data.player_stats)}")

    def _process_roster_import(self, team_data: dict, player_data: list) -> bool:
        """Process the roster import into the database."""
        db = None
        try:
            db = db_manager.get_session()
            processor = ImportProcessor(db)

            # Process teams
            teams_added, teams_existing, teams_error = processor.process_teams(team_data)

            # Commit teams before processing players
            try:
                db.commit()
            except SQLAlchemyError as e:
                typer.echo(f"Error committing teams: {e}")
                db.rollback()
                return False

            # Process players
            players_processed, players_error = processor.process_players(player_data)

            # Commit players
            try:
                db.commit()
                typer.echo("\nImport completed:")
                typer.echo(f"  - Teams: {teams_added} added, {teams_existing} existing, {teams_error} errors")
                typer.echo(f"  - Players: {players_processed} processed, {players_error} errors")
                return teams_error == 0 and players_error == 0
            except SQLAlchemyError as e:
                typer.echo(f"Error committing players: {e}")
                db.rollback()
                return False

        except SQLAlchemyError as e:
            typer.echo(f"Database error: {e}")
            return False
        finally:
            if db:
                db.close()

    def _process_game_stats_import(self, validated_data: GameStatsCSVInputSchema) -> bool:
        """Process the game stats import into the database."""
        db = None
        try:
            db = db_manager.get_session()
            processor = ImportProcessor(db)

            # Process game and stats
            success = processor.process_game_stats(validated_data)

            if success:
                db.commit()
                typer.echo("\nGame stats import completed successfully.")
            else:
                db.rollback()
                typer.echo("\nGame stats import failed.")

            return success

        except SQLAlchemyError as e:
            typer.echo(f"Database error: {e}")
            if db:
                db.rollback()
            return False
        finally:
            if db:
                db.close()
