"""Service for converting between shot notation and statistics."""

from app.data_access.models import PlayerGameStats, PlayerQuarterStats


class ShotNotationService:
    """Converts between shot notation format and stored statistics."""

    @staticmethod
    def stats_to_notation(ftm: int, fta: int, fg2m: int, fg2a: int, fg3m: int, fg3a: int) -> str:
        """Convert statistics to shot notation string.

        Args:
            ftm: Free throws made
            fta: Free throws attempted
            fg2m: 2-point field goals made
            fg2a: 2-point field goals attempted
            fg3m: 3-point field goals made
            fg3a: 3-point field goals attempted

        Returns:
            Shot notation string (e.g., "22-3/1x")
        """
        notation = ""

        # Add 2-point shots
        notation += "2" * fg2m
        notation += "-" * (fg2a - fg2m)

        # Add 3-point shots
        notation += "3" * fg3m
        notation += "/" * (fg3a - fg3m)

        # Add free throws
        notation += "1" * ftm
        notation += "x" * (fta - ftm)

        return notation

    @staticmethod
    def player_game_stats_to_scorebook_format(
        player_game_stats: PlayerGameStats, quarter_stats: list[PlayerQuarterStats] | None = None
    ) -> dict[str, any]:
        """Convert PlayerGameStats to scorebook format.

        Args:
            player_game_stats: The player's game statistics
            quarter_stats: Optional quarter-by-quarter statistics

        Returns:
            Dictionary with scorebook-compatible format
        """
        result = {
            "player_id": player_game_stats.player_id,
            "player_name": player_game_stats.player.name,
            "jersey_number": player_game_stats.player.jersey_number,
            "team": "home" if player_game_stats.player.team_id == player_game_stats.game.playing_team_id else "away",
            "fouls": player_game_stats.fouls or 0,
            # Initialize all quarter fields to empty strings
            "shots_q1": "",
            "shots_q2": "",
            "shots_q3": "",
            "shots_q4": "",
            "shots_ot1": "",
            "shots_ot2": "",
        }

        if quarter_stats:
            # Convert quarter-by-quarter stats to notation
            for qs in quarter_stats:
                # Map quarter numbers to appropriate field names
                if qs.quarter_number <= 4:
                    quarter_key = f"shots_q{qs.quarter_number}"
                elif qs.quarter_number == 5:
                    quarter_key = "shots_ot1"
                elif qs.quarter_number == 6:
                    quarter_key = "shots_ot2"
                else:
                    # Handle additional overtime periods if needed
                    quarter_key = f"shots_ot{qs.quarter_number - 4}"

                result[quarter_key] = ShotNotationService.stats_to_notation(
                    qs.ftm or 0, qs.fta or 0, qs.fg2m or 0, qs.fg2a or 0, qs.fg3m or 0, qs.fg3a or 0
                )
        else:
            # If no quarter stats, create a single notation for Q1
            result["shots_q1"] = ShotNotationService.stats_to_notation(
                player_game_stats.total_ftm or 0,
                player_game_stats.total_fta or 0,
                player_game_stats.total_2pm or 0,
                player_game_stats.total_2pa or 0,
                player_game_stats.total_3pm or 0,
                player_game_stats.total_3pa or 0,
            )

        return result

    @staticmethod
    def game_to_scorebook_format(game, player_game_stats_list, player_quarter_stats_dict) -> dict:
        """Convert a game and its stats to scorebook format.

        Args:
            game: The game object
            player_game_stats_list: List of PlayerGameStats
            player_quarter_stats_dict: Dict mapping player_id to list of PlayerQuarterStats

        Returns:
            Dictionary with complete scorebook format
        """
        return {
            "game_info": {
                "id": game.id,
                "date": game.date.isoformat() if game.date else "",
                "home_team_id": game.playing_team_id,
                "away_team_id": game.opponent_team_id,
                "location": game.location or "",
                "notes": game.notes or "",
                "is_playoff_game": game.is_playoff_game,
            },
            "player_stats": [
                ShotNotationService.player_game_stats_to_scorebook_format(
                    pgs, player_quarter_stats_dict.get(pgs.player_id, [])
                )
                for pgs in player_game_stats_list
            ],
        }
