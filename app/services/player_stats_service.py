"""
Player statistics service for calculating individual player performance metrics.
"""

from sqlalchemy.orm import Session

from app.data_access.crud.crud_player import get_all_players
from app.data_access.crud.crud_player_game_stats import get_all_player_game_stats_for_player


class PlayerStatsService:
    """Service for calculating and providing player-level statistics."""

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self._db_session = db_session

    def get_player_stats(self, team_id: int | None = None) -> list[dict]:
        """
        Calculate and return aggregated statistics for all players.

        Args:
            team_id: Optional team ID to filter players by team

        Returns:
            List of dictionaries containing player statistics including:
            - player_id, player_name, jersey_number, team_name
            - games_played, total_points, points_per_game
            - field goal percentages, free throw percentage
            - advanced metrics (true shooting %, effective field goal %)
        """
        players = get_all_players(self._db_session)
        
        # Filter by team if specified
        if team_id is not None:
            players = [p for p in players if p.team_id == team_id]

        player_stats = []

        for player in players:
            # Get all game stats for this player
            game_stats = get_all_player_game_stats_for_player(self._db_session, player.id)
            
            # Calculate aggregated statistics
            stats = self._calculate_player_stats(player, game_stats)
            player_stats.append(stats)

        return player_stats

    def _calculate_player_stats(self, player, game_stats) -> dict:
        """Calculate aggregated statistics for a single player."""
        # Initialize totals
        games_played = len(game_stats)
        total_fouls = 0
        total_ftm = 0
        total_fta = 0
        total_2pm = 0
        total_2pa = 0
        total_3pm = 0
        total_3pa = 0

        # Sum up all game stats
        for game_stat in game_stats:
            total_fouls += game_stat.fouls
            total_ftm += game_stat.total_ftm
            total_fta += game_stat.total_fta
            total_2pm += game_stat.total_2pm
            total_2pa += game_stat.total_2pa
            total_3pm += game_stat.total_3pm
            total_3pa += game_stat.total_3pa

        # Calculate derived statistics
        total_fgm = total_2pm + total_3pm
        total_fga = total_2pa + total_3pa
        total_points = total_ftm + (total_2pm * 2) + (total_3pm * 3)

        # Calculate percentages
        fg_percentage = (total_fgm / total_fga * 100) if total_fga > 0 else 0
        ft_percentage = (total_ftm / total_fta * 100) if total_fta > 0 else 0
        fg2_percentage = (total_2pm / total_2pa * 100) if total_2pa > 0 else 0
        fg3_percentage = (total_3pm / total_3pa * 100) if total_3pa > 0 else 0

        # Calculate advanced metrics
        effective_fg_percentage = self._calculate_effective_fg_percentage(total_fgm, total_3pm, total_fga)
        true_shooting_percentage = self._calculate_true_shooting_percentage(total_points, total_fga, total_fta)

        # Calculate averages
        ppg = total_points / games_played if games_played > 0 else 0
        fouls_per_game = total_fouls / games_played if games_played > 0 else 0

        return {
            "player_id": player.id,
            "player_name": player.name,
            "jersey_number": player.jersey_number,
            "team_id": player.team_id,
            "team_name": player.team.display_name or player.team.name,
            "position": player.position,
            "games_played": games_played,
            "total_points": total_points,
            "points_per_game": round(ppg, 1),
            "total_fouls": total_fouls,
            "fouls_per_game": round(fouls_per_game, 1),
            "total_ftm": total_ftm,
            "total_fta": total_fta,
            "ft_percentage": round(ft_percentage, 1),
            "total_fgm": total_fgm,
            "total_fga": total_fga,
            "fg_percentage": round(fg_percentage, 1),
            "total_2pm": total_2pm,
            "total_2pa": total_2pa,
            "fg2_percentage": round(fg2_percentage, 1),
            "total_3pm": total_3pm,
            "total_3pa": total_3pa,
            "fg3_percentage": round(fg3_percentage, 1),
            "effective_fg_percentage": round(effective_fg_percentage, 1),
            "true_shooting_percentage": round(true_shooting_percentage, 1),
        }

    def _calculate_effective_fg_percentage(self, total_fgm: int, total_3pm: int, total_fga: int) -> float:
        """
        Calculate Effective Field Goal Percentage.
        eFG% = (FGM + 0.5 * 3PM) / FGA
        """
        if total_fga == 0:
            return 0
        return (total_fgm + 0.5 * total_3pm) / total_fga * 100

    def _calculate_true_shooting_percentage(self, total_points: int, total_fga: int, total_fta: int) -> float:
        """
        Calculate True Shooting Percentage.
        TS% = PTS / (2 * (FGA + 0.44 * FTA))
        """
        if total_fga == 0 and total_fta == 0:
            return 0
        
        denominator = 2 * (total_fga + 0.44 * total_fta)
        if denominator == 0:
            return 0
        
        return total_points / denominator * 100