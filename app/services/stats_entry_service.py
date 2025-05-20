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
        self.parse_quarter_shot_string = input_parser_func
        self.shot_mapping = shot_mapping

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
        player_game_stats = create_player_game_stats(self._db_session, game_id, player_id, fouls)

        # Initialize aggregated totals
        totals = {"total_ftm": 0, "total_fta": 0, "total_2pm": 0, "total_2pa": 0, "total_3pm": 0, "total_3pa": 0}

        # Process each quarter's shot string
        for quarter_num, shot_string in enumerate(quarter_shot_strings, start=1):
            if not shot_string:
                continue  # Skip empty quarters

            # Parse the shot string
            quarter_stats = self.parse_quarter_shot_string(shot_string, self.shot_mapping)

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
        updated_stats = update_player_game_stats_totals(self._db_session, player_game_stats.id, totals)

        return updated_stats
