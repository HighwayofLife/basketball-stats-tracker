"""Database operations for CSV imports."""

from typing import Any

import typer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import SHOT_MAPPING
from app.data_access.models import Game, Player, Team
from app.schemas.csv_schemas import GameStatsCSVInputSchema
from app.services.game_service import GameService
from app.services.player_service import PlayerService
from app.services.score_calculation_service import ScoreCalculationService
from app.services.stats_entry_service import StatsEntryService
from app.utils.input_parser import parse_quarter_shot_string


class ImportProcessor:
    """Handles database operations for CSV imports."""

    def __init__(self, db: Session):
        """Initialize the import processor.

        Args:
            db: Database session
        """
        self.db = db
        self.game_service = GameService(db)
        self.player_service = PlayerService(db)
        self.stats_service = StatsEntryService(db)

    def process_teams(self, team_data: dict[str, dict[str, int]]) -> tuple[int, int, int]:
        """Process team imports.

        Args:
            team_data: Dictionary of team names and their data

        Returns:
            Tuple of (teams_added, teams_existing, teams_error)
        """
        teams_added = 0
        teams_existing = 0
        teams_error = 0

        for team_name in team_data:
            try:
                existing_team = self.db.query(Team).filter(Team.name == team_name).first()
                if existing_team:
                    teams_existing += 1
                else:
                    new_team = Team(name=team_name)
                    self.db.add(new_team)
                    teams_added += 1
            except SQLAlchemyError as e:
                typer.echo(f"Error adding team '{team_name}': {e}")
                teams_error += 1

        return teams_added, teams_existing, teams_error

    def process_players(self, player_data: list[dict[str, Any]]) -> tuple[int, int]:
        """Process player imports.

        Args:
            player_data: List of player data dictionaries

        Returns:
            Tuple of (players_processed, players_error)
        """
        players_processed = 0
        players_error = 0

        for player in player_data:
            try:
                team = self.db.query(Team).filter(Team.name == player["team_name"]).first()
                if not team:
                    typer.echo(f"Error: Team '{player['team_name']}' not found for player '{player['name']}'")
                    players_error += 1
                    continue

                result = self._add_or_update_player(team.id, player)
                if result:
                    players_processed += 1
                else:
                    players_error += 1
            except SQLAlchemyError as e:
                typer.echo(f"Error processing player '{player['name']}': {e}")
                players_error += 1

        return players_processed, players_error

    def _add_or_update_player(self, team_id: int, player_data: dict[str, Any]) -> bool:
        """Add or update a single player.

        Args:
            team_id: ID of the team
            player_data: Player data dictionary

        Returns:
            True if successful, False otherwise
        """
        existing_player = (
            self.db.query(Player)
            .filter(Player.team_id == team_id, Player.jersey_number == player_data["jersey_number"])
            .first()
        )

        if existing_player:
            if existing_player.name != player_data["name"]:
                typer.echo(
                    f"Warning: Jersey #{player_data['jersey_number']} on team already assigned to "
                    f"'{existing_player.name}'. Skipping '{player_data['name']}'."
                )
                return False
            return True

        # Create new player
        new_player = Player(
            team_id=team_id,
            name=player_data["name"],
            jersey_number=player_data["jersey_number"],
        )

        # Add optional fields
        if "position" in player_data:
            new_player.position = player_data["position"]
        if "height" in player_data:
            new_player.height = player_data["height"]
        if "weight" in player_data:
            new_player.weight = player_data["weight"]
        if "year" in player_data:
            new_player.year = player_data["year"]

        self.db.add(new_player)
        return True

    def process_game_stats(self, validated_data: GameStatsCSVInputSchema) -> bool:
        """Process game statistics import.

        Args:
            validated_data: Validated game statistics data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create teams
            home_team = self._get_or_create_team(validated_data.game_info.Home)
            visitor_team = self._get_or_create_team(validated_data.game_info.Visitor)

            if not home_team or not visitor_team:
                return False

            # Create the game
            game = self.game_service.create_game(
                date=validated_data.game_info.Date,
                playing_team_id=home_team.id,
                opponent_team_id=visitor_team.id,
            )

            if not game:
                typer.echo("Error: Failed to create game.")
                return False

            typer.echo(f"\nCreated game: {home_team.name} vs {visitor_team.name} on {validated_data.game_info.Date}")

            # Process player statistics
            players_processed = 0
            players_error = 0

            for player_stats in validated_data.player_stats:
                success = self._process_player_game_stats(game, player_stats)
                if success:
                    players_processed += 1
                else:
                    players_error += 1

            # Update game scores
            ScoreCalculationService.update_game_scores(self.db, game)

            typer.echo(f"\nProcessed {players_processed} player stats successfully.")
            if players_error > 0:
                typer.echo(f"Failed to process {players_error} player stats.")

            return players_error == 0

        except SQLAlchemyError as e:
            typer.echo(f"Database error: {e}")
            self.db.rollback()
            return False

    def _get_or_create_team(self, team_name: str) -> Team | None:
        """Get existing team or create new one.

        Args:
            team_name: Name of the team

        Returns:
            Team object or None if creation fails
        """
        team = self.db.query(Team).filter(Team.name == team_name).first()
        if not team:
            try:
                team = Team(name=team_name)
                self.db.add(team)
                self.db.flush()
                typer.echo(f"Created new team: {team_name}")
            except SQLAlchemyError as e:
                typer.echo(f"Error creating team '{team_name}': {e}")
                return None
        return team

    def _process_player_game_stats(self, game: Game, player_stats: Any) -> bool:
        """Process statistics for a single player in a game.

        Args:
            game: The game object
            player_stats: Player statistics from CSV

        Returns:
            True if successful, False otherwise
        """
        # Get the team
        team = self.db.query(Team).filter(Team.name == player_stats.team_name).first()
        if not team:
            typer.echo(f"Error: Team '{player_stats.team_name}' not found.")
            return False

        # Get or create the player
        player = self.player_service.get_or_create_player(
            team_id=team.id, jersey_number=player_stats.jersey_number, player_name=player_stats.player_name
        )
        if not player:
            typer.echo(
                f"Error: Could not get or create player '{player_stats.player_name}' #{player_stats.jersey_number} on team '{player_stats.team_name}'."
            )
            return False

        # Process quarter statistics
        for quarter in range(1, 5):
            quarter_key = f"quarter_{quarter}"
            if hasattr(player_stats, quarter_key):
                shot_string = getattr(player_stats, quarter_key)
                if shot_string and shot_string.strip():
                    try:
                        shot_stats = parse_quarter_shot_string(shot_string, shot_mapping=SHOT_MAPPING)
                        self.stats_service.add_player_quarter_stats(
                            game_id=game.id,
                            player_id=player.id,
                            quarter=quarter,
                            stats=shot_stats,
                        )
                    except ValueError as e:
                        typer.echo(f"Warning: Invalid shot string for {player.name} Q{quarter}: {e}")

        # Process overtime if present
        if hasattr(player_stats, "overtime") and player_stats.overtime and player_stats.overtime.strip():
            try:
                shot_stats = parse_quarter_shot_string(player_stats.overtime, shot_mapping=SHOT_MAPPING)
                self.stats_service.add_player_quarter_stats(
                    game_id=game.id,
                    player_id=player.id,
                    quarter=5,  # OT is quarter 5
                    stats=shot_stats,
                )
            except ValueError as e:
                typer.echo(f"Warning: Invalid shot string for {player.name} OT: {e}")

        return True
