"""Service layer for playoff-related operations."""

from datetime import date
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, joinedload

from app.data_access.models import Game, ScheduledGame, ScheduledGameStatus


class GameNotFoundError(Exception):
    """Raised when a game is not found."""
    pass


class InvalidPlayoffGameError(Exception):
    """Raised when a game cannot be marked as playoff."""
    pass


class InvalidSeasonError(Exception):
    """Raised when season validation fails."""
    pass


class PlayoffsService:
    """Service for managing playoff bracket data and operations."""

    def __init__(self, db_session: Session):
        """Initialize the playoffs service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def _validate_season(self, season: str) -> int:
        """Validate and sanitize season input."""
        try:
            year = int(season)
            if year < 2000 or year > 2100:
                raise InvalidSeasonError("Season year must be between 2000 and 2100")
            return year
        except (ValueError, TypeError) as e:
            raise InvalidSeasonError(f"Invalid season format: {season}") from e

    def get_playoff_bracket(self, season: str | None = None) -> dict[str, Any]:
        """Get playoff bracket data for display.

        Args:
            season: Season year (e.g., "2025"). If None, gets current season playoffs.

        Returns:
            Dictionary containing bracket structure with teams and scores
        """
        # Get all completed playoff games
        completed_games_query = (
            select(Game)
            .options(
                joinedload(Game.playing_team),
                joinedload(Game.opponent_team),
            )
            .where(Game.is_playoff_game)
        )

        # Get all scheduled playoff games
        scheduled_games_query = (
            select(ScheduledGame)
            .options(
                joinedload(ScheduledGame.home_team),
                joinedload(ScheduledGame.away_team),
            )
            .where(
                and_(
                    ScheduledGame.is_playoff_game,
                    ScheduledGame.status == ScheduledGameStatus.SCHEDULED,
                    ScheduledGame.is_deleted.is_not(True),
                )
            )
        )

        if season:
            # Validate and filter by season year in the date
            validated_year = self._validate_season(season)
            start_date = date(validated_year, 1, 1)
            end_date = date(validated_year, 12, 31)
            completed_games_query = completed_games_query.where(and_(Game.date >= start_date, Game.date <= end_date))
            scheduled_games_query = scheduled_games_query.where(
                and_(ScheduledGame.scheduled_date >= start_date, ScheduledGame.scheduled_date <= end_date)
            )

        completed_games = self.db.execute(completed_games_query).scalars().all()
        scheduled_games = self.db.execute(scheduled_games_query).scalars().all()

        # Combine both types of games
        all_playoff_matchups = []

        # Add completed games
        for game in completed_games:
            all_playoff_matchups.append({"type": "completed", "data": game, "date": game.date})

        # Add scheduled games
        for game in scheduled_games:
            all_playoff_matchups.append({"type": "scheduled", "data": game, "date": game.scheduled_date})

        if not all_playoff_matchups:
            # Get playoff configuration to determine bracket structure
            config = self._get_playoff_config(season)
            return self._create_empty_bracket(config)

        # Sort all matchups by date to identify rounds
        sorted_matchups = sorted(all_playoff_matchups, key=lambda m: m["date"], reverse=True)

        bracket_data = {
            "season": season or str(sorted_matchups[0]["date"].year),
            "champion": None,
            "finals": None,
            "semi_finals": [],
        }

        # Group games by date to handle same-day games properly
        games_by_date = {}
        for matchup in sorted_matchups:
            date_key = matchup["date"]
            if date_key not in games_by_date:
                games_by_date[date_key] = []
            games_by_date[date_key].append(matchup)

        # Sort dates to get chronological order (latest first for playoffs)
        sorted_dates = sorted(games_by_date.keys(), reverse=True)

        # Assign rounds based on simple heuristics:
        # - If there's only 1 game total, it's the finals
        # - If there are 2-3 games total, the latest is finals, others are semi-finals
        # - If there are 4+ games, we need better logic (for now, treat conservatively)

        total_games = len(sorted_matchups)

        if total_games == 1:
            # Single game = Finals
            bracket_data["finals"] = self._format_matchup_data(sorted_matchups[0])
        elif total_games <= 3:
            # 2-3 games: Latest date is finals, others are semi-finals
            if sorted_dates:
                latest_date_games = games_by_date[sorted_dates[0]]
                if len(latest_date_games) == 1:
                    # Single game on latest date = Finals
                    bracket_data["finals"] = self._format_matchup_data(latest_date_games[0])
                    # Rest are semi-finals
                    for i in range(1, len(sorted_matchups)):
                        bracket_data["semi_finals"].append(self._format_matchup_data(sorted_matchups[i]))
                else:
                    # Multiple games on same latest date = all are semi-finals for now
                    # This handles your current case where 2 games on same day should both be semi-finals
                    for matchup in sorted_matchups:
                        bracket_data["semi_finals"].append(self._format_matchup_data(matchup))

                    # Fill in TBD finals if no finals game exists
                    if not bracket_data["finals"]:
                        bracket_data["finals"] = self._create_tbd_matchup("Finals")

            # Ensure we always have exactly 2 semi-final slots
            while len(bracket_data["semi_finals"]) < 2:
                slot_num = len(bracket_data["semi_finals"]) + 1
                bracket_data["semi_finals"].append(self._create_tbd_matchup(f"Semi-Finals Game {slot_num}"))
        else:
            # 4+ games: More complex bracket structure needed
            # For now, be conservative and treat later dates as later rounds
            if sorted_dates:
                latest_date_games = games_by_date[sorted_dates[0]]
                if len(latest_date_games) == 1:
                    bracket_data["finals"] = self._format_matchup_data(latest_date_games[0])
                    # Next games are semi-finals
                    semi_count = 0
                    for i in range(1, len(sorted_matchups)):
                        if semi_count < 2:  # Limit to 2 semi-final games
                            bracket_data["semi_finals"].append(self._format_matchup_data(sorted_matchups[i]))
                            semi_count += 1
                else:
                    # Multiple games on latest date - treat as semi-finals
                    for matchup in sorted_matchups[:3]:  # Take up to 3 as semi-finals
                        bracket_data["semi_finals"].append(self._format_matchup_data(matchup))
                    # Add TBD finals if no finals exists
                    if not bracket_data["finals"]:
                        bracket_data["finals"] = self._create_tbd_matchup("Finals")

        # Ensure we always have exactly 2 semi-final slots and 1 finals slot
        while len(bracket_data["semi_finals"]) < 2:
            slot_num = len(bracket_data["semi_finals"]) + 1
            bracket_data["semi_finals"].append(self._create_tbd_matchup(f"Semi-Finals Game {slot_num}"))

        if not bracket_data["finals"]:
            bracket_data["finals"] = self._create_tbd_matchup("Finals")

        # Determine champion if final game has been played and has scores
        if bracket_data["finals"]:
            final_matchup_data = bracket_data["finals"]["matchup"]
            if final_matchup_data["status"] == "completed":
                team1_score = final_matchup_data["team1"]["score"]
                team2_score = final_matchup_data["team2"]["score"]
                if team1_score is not None and team2_score is not None:
                    if team1_score > team2_score:
                        bracket_data["champion"] = {
                            "team_id": final_matchup_data["team1"]["team_id"],
                            "team_name": final_matchup_data["team1"]["team_name"],
                        }
                    else:
                        bracket_data["champion"] = {
                            "team_id": final_matchup_data["team2"]["team_id"],
                            "team_name": final_matchup_data["team2"]["team_name"],
                        }

        return bracket_data

    def _create_tbd_matchup(self, matchup_name: str) -> dict[str, Any]:
        """Create a TBD (To Be Determined) matchup placeholder.

        Args:
            matchup_name: Name/description of the matchup (e.g., "Finals", "Semi-Finals Game 1")

        Returns:
            Dictionary with TBD matchup data
        """
        return {
            "matchup": {
                "game_id": f"tbd-{matchup_name.lower().replace(' ', '-')}",
                "date": None,
                "status": "tbd",
                "team1": {
                    "team_id": None,
                    "team_name": "TBD",
                    "score": None,
                },
                "team2": {
                    "team_id": None,
                    "team_name": "TBD",
                    "score": None,
                },
            }
        }

    def _format_matchup_data(self, matchup: dict[str, Any]) -> dict[str, Any]:
        """Format a matchup (completed game or scheduled game) into bracket display format.

        Args:
            matchup: Dictionary with 'type', 'data', and 'date' keys

        Returns:
            Dictionary with formatted matchup data
        """
        matchup_type = matchup["type"]
        game_data = matchup["data"]

        if matchup_type == "completed":
            # Format completed game
            return {
                "matchup": {
                    "game_id": game_data.id,
                    "date": game_data.date.isoformat(),
                    "status": "completed",
                    "team1": {
                        "team_id": game_data.playing_team_id,
                        "team_name": game_data.playing_team.name,
                        "score": game_data.playing_team_score,
                    },
                    "team2": {
                        "team_id": game_data.opponent_team_id,
                        "team_name": game_data.opponent_team.name,
                        "score": game_data.opponent_team_score,
                    },
                }
            }
        else:
            # Format scheduled game
            return {
                "matchup": {
                    "game_id": f"scheduled-{game_data.id}",
                    "date": game_data.scheduled_date.isoformat(),
                    "status": "scheduled",
                    "team1": {
                        "team_id": game_data.home_team_id,
                        "team_name": game_data.home_team.name,
                        "score": None,
                    },
                    "team2": {
                        "team_id": game_data.away_team_id,
                        "team_name": game_data.away_team.name,
                        "score": None,
                    },
                }
            }

    def _format_game_data(self, game: Game) -> dict[str, Any]:
        """Format a game into bracket display format.

        Args:
            game: Game model instance

        Returns:
            Dictionary with formatted game data
        """
        return {
            "matchup": {
                "game_id": game.id,
                "date": game.date.isoformat(),
                "team1": {
                    "team_id": game.playing_team_id,
                    "team_name": game.playing_team.name,
                    "score": game.playing_team_score,
                },
                "team2": {
                    "team_id": game.opponent_team_id,
                    "team_name": game.opponent_team.name,
                    "score": game.opponent_team_score,
                },
            }
        }

    def mark_game_as_playoff(self, game_id: int) -> Game:
        """Mark a game as a playoff game.

        Args:
            game_id: ID of the game to mark as playoff

        Returns:
            Updated Game model instance
        """
        game = self.db.get(Game, game_id)
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found")

        game.is_playoff_game = True
        self.db.commit()
        return game

    def unmark_game_as_playoff(self, game_id: int) -> Game:
        """Remove playoff designation from a game.

        Args:
            game_id: ID of the game to unmark as playoff

        Returns:
            Updated Game model instance
        """
        game = self.db.get(Game, game_id)
        if not game:
            raise GameNotFoundError(f"Game with ID {game_id} not found")

        game.is_playoff_game = False
        self.db.commit()
        return game

    def determine_playoff_round(self, game_id: int | str) -> str | None:
        """Determine the playoff round for a given game.

        Args:
            game_id: ID of the game (can be int for completed games or "scheduled-X" for scheduled games)

        Returns:
            String representing the round (e.g., "Quarter-Finals", "Semi-Finals", "Finals") or None if not playoff
        """
        # Get all playoff games to determine context
        bracket_data = self.get_playoff_bracket()

        # Check if there are any actual playoff games (not just TBD placeholders)
        has_real_games = False
        if bracket_data["finals"] and bracket_data["finals"]["matchup"]["status"] != "tbd":
            has_real_games = True
        for semi in bracket_data["semi_finals"]:
            if semi["matchup"]["status"] != "tbd":
                has_real_games = True
                break

        if not has_real_games:
            return None

        # Convert game_id to string for comparison
        game_id_str = str(game_id)

        # Check if this is the finals game
        if bracket_data["finals"] and str(bracket_data["finals"]["matchup"]["game_id"]) == game_id_str:
            return "Finals"

        # Check if this is a semi-finals game
        for semi in bracket_data["semi_finals"]:
            if str(semi["matchup"]["game_id"]) == game_id_str:
                return "Semi-Finals"

        # If we have more than 3 total games and this game is not in finals/semi-finals,
        # it could be a quarter-finals game
        total_games = len(bracket_data["semi_finals"]) + (1 if bracket_data["finals"] else 0)
        if total_games >= 3:
            # Check if this game exists in our playoff system but wasn't categorized
            # For now, assume any other playoff game is quarter-finals
            return "Quarter-Finals"

        return None

    def _get_playoff_config(self, season: str | None) -> dict[str, Any]:
        """Get playoff configuration for the given season.

        Args:
            season: Season year (e.g., "2025")

        Returns:
            Dictionary with playoff configuration
        """
        from app.data_access.models import PlayoffConfig

        if season:
            # Validate season if provided
            validated_year = self._validate_season(season)
            current_season = str(validated_year)
        else:
            current_season = str(date.today().year)

        config = (
            self.db.query(PlayoffConfig).filter(PlayoffConfig.season == current_season, PlayoffConfig.is_active).first()
        )

        if not config:
            # Return default configuration for 8 teams
            return {"season": current_season, "num_teams": 8, "num_rounds": 3, "bracket_type": "single_elimination"}

        return {
            "season": config.season,
            "num_teams": config.num_teams,
            "num_rounds": config.num_rounds,
            "bracket_type": config.bracket_type,
        }

    def _create_empty_bracket(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create an empty bracket structure based on configuration.

        Args:
            config: Playoff configuration dictionary

        Returns:
            Empty bracket structure with TBD placeholders
        """
        num_teams = config["num_teams"]
        season = config["season"]

        bracket = {
            "season": season,
            "champion": None,
            "finals": None,
        }

        # Create rounds based on number of teams
        if num_teams == 4:
            # 4 teams: Semi-Finals (2 games) → Finals (1 game)
            bracket.update(
                {
                    "finals": self._create_tbd_matchup("Finals"),
                    "semi_finals": [
                        self._create_tbd_matchup("Semi-Finals Game 1"),
                        self._create_tbd_matchup("Semi-Finals Game 2"),
                    ],
                }
            )
        elif num_teams == 8:
            # 8 teams: Quarter-Finals (4 games) → Semi-Finals (2 games) → Finals (1 game)
            bracket.update(
                {
                    "finals": self._create_tbd_matchup("Finals"),
                    "semi_finals": [
                        self._create_tbd_matchup("Semi-Finals Game 1"),
                        self._create_tbd_matchup("Semi-Finals Game 2"),
                    ],
                    "quarter_finals": [
                        self._create_tbd_matchup("Quarter-Finals Game 1"),
                        self._create_tbd_matchup("Quarter-Finals Game 2"),
                        self._create_tbd_matchup("Quarter-Finals Game 3"),
                        self._create_tbd_matchup("Quarter-Finals Game 4"),
                    ],
                }
            )
        elif num_teams == 16:
            # 16 teams: Round of 16 → Quarter-Finals → Semi-Finals → Finals
            bracket.update(
                {
                    "finals": self._create_tbd_matchup("Finals"),
                    "semi_finals": [
                        self._create_tbd_matchup("Semi-Finals Game 1"),
                        self._create_tbd_matchup("Semi-Finals Game 2"),
                    ],
                    "quarter_finals": [
                        self._create_tbd_matchup("Quarter-Finals Game 1"),
                        self._create_tbd_matchup("Quarter-Finals Game 2"),
                        self._create_tbd_matchup("Quarter-Finals Game 3"),
                        self._create_tbd_matchup("Quarter-Finals Game 4"),
                    ],
                    "round_of_16": [self._create_tbd_matchup(f"Round of 16 Game {i}") for i in range(1, 9)],
                }
            )
        else:
            # Default to semi-finals structure for other team counts
            bracket.update(
                {
                    "finals": self._create_tbd_matchup("Finals"),
                    "semi_finals": [
                        self._create_tbd_matchup("Semi-Finals Game 1"),
                        self._create_tbd_matchup("Semi-Finals Game 2"),
                    ],
                }
            )

        return bracket
