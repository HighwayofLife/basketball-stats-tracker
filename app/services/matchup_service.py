"""Service for handling game matchup/preview data for scheduled games."""

import logging
from typing import Any

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.data_access.crud import get_team_by_id
from app.data_access.models import Game, Player, PlayerSeasonStats, ScheduledGame, TeamSeasonStats

logger = logging.getLogger(__name__)


class MatchupService:
    """Service for generating matchup preview data for scheduled games."""

    def __init__(self, db: Session):
        """Initialize the matchup service with a database session."""
        self.db = db

    def get_matchup_data(self, scheduled_game_id: int) -> dict[str, Any] | None:
        """
        Get comprehensive matchup data for a scheduled game.

        Args:
            scheduled_game_id: The ID of the scheduled game

        Returns:
            Dictionary containing matchup data or None if game not found
        """
        # Fetch the scheduled game
        scheduled_game = self.db.query(ScheduledGame).filter(ScheduledGame.id == scheduled_game_id).first()
        if not scheduled_game:
            logger.warning(f"Scheduled game {scheduled_game_id} not found")
            return None

        # Get team objects
        home_team = get_team_by_id(self.db, scheduled_game.home_team_id)
        away_team = get_team_by_id(self.db, scheduled_game.away_team_id)

        if not home_team or not away_team:
            logger.error(f"Teams not found for scheduled game {scheduled_game_id}")
            return None

        # Get season string from scheduled game
        season_string = self._get_season_string(scheduled_game.season_id) if scheduled_game.season_id else "2024-2025"

        # Compile matchup data
        matchup_data = {
            "scheduled_game": scheduled_game,
            "home_team": {
                "team": home_team,
                "season_stats": self._get_team_season_stats(home_team.id, season_string),
                "top_players": self._get_player_season_stats(home_team.id, season_string),
            },
            "away_team": {
                "team": away_team,
                "season_stats": self._get_team_season_stats(away_team.id, season_string),
                "top_players": self._get_player_season_stats(away_team.id, season_string),
            },
            "head_to_head": self._get_head_to_head_history(home_team.id, away_team.id),
        }

        return matchup_data

    def _get_season_string(self, season_id: int) -> str:
        """
        Get season string from season ID.

        Args:
            season_id: The season ID

        Returns:
            Season string (e.g., "2024-2025")
        """
        from app.data_access.models import Season

        season = self.db.query(Season).filter(Season.id == season_id).first()
        if season:
            # Convert season name to format like "2024-2025"
            if "-" in season.name:
                return season.name
            # Otherwise create from dates
            start_year = season.start_date.year
            end_year = season.end_date.year if season.end_date.year != start_year else start_year + 1
            return f"{start_year}-{end_year}"
        return "2024-2025"  # Default fallback

    def _get_team_season_stats(self, team_id: int, season: str) -> dict[str, Any] | None:
        """
        Get team season statistics with computed fields.

        Args:
            team_id: The team ID
            season: The season string (e.g., "2024-2025")

        Returns:
            Dict with computed stats or None if not found
        """
        stats = (
            self.db.query(TeamSeasonStats)
            .filter(and_(TeamSeasonStats.team_id == team_id, TeamSeasonStats.season == season))
            .first()
        )

        if not stats:
            return None

        # Calculate computed fields
        ppg = stats.total_points_for / stats.games_played if stats.games_played > 0 else 0
        opp_ppg = stats.total_points_against / stats.games_played if stats.games_played > 0 else 0
        win_percentage = stats.wins / stats.games_played if stats.games_played > 0 else 0
        ft_percentage = stats.total_ftm / stats.total_fta if stats.total_fta > 0 else 0
        fg2_percentage = stats.total_2pm / stats.total_2pa if stats.total_2pa > 0 else 0
        fg3_percentage = stats.total_3pm / stats.total_3pa if stats.total_3pa > 0 else 0

        return {
            "raw_stats": stats,
            "wins": stats.wins,
            "losses": stats.losses,
            "games_played": stats.games_played,
            "ppg": ppg,
            "opp_ppg": opp_ppg,
            "win_percentage": win_percentage,
            "ft_percentage": ft_percentage,
            "fg2_percentage": fg2_percentage,
            "fg3_percentage": fg3_percentage,
        }

    def _get_player_season_stats(self, team_id: int, season: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get top players' season statistics for a team.

        Args:
            team_id: The team ID
            season: The season string
            limit: Number of top players to return (default: 5)

        Returns:
            List of dicts with PlayerSeasonStats and computed fields
        """
        # Join with Player to get team_id
        stats = (
            self.db.query(PlayerSeasonStats)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .filter(
                and_(
                    Player.team_id == team_id,
                    PlayerSeasonStats.season == season,
                    PlayerSeasonStats.games_played > 0,  # Only include players who have played
                )
            )
            .all()
        )

        # Calculate points per game and sort
        players_with_stats = []
        for stat in stats:
            total_points = stat.total_ftm + (stat.total_2pm * 2) + (stat.total_3pm * 3)
            ppg = total_points / stat.games_played if stat.games_played > 0 else 0
            players_with_stats.append(
                {
                    "raw_stats": stat,
                    "player": stat.player,
                    "ppg": ppg,
                    "total_points": total_points,
                }
            )

        # Sort by PPG and limit
        players_with_stats.sort(key=lambda x: x["ppg"], reverse=True)
        return players_with_stats[:limit]

    def _get_head_to_head_history(self, team1_id: int, team2_id: int, limit: int = 5) -> list[Game]:
        """
        Get historical games between two teams.

        Args:
            team1_id: First team ID
            team2_id: Second team ID
            limit: Maximum number of games to return (default: 5)

        Returns:
            List of completed games between the teams, most recent first
        """
        # Query for games where either team was home or away
        games = (
            self.db.query(Game)
            .filter(
                # Either team1 is home and team2 is away, or vice versa
                or_(
                    and_(Game.playing_team_id == team1_id, Game.opponent_team_id == team2_id),
                    and_(Game.playing_team_id == team2_id, Game.opponent_team_id == team1_id),
                )
            )
            .order_by(desc(Game.date))
            .limit(limit)
            .all()
        )

        return games
