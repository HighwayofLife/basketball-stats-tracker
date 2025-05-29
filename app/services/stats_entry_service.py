"""
Service for recording and processing player game statistics.
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.data_access.crud import (
    create_player_game_stats,
    create_player_quarter_stats,
    update_player_game_stats_totals,
)
from app.data_access.models import PlayerGameStats


class StatsEntryService:
    """
    Service class for recording player game statistics.
    """

    def __init__(self, db_session: Session, input_parser_func: Callable, shot_mapping: dict):
        """
        Initialize the StatsEntryService with a database session.

        Args:
            db_session: SQLAlchemy session for database operations
            input_parser_func: Function to parse quarter shot strings
            shot_mapping: Dictionary mapping shot characters to their properties
        """
        self._db_session = db_session
        self._parse_shot_string = input_parser_func
        self._shot_mapping = shot_mapping

    def record_player_game_performance(
        self, game_id: int, player_id: int, fouls: int, quarter_shot_strings: list[str]
    ) -> PlayerGameStats:
        """
        Record a player's performance in a game, including quarter-by-quarter stats.

        Args:
            game_id: ID of the game
            player_id: ID of the player
            fouls: Number of fouls committed by the player
            quarter_shot_strings: List of shot strings for each quarter (up to 4)

        Returns:
            The created PlayerGameStats instance with updated totals
        """
        # Create the basic player game stats record with fouls
        player_game_stats = create_player_game_stats(
            self._db_session,
            game_id=game_id,
            player_id=player_id,
            fouls=fouls,
        )

        # Initialize aggregated totals
        totals = {"total_ftm": 0, "total_fta": 0, "total_2pm": 0, "total_2pa": 0, "total_3pm": 0, "total_3pa": 0}

        # Always process 4 quarters, fill missing with empty string
        for quarter_num in range(1, 5):
            try:
                shot_string = quarter_shot_strings[quarter_num - 1]
            except IndexError:
                shot_string = ""

            # Parse the shot string (empty string yields all zeros)
            quarter_stats = self._parse_shot_string(shot_string, self._shot_mapping)

            # Record quarter stats in the database
            create_player_quarter_stats(
                self._db_session,
                player_game_stats.id,
                quarter_num,
                {
                    "ftm": quarter_stats["ftm"],
                    "fta": quarter_stats["fta"],
                    "fg2m": quarter_stats["fg2m"],
                    "fg2a": quarter_stats["fg2a"],
                    "fg3m": quarter_stats["fg3m"],
                    "fg3a": quarter_stats["fg3a"],
                },
            )

            # Aggregate stats
            totals["total_ftm"] += quarter_stats["ftm"]
            totals["total_fta"] += quarter_stats["fta"]
            totals["total_2pm"] += quarter_stats["fg2m"]
            totals["total_2pa"] += quarter_stats["fg2a"]
            totals["total_3pm"] += quarter_stats["fg3m"]
            totals["total_3pa"] += quarter_stats["fg3a"]

        # Update player game stats with totals
        updated_stats = update_player_game_stats_totals(
            self._db_session,
            player_game_stat_id=player_game_stats.id,
            totals=totals,
        )

        return updated_stats

    def add_player_quarter_stats(
        self, game_id: int, player_id: int, quarter: int, stats: dict, playing_for_team_id: int | None = None
    ) -> bool:
        """
        Add statistics for a specific quarter for a player.

        Args:
            game_id: ID of the game
            player_id: ID of the player
            quarter: Quarter number (1-4 for regular, 5 for OT)
            stats: Dictionary with shooting stats
            playing_for_team_id: ID of team the player is playing for (for substitutes)

        Returns:
            True if successful
        """
        from app.data_access.crud.crud_player_game_stats import get_player_game_stats_by_game_and_player

        try:
            # Get or create player game stats
            player_game_stats = get_player_game_stats_by_game_and_player(self._db_session, game_id, player_id)

            if not player_game_stats:
                # Create new player game stats
                player_game_stats = create_player_game_stats(
                    self._db_session,
                    game_id=game_id,
                    player_id=player_id,
                    fouls=0,
                    playing_for_team_id=playing_for_team_id,
                )
            elif playing_for_team_id and not player_game_stats.playing_for_team_id:
                # Update playing_for_team_id if it's a substitute
                player_game_stats.playing_for_team_id = playing_for_team_id
                self._db_session.commit()

            # Create quarter stats
            create_player_quarter_stats(
                self._db_session,
                player_game_stats.id,
                quarter,
                {
                    "ftm": stats.get("ftm", 0),
                    "fta": stats.get("fta", 0),
                    "fg2m": stats.get("fg2m", 0),
                    "fg2a": stats.get("fg2a", 0),
                    "fg3m": stats.get("fg3m", 0),
                    "fg3a": stats.get("fg3a", 0),
                },
            )

            # Update totals
            self._update_player_game_totals(player_game_stats.id)

            return True

        except Exception as e:
            print(f"Error adding quarter stats: {e}")
            self._db_session.rollback()
            return False

    def _update_player_game_totals(self, player_game_stat_id: int) -> None:
        """Update the total statistics for a player's game from quarter stats."""
        from app.data_access.crud.crud_player_quarter_stats import get_player_quarter_stats_by_game_stat

        # Get all quarter stats
        quarter_stats = get_player_quarter_stats_by_game_stat(self._db_session, player_game_stat_id)

        # Calculate totals
        totals = {
            "total_ftm": sum(q.ftm for q in quarter_stats),
            "total_fta": sum(q.fta for q in quarter_stats),
            "total_2pm": sum(q.fg2m for q in quarter_stats),
            "total_2pa": sum(q.fg2a for q in quarter_stats),
            "total_3pm": sum(q.fg3m for q in quarter_stats),
            "total_3pa": sum(q.fg3a for q in quarter_stats),
        }

        # Update player game stats with totals
        update_player_game_stats_totals(
            self._db_session,
            player_game_stat_id=player_game_stat_id,
            totals=totals,
        )
