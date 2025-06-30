"""
Service for generating statistical reports.
This module handles all business logic related to report generation.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.data_access.crud import get_player_by_id, get_player_season_stats
from app.data_access.crud.crud_game import get_all_games, get_game_by_id
from app.data_access.crud.crud_player_game_stats import get_player_game_stats_by_game
from app.data_access.crud.crud_team_season_stats import get_season_teams, get_team_season_stats
from app.reports.report_generator import ReportGenerator
from app.services.season_stats_service import SeasonStatsService
from app.utils import stats_calculator

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating statistical reports."""

    def __init__(self):
        """Initialize the report service."""
        pass

    def get_game_or_suggestions(
        self, db_session: Session, game_id: int
    ) -> tuple[Any | None, list[dict[str, Any]] | None]:
        """
        Get a game by ID or return suggestions if not found.

        Args:
            db_session: Database session
            game_id: ID of the game to retrieve

        Returns:
            Tuple of (game, suggestions) where suggestions is None if game found
        """
        game = get_game_by_id(db_session, game_id)
        if game:
            return game, None

        # Game not found, return suggestions
        games = get_all_games(db_session)
        suggestions = []

        if games:
            # Show last 5 games
            games.sort(key=lambda g: g.date, reverse=True)
            for g in games[:5]:
                # Check if game has been played
                game_stats = get_player_game_stats_by_game(db_session, g.id)
                score = "Scheduled" if not game_stats else "Played"
                game_info = f"{g.playing_team.name} vs {g.opponent_team.name}"
                suggestions.append({"id": g.id, "date": g.date, "info": game_info, "status": score})

        return None, suggestions

    def get_report_options(self, db_session: Session, game_id: int, game: Any) -> dict[str, Any]:
        """
        Get available report options for a specific game.

        Args:
            db_session: Database session
            game_id: ID of the game
            game: Game object

        Returns:
            Dictionary containing available reports and parameters
        """
        # Get players who played in this game
        player_stats = get_player_game_stats_by_game(db_session, game_id)

        # Organize players by team
        playing_team_players = []
        opponent_team_players = []

        for stat in player_stats:
            player_info = {"id": stat.player_id, "name": stat.player.name, "jersey": stat.player.jersey_number}
            if stat.player.team_id == game.playing_team_id:
                playing_team_players.append(player_info)
            else:
                opponent_team_players.append(player_info)

        return {
            "game": {
                "id": game.id,
                "date": game.date,
                "playing_team": game.playing_team.name,
                "opponent_team": game.opponent_team.name,
            },
            "available_reports": [
                {"type": "box-score", "description": "Traditional box score with player and team stats"},
                {
                    "type": "player-performance",
                    "description": "Detailed analysis of a single player's performance",
                    "requires": "player_id",
                },
                {
                    "type": "team-efficiency",
                    "description": "Analysis of a team's offensive efficiency",
                    "requires": "team_id",
                },
                {
                    "type": "scoring-analysis",
                    "description": "Breakdown of how a team generated points",
                    "requires": "team_id",
                },
                {"type": "game-flow", "description": "Quarter-by-quarter analysis of game momentum"},
            ],
            "teams": [
                {"id": game.playing_team_id, "name": game.playing_team.name},
                {"id": game.opponent_team_id, "name": game.opponent_team.name},
            ],
            "players": {game.playing_team.name: playing_team_players, game.opponent_team.name: opponent_team_players},
            "has_stats": len(player_stats) > 0,
        }

    def generate_game_report(
        self,
        db_session: Session,
        game_id: int,
        report_type: str,
        player_id: int | None = None,
        team_id: int | None = None,
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        """
        Generate a statistical report for a specific game.

        Args:
            db_session: Database session
            game_id: ID of the game
            report_type: Type of report to generate
            player_id: Player ID (required for player-performance report)
            team_id: Team ID (required for team-efficiency and scoring-analysis reports)

        Returns:
            Tuple of (success, report_data, error_message)
        """
        try:
            # Verify game exists
            game, suggestions = self.get_game_or_suggestions(db_session, game_id)
            if not game:
                return False, {"suggestions": suggestions}, f"Game ID {game_id} not found"

            report_generator = ReportGenerator(db_session, stats_calculator)

            # Generate the appropriate report based on type
            if report_type == "box-score":
                player_stats, game_summary = report_generator.get_game_box_score_data(game_id)
                report_data = {"player_stats": player_stats, "game_summary": game_summary}

            elif report_type == "player-performance":
                if not player_id:
                    return False, None, "Player ID is required for player-performance report"

                # Verify player exists
                player = get_player_by_id(db_session, player_id)
                if not player:
                    return False, None, f"Player ID {player_id} not found"

                report_data = report_generator.generate_player_performance_report(player_id, game_id)

            elif report_type == "team-efficiency":
                if not team_id:
                    return False, None, "Team ID is required for team-efficiency report"

                # Verify team is in this game
                if team_id not in [game.playing_team_id, game.opponent_team_id]:
                    return (
                        False,
                        {"teams": [game.playing_team, game.opponent_team]},
                        f"Team ID {team_id} did not play in game {game_id}",
                    )

                report_data = report_generator.generate_team_efficiency_report(team_id, game_id)

            elif report_type == "scoring-analysis":
                if not team_id:
                    return False, None, "Team ID is required for scoring-analysis report"

                # Verify team is in this game
                if team_id not in [game.playing_team_id, game.opponent_team_id]:
                    return (
                        False,
                        {"teams": [game.playing_team, game.opponent_team]},
                        f"Team ID {team_id} did not play in game {game_id}",
                    )

                report_data = report_generator.generate_scoring_analysis_report(team_id, game_id)

            elif report_type == "game-flow":
                report_data = report_generator.generate_game_flow_report(game_id)

            else:
                available_types = [
                    "box-score",
                    "player-performance",
                    "team-efficiency",
                    "scoring-analysis",
                    "game-flow",
                ]
                return False, {"available_types": available_types}, f"Unknown report type '{report_type}'"

            # Check if report has data
            if not report_data or (isinstance(report_data, dict) and all(not v for v in report_data.values())):
                return False, None, f"No data found for {report_type} report. Game may not have been played yet."

            # Add game context to report data
            report_data["_game"] = game
            report_data["_report_type"] = report_type

            return True, report_data, None

        except Exception as e:
            logger.error(f"Error generating {report_type} report for game {game_id}: {e}")
            return False, None, str(e)

    def generate_season_report(
        self,
        db_session: Session,
        season: str | None = None,
        report_type: str = "standings",
        stat_category: str = "ppg",
        player_id: int | None = None,
        team_id: int | None = None,
        limit: int = 10,
        min_games: int = 1,
    ) -> tuple[bool, dict[str, Any] | None, str | None]:
        """
        Generate season-long statistical reports.

        Args:
            db_session: Database session
            season: Season to generate report for
            report_type: Type of report to generate
            stat_category: Stat category for player-leaders
            player_id: Player ID (required for player-season report)
            team_id: Team ID (optional for filtering)
            limit: Number of players to show in leaderboards
            min_games: Minimum games played for leaderboards

        Returns:
            Tuple of (success, report_data, error_message)
        """
        try:
            # Use current season if not specified
            if not season:
                season_service = SeasonStatsService(db_session)
                season = season_service.get_current_season()
                logger.info(f"Using current season: {season}")

            if report_type == "standings":
                standings_data = self._generate_standings_report(db_session, season, team_id)
                return True, standings_data, None

            elif report_type == "player-leaders":
                leaders_data = self._generate_player_leaders_report(
                    db_session, season, stat_category, limit, min_games, team_id
                )
                return True, leaders_data, None

            elif report_type == "team-stats":
                team_stats_data = self._generate_team_stats_report(db_session, season, team_id)
                return True, team_stats_data, None

            elif report_type == "player-season":
                if not player_id:
                    return False, None, "Player ID is required for player-season report"

                player_stats_data = self._generate_player_season_report(db_session, season, player_id)
                return True, player_stats_data, None

            else:
                available_types = ["standings", "player-leaders", "team-stats", "player-season"]
                return False, {"available_types": available_types}, f"Unknown report type '{report_type}'"

        except Exception as e:
            logger.error(f"Error generating {report_type} season report: {e}")
            return False, None, str(e)

    def _generate_standings_report(
        self, db_session: Session, season: str, team_id: int | None = None
    ) -> dict[str, Any]:
        """Generate team standings report."""
        season_service = SeasonStatsService(db_session)
        standings = season_service.get_team_standings(season)

        # Filter by team if specified
        if team_id:
            standings = [s for s in standings if s.get("team_id") == team_id]

        return {"season": season, "standings": standings, "_report_type": "standings"}

    def _generate_player_leaders_report(
        self,
        db_session: Session,
        season: str,
        stat_category: str,
        limit: int,
        min_games: int,
        team_id: int | None = None,
    ) -> dict[str, Any]:
        """Generate player leaders report."""
        season_service = SeasonStatsService(db_session)
        leaders = season_service.get_player_rankings(
            stat_category=stat_category, season=season, limit=limit, min_games=min_games
        )

        # Filter by team if specified
        if team_id:
            # Get team name for filtering
            teams = get_season_teams(db_session, season)
            team_name = next((t.name for t in teams if t.id == team_id), None)
            if team_name:
                leaders = [leader for leader in leaders if leader.get("team_name") == team_name]

        # Transform data to match expected format
        transformed_leaders = []
        for leader in leaders:
            transformed_leader = {
                "player": leader.get("player_name", ""),
                "team": leader.get("team_name", ""),
                "games": leader.get("games_played", 0),
                "value": leader.get("value", 0),
            }
            # Add the specific stat value with its key
            if stat_category == "ppg":
                transformed_leader["ppg"] = leader.get("value", 0)
            elif stat_category == "fpg":
                transformed_leader["fpg"] = leader.get("value", 0)
            elif stat_category == "ft_pct":
                transformed_leader["ft_pct"] = leader.get("value", 0)
            elif stat_category == "fg_pct":
                transformed_leader["fg_pct"] = leader.get("value", 0)
            elif stat_category == "fg3_pct":
                transformed_leader["fg3_pct"] = leader.get("value", 0)
            elif stat_category == "efg_pct":
                transformed_leader["efg_pct"] = leader.get("value", 0)

            transformed_leaders.append(transformed_leader)

        return {
            "season": season,
            "stat_category": stat_category,
            "leaders": transformed_leaders,
            "min_games": min_games,
            "_report_type": "player-leaders",
        }

    def _generate_team_stats_report(
        self, db_session: Session, season: str, team_id: int | None = None
    ) -> dict[str, Any]:
        """Generate team statistics report."""
        teams = get_season_teams(db_session, season)
        team_stats_list = []

        for team in teams:
            if team_id and team.id != team_id:
                continue

            stats = get_team_season_stats(db_session, team.id, season)
            if stats:
                team_stats_list.append(
                    {
                        "team": team.name,
                        "games": stats.games_played,
                        "wins": stats.wins,
                        "losses": stats.losses,
                        "ppg": stats.points_per_game,
                        "papg": stats.points_against_per_game,
                        "fg_pct": stats.fg_percentage,
                        "fg3_pct": stats.fg3_percentage,
                        "ft_pct": stats.ft_percentage,
                        "fouls_pg": stats.fouls_per_game,
                    }
                )

        return {"season": season, "team_stats": team_stats_list, "_report_type": "team-stats"}

    def _generate_player_season_report(self, db_session: Session, season: str, player_id: int) -> dict[str, Any]:
        """Generate individual player season report."""
        player = get_player_by_id(db_session, player_id)
        if not player:
            return {}

        stats = get_player_season_stats(db_session, player_id, season)
        if not stats:
            return {}

        return {
            "season": season,
            "player": {
                "name": player.name,
                "team": player.team.name,
                "jersey": player.jersey_number,
                "position": player.position,
            },
            "stats": {
                "games_played": stats.games_played,
                "points": stats.total_points,
                "ppg": stats.points_per_game,
                "fg": f"{stats.fg_made}/{stats.fg_attempted}",
                "fg_pct": stats.fg_percentage,
                "fg3": f"{stats.fg3_made}/{stats.fg3_attempted}",
                "fg3_pct": stats.fg3_percentage,
                "ft": f"{stats.ft_made}/{stats.ft_attempted}",
                "ft_pct": stats.ft_percentage,
                "fouls": stats.total_fouls,
                "fpg": stats.fouls_per_game,
            },
            "_report_type": "player-season",
        }
