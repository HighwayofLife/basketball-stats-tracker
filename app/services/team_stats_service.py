"""
Team statistics service for calculating team rankings and performance metrics.
"""

from sqlalchemy.orm import Session

from app.data_access.crud.crud_game import get_all_games
from app.data_access.crud.crud_player_game_stats import get_player_game_stats_for_game_and_team
from app.data_access.crud.crud_team import get_all_teams


class TeamStatsService:
    """Service for calculating and providing team-level statistics and rankings."""

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self._db_session = db_session

    def get_team_rankings(self) -> list[dict]:
        """
        Calculate and return aggregated offensive and defensive statistics for all teams.

        Returns:
            List of dictionaries containing team ranking statistics including:
            - team_id, team_name
            - total_points_scored, total_points_allowed
            - fg_percentage, opponent_fg_percentage
            - games_played
            - offensive_rating, defensive_rating (composite scores)
        """
        team_stats = {}
        teams = get_all_teams(self._db_session)

        # Initialize stats for all teams
        for team in teams:
            team_stats[team.id] = {
                "team_id": team.id,
                "team_name": team.display_name or team.name,
                "total_points_scored": 0,
                "total_fgm": 0,
                "total_fga": 0,
                "total_points_allowed": 0,
                "opponent_total_fgm": 0,
                "opponent_total_fga": 0,
                "games_played": 0,
            }

        games = get_all_games(self._db_session)

        for game in games:
            playing_team_id = game.playing_team_id
            opponent_team_id = game.opponent_team_id

            # Skip if either team is not in our stats dictionary
            if playing_team_id not in team_stats or opponent_team_id not in team_stats:
                continue

            # Get player stats for both teams
            playing_team_player_stats = get_player_game_stats_for_game_and_team(
                self._db_session, game.id, playing_team_id
            )
            opponent_team_player_stats = get_player_game_stats_for_game_and_team(
                self._db_session, game.id, opponent_team_id
            )

            # Calculate team scores and field goal stats
            playing_team_score = self._calculate_team_score(playing_team_player_stats)
            opponent_team_score = self._calculate_team_score(opponent_team_player_stats)

            playing_team_fgm, playing_team_fga = self._calculate_team_fg_stats(playing_team_player_stats)
            opponent_team_fgm, opponent_team_fga = self._calculate_team_fg_stats(opponent_team_player_stats)

            # Update stats for playing team (home team)
            team_stats[playing_team_id]["total_points_scored"] += playing_team_score
            team_stats[playing_team_id]["total_points_allowed"] += opponent_team_score
            team_stats[playing_team_id]["total_fgm"] += playing_team_fgm
            team_stats[playing_team_id]["total_fga"] += playing_team_fga
            team_stats[playing_team_id]["opponent_total_fgm"] += opponent_team_fgm
            team_stats[playing_team_id]["opponent_total_fga"] += opponent_team_fga
            team_stats[playing_team_id]["games_played"] += 1

            # Update stats for opponent team (away team)
            team_stats[opponent_team_id]["total_points_scored"] += opponent_team_score
            team_stats[opponent_team_id]["total_points_allowed"] += playing_team_score
            team_stats[opponent_team_id]["total_fgm"] += opponent_team_fgm
            team_stats[opponent_team_id]["total_fga"] += opponent_team_fga
            team_stats[opponent_team_id]["opponent_total_fgm"] += playing_team_fgm
            team_stats[opponent_team_id]["opponent_total_fga"] += playing_team_fga
            team_stats[opponent_team_id]["games_played"] += 1

        # Calculate percentages and composite ratings
        ranked_teams = []
        for _team_id, stats in team_stats.items():
            # Calculate field goal percentages
            fg_percentage = (stats["total_fgm"] / stats["total_fga"] * 100) if stats["total_fga"] > 0 else 0
            opponent_fg_percentage = (
                (stats["opponent_total_fgm"] / stats["opponent_total_fga"] * 100)
                if stats["opponent_total_fga"] > 0
                else 0
            )

            # Calculate average points per game
            ppg = stats["total_points_scored"] / stats["games_played"] if stats["games_played"] > 0 else 0
            opp_ppg = stats["total_points_allowed"] / stats["games_played"] if stats["games_played"] > 0 else 0

            # Calculate composite ratings (0-100 scale)
            offensive_rating = self._calculate_offensive_rating(ppg, fg_percentage)
            defensive_rating = self._calculate_defensive_rating(opp_ppg, opponent_fg_percentage)

            ranked_teams.append(
                {
                    "team_id": stats["team_id"],
                    "team_name": stats["team_name"],
                    "total_points_scored": stats["total_points_scored"],
                    "avg_points_scored": round(ppg, 1),
                    "fg_percentage": round(fg_percentage, 1),
                    "total_points_allowed": stats["total_points_allowed"],
                    "avg_points_allowed": round(opp_ppg, 1),
                    "opponent_fg_percentage": round(opponent_fg_percentage, 1),
                    "games_played": stats["games_played"],
                    "offensive_rating": round(offensive_rating, 1),
                    "defensive_rating": round(defensive_rating, 1),
                    "point_differential": round(ppg - opp_ppg, 1),
                }
            )

        return ranked_teams

    def _calculate_team_score(self, player_stats) -> int:
        """Calculate total team score from player stats."""
        total_score = 0
        for pgs in player_stats:
            # Points = FTM + (2PM * 2) + (3PM * 3)
            total_score += pgs.total_ftm + (pgs.total_2pm * 2) + (pgs.total_3pm * 3)
        return total_score

    def _calculate_team_fg_stats(self, player_stats) -> tuple[int, int]:
        """Calculate team field goal makes and attempts from player stats."""
        total_fgm = 0
        total_fga = 0
        for pgs in player_stats:
            # Field goals = 2-point + 3-point shots
            total_fgm += pgs.total_2pm + pgs.total_3pm
            total_fga += pgs.total_2pa + pgs.total_3pa
        return total_fgm, total_fga

    def _calculate_offensive_rating(self, ppg: float, fg_percentage: float) -> float:
        """
        Calculate composite offensive rating (0-100 scale).
        Combines points per game and field goal percentage.
        """
        if ppg == 0 and fg_percentage == 0:
            return 0

        # Normalize PPG to 0-50 scale (assuming 100 PPG is excellent)
        ppg_score = min(ppg * 0.5, 50)

        # FG% is already 0-100, scale to 0-50
        fg_score = fg_percentage * 0.5

        return ppg_score + fg_score

    def _calculate_defensive_rating(self, opp_ppg: float, opp_fg_percentage: float) -> float:
        """
        Calculate composite defensive rating (0-100 scale).
        Higher is better (lower opponent scoring and lower opponent FG%).
        """
        if opp_ppg == 0 and opp_fg_percentage == 0:
            return 100  # Perfect defense

        # Invert opponent PPG (lower is better for defense)
        # Assuming 100 PPG allowed is terrible, 0 is perfect
        ppg_defense_score = max(50 - (opp_ppg * 0.5), 0)

        # Invert opponent FG% (lower is better for defense)
        fg_defense_score = max(50 - (opp_fg_percentage * 0.5), 0)

        return ppg_defense_score + fg_defense_score
