"""Database operations for CSV imports."""

from typing import Any

import typer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import SHOT_MAPPING
from app.data_access.models import Game, Player, Team
from app.schemas.csv_schemas import GameStatsCSVInputSchema
from app.services.game_service import GameService
from app.services.game_state_service import GameStateService
from app.services.player_service import PlayerService
from app.services.score_calculation_service import ScoreCalculationService
from app.services.season_stats_service import SeasonStatsService
from app.services.stats_entry_service import StatsEntryService
from app.utils.fuzzy_matching import names_match_enhanced
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
        self.game_state_service = GameStateService(db)
        self.player_service = PlayerService(db)
        self.stats_service = StatsEntryService(db, parse_quarter_shot_string, SHOT_MAPPING)
        self.season_stats_service = SeasonStatsService(db)

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
                # Check if this is a substitute player
                is_substitute = player.get("is_substitute", False)

                if is_substitute:
                    # For substitute players, directly create in Guest Players team
                    substitute_player = self.player_service.get_or_create_substitute_player(
                        jersey_number=player["jersey_number"], player_name=player["name"]
                    )
                    if substitute_player:
                        typer.echo(f"Created substitute player: {player['name']} #{player['jersey_number']}")
                        players_processed += 1
                    else:
                        typer.echo(f"Error: Failed to create substitute player '{player['name']}'")
                        players_error += 1
                else:
                    # Regular player - needs a valid team
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
                if names_match_enhanced(existing_player.name, player_data["name"]):
                    typer.echo(
                        f"Info: Jersey #{player_data['jersey_number']} name variation accepted: "
                        f"'{existing_player.name}' → '{player_data['name']}'"
                    )
                    return True
                else:
                    typer.echo(
                        f"Error: Jersey #{player_data['jersey_number']} on team already assigned to "
                        f"'{existing_player.name}'. Cannot import '{player_data['name']}' - names too different."
                    )
                    return False
            return True

        # Create new regular player
        new_player = Player(
            team_id=team_id,
            name=player_data["name"],
            jersey_number=player_data["jersey_number"],
            is_substitute=False,
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
            home_team = self._get_or_create_team(validated_data.game_info.HomeTeam)
            visitor_team = self._get_or_create_team(validated_data.game_info.VisitorTeam)

            if not home_team or not visitor_team:
                return False

            # Convert date format if necessary
            date_str = validated_data.game_info.Date
            if "/" in date_str:
                # Convert M/D/YYYY to YYYY-MM-DD
                from datetime import datetime

                date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                date_str = date_obj.strftime("%Y-%m-%d")

            # Determine the season from the game date
            from datetime import datetime

            from app.services.season_service import SeasonService

            game_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Use SeasonService to find appropriate season
            season_service = SeasonService(self.db)
            season = season_service.get_season_for_date(game_date)

            if not season:
                # No season found for this date, check for active season
                season = season_service.get_active_season()
                if season:
                    typer.echo(
                        f"Note: Game date {date_str} is outside active season '{season.name}', but using it anyway."
                    )
                else:
                    # No seasons exist at all, create a default season
                    typer.echo("No seasons found in database. Creating default season...")

                    # Determine season based on game date
                    # Basketball seasons typically run Oct-Apr
                    year = game_date.year
                    month = game_date.month

                    # If game is in Oct-Dec, it's the start of season YYYY-(YYYY+1)
                    # If game is in Jan-Apr, it's the end of season (YYYY-1)-YYYY
                    if month >= 10:  # October or later
                        start_year = year
                        end_year = year + 1
                    else:  # January through April
                        start_year = year - 1
                        end_year = year

                    season_code = f"{start_year}-{end_year}"
                    season_name = f"Season {season_code}"

                    # Create the season
                    from datetime import date as date_type

                    success, message, season = season_service.create_season(
                        name=season_name,
                        code=season_code,
                        start_date=date_type(start_year, 10, 1),
                        end_date=date_type(end_year, 4, 30),
                        description="Auto-created during game import",
                        set_as_active=True,
                    )

                    if success and season:
                        typer.echo(f"Created season: {season_name}")
                    else:
                        typer.echo(f"Warning: Could not create season - {message}")
                        # Continue without season association

            # Get or create the game (handles duplicates gracefully)
            game = self.game_service.add_game(
                date=date_str,
                playing_team_name=home_team.name,
                opponent_team_name=visitor_team.name,
            )

            if not game:
                typer.echo("Error: Failed to create game.")
                return False

            # Update season if needed
            if season and not game.season_id:
                game.season_id = season.id
                self.db.flush()

            typer.echo(f"\nProcessing game: {home_team.name} vs {visitor_team.name} on {validated_data.game_info.Date}")

            # Process player statistics
            players_processed = 0
            players_error = 0

            for player_stats in validated_data.player_stats:
                success = self._process_player_game_stats(game, player_stats)
                if success:
                    players_processed += 1
                else:
                    players_error += 1

            # Update game scores (let orchestrator handle commits)
            ScoreCalculationService.update_game_scores(self.db, game, commit=False)

            typer.echo(f"\nProcessed {players_processed} player stats successfully.")
            if players_error > 0:
                typer.echo(f"Failed to process {players_error} player stats.")

            # Update season statistics for all players who played in this game
            if players_processed > 0:
                typer.echo("\nUpdating season statistics...")
                try:
                    # Use the season code from the game's associated Season object
                    if game.season_id and game.season:
                        season_code = game.season.code
                    else:
                        # Fallback to date-based season
                        season_code = self.season_stats_service.get_season_from_date(game.date)

                    # Get all unique player IDs from this game
                    player_ids = set()
                    for player_stats in validated_data.player_stats:
                        # Get the team
                        team = self.db.query(Team).filter(Team.name == player_stats.TeamName).first()
                        if team:
                            # Get the player
                            player = (
                                self.db.query(Player)
                                .filter(Player.team_id == team.id, Player.jersey_number == player_stats.PlayerJersey)
                                .first()
                            )
                            if player:
                                player_ids.add(player.id)

                    # Update season stats for each player
                    for player_id in player_ids:
                        try:
                            self.season_stats_service.update_player_season_stats(player_id, season_code)
                        except Exception as e:
                            typer.echo(f"Warning: Failed to update season stats for player {player_id}: {e}")

                    # Update team season stats
                    try:
                        self.season_stats_service.update_team_season_stats(home_team.id, season_code)
                        self.season_stats_service.update_team_season_stats(visitor_team.id, season_code)
                    except Exception as e:
                        typer.echo(f"Warning: Failed to update team season stats: {e}")

                    typer.echo("Season statistics updated.")
                except Exception as e:
                    typer.echo(f"Warning: Season statistics update failed: {e}")
                    # Don't let season stats failure break the import

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
        # Skip players with empty jersey numbers or team names
        if not player_stats.PlayerJersey or not player_stats.PlayerJersey.strip():
            typer.echo(f"Warning: Skipping player with empty jersey number: {player_stats.PlayerName}")
            return True  # Return True to not fail the entire import

        if not player_stats.TeamName or not player_stats.TeamName.strip():
            typer.echo(f"Warning: Skipping player with empty team name: {player_stats.PlayerName}")
            return True  # Return True to not fail the entire import

        # Get the team
        team = self.db.query(Team).filter(Team.name == player_stats.TeamName).first()
        if not team:
            typer.echo(f"Error: Team '{player_stats.TeamName}' not found.")
            return False

        # Check if this is a substitute player
        playing_for_team_id = None

        # Check if this is an unknown/unidentified shot
        if player_stats.PlayerName and player_stats.PlayerName.strip().lower() in ["unknown", "unidentified"]:
            # Create a special "Unknown Player" entry for this team and game
            player_name = f"Unknown #{player_stats.PlayerJersey} ({team.name})"
            player = self.player_service.get_or_create_player(
                team_id=team.id, jersey_number=player_stats.PlayerJersey, player_name=player_name
            )
            if not player:
                typer.echo("Error: Could not create unknown player entry.")
                return False
        # Check if this is a known substitute player
        elif self._is_substitute_player(player_stats.PlayerName, player_stats.PlayerJersey):
            playing_for_team_id = team.id

            # Get or create substitute player
            player = self.player_service.get_or_create_substitute_player(
                jersey_number=player_stats.PlayerJersey, player_name=player_stats.PlayerName
            )
            if not player:
                typer.echo(f"Error: Could not create substitute player #{player_stats.PlayerJersey}.")
                return False
        else:
            # Regular team player
            player = self.player_service.get_or_create_player(
                team_id=team.id, jersey_number=player_stats.PlayerJersey, player_name=player_stats.PlayerName
            )
            if not player:
                typer.echo(
                    f"Error: Could not get or create player '{player_stats.PlayerName}' "
                    f"#{player_stats.PlayerJersey} on team '{player_stats.TeamName}'."
                )
                return False

        # Process quarter statistics
        for i, quarter_key in enumerate(["QT1Shots", "QT2Shots", "QT3Shots", "QT4Shots", "OT1Shots", "OT2Shots"]):
            quarter = i + 1
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
                            playing_for_team_id=playing_for_team_id,
                        )
                    except ValueError as e:
                        typer.echo(f"Warning: Invalid shot string for {player.name} Q{quarter}: {e}")

        return True

    def _is_substitute_player(self, player_name: str | None, jersey_number: str) -> bool:
        """
        Determine if a player is a substitute based on name and jersey number.

        Args:
            player_name: Player's name
            jersey_number: Player's jersey number

        Returns:
            True if this is likely a substitute player
        """
        if not player_name:
            return False

        # Check if this player exists in the Guest Players team
        guest_team = self.db.query(Team).filter_by(name="Guest Players").first()
        if not guest_team:
            return False

        # Check if player exists as a substitute
        existing_player = (
            self.db.query(Player)
            .filter_by(team_id=guest_team.id, name=player_name, jersey_number=jersey_number, is_substitute=True)
            .first()
        )

        return existing_player is not None
