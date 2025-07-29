"""Service for handling game matchup/preview data for scheduled games."""

import logging
from typing import Any

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.data_access.crud import get_team_by_id
from app.data_access.models import Game, Player, PlayerSeasonStats, ScheduledGame, Season, TeamSeasonStats

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
        season_string = (
            self._get_season_string(scheduled_game.season_id)
            if scheduled_game.season_id
            else self._get_current_season()
        )

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

    def get_formatted_matchup_data(self, scheduled_game_id: int) -> dict[str, Any] | None:
        """
        Get comprehensive matchup data formatted for display.

        Args:
            scheduled_game_id: The ID of the scheduled game

        Returns:
            Dictionary containing formatted matchup data or None if game not found
        """
        matchup_data = self.get_matchup_data(scheduled_game_id)
        if not matchup_data:
            return None

        # Format the data for display
        formatted_data = {
            "scheduled_game": matchup_data["scheduled_game"],
            "home_team": self._format_team_data(matchup_data["home_team"]),
            "away_team": self._format_team_data(matchup_data["away_team"]),
            "head_to_head": self._format_head_to_head_history(matchup_data["head_to_head"]),
        }

        # Add playoff round information if it's a playoff game
        scheduled_game = matchup_data["scheduled_game"]
        if scheduled_game.is_playoff_game:
            from app.services.playoffs_service import PlayoffsService

            playoffs_service = PlayoffsService(self.db)
            playoff_round = playoffs_service.determine_playoff_round(f"scheduled-{scheduled_game.id}")
            formatted_data["playoff_round"] = playoff_round

        return formatted_data

    def _format_team_data(self, team_data: dict[str, Any]) -> dict[str, Any]:
        """Format team data for display."""
        formatted_team = {
            "team": team_data["team"],
            "top_players": self._format_players_for_display(team_data["top_players"]),
        }

        # Format season stats
        season_stats = team_data["season_stats"]
        if season_stats:
            formatted_team.update(
                {
                    "ppg": round(season_stats["ppg"], 1),
                    "opp_ppg": round(season_stats["opp_ppg"], 1),
                    "record": self._format_team_record(season_stats["wins"], season_stats["losses"]),
                    "win_pct": round(season_stats["win_percentage"] * 100, 1),
                    "ft_pct": round(season_stats["ft_percentage"] * 100, 1),
                    "fg2_pct": round(season_stats["fg2_percentage"] * 100, 1),
                    "fg3_pct": round(season_stats["fg3_percentage"] * 100, 1),
                }
            )
        else:
            formatted_team.update(
                {
                    "ppg": 0,
                    "opp_ppg": 0,
                    "record": self._format_team_record(0, 0),
                    "win_pct": 0,
                    "ft_pct": 0,
                    "fg2_pct": 0,
                    "fg3_pct": 0,
                }
            )

        return formatted_team

    def _format_players_for_display(self, players_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format player stats for display."""
        formatted_players = []
        for player_data in players_data:
            stats = player_data["raw_stats"]
            player = player_data["player"]

            # Calculate percentages
            ft_pct = round((stats.total_ftm / stats.total_fta * 100) if stats.total_fta > 0 else 0, 1)
            fg3_pct = round((stats.total_3pm / stats.total_3pa * 100) if stats.total_3pa > 0 else 0, 1)

            # Calculate overall field goal percentage (2P + 3P combined)
            total_fg_made = stats.total_2pm + stats.total_3pm
            total_fg_attempted = stats.total_2pa + stats.total_3pa
            fg_pct = round((total_fg_made / total_fg_attempted * 100) if total_fg_attempted > 0 else 0, 1)

            formatted_players.append(
                {
                    "id": player.id,
                    "name": player.name,
                    "jersey_number": player.jersey_number,
                    "position": player.position or "N/A",
                    "ppg": round(player_data["ppg"], 1),
                    "games_played": stats.games_played,
                    "ft_pct": ft_pct,
                    "fg_pct": fg_pct,
                    "fg3_pct": fg3_pct,
                }
            )

        return formatted_players

    def _format_head_to_head_history(self, games: list[Game]) -> list[dict[str, Any]]:
        """Format head-to-head history for display."""
        formatted_h2h = []
        for game in games:
            # Determine winner and format score
            if game.playing_team_score > game.opponent_team_score:
                winner = game.playing_team.display_name or game.playing_team.name
                score_display = (
                    f"{game.playing_team.display_name or game.playing_team.name} {game.playing_team_score}, "
                    f"{game.opponent_team.display_name or game.opponent_team.name} {game.opponent_team_score}"
                )
            else:
                winner = game.opponent_team.display_name or game.opponent_team.name
                score_display = (
                    f"{game.opponent_team.display_name or game.opponent_team.name} {game.opponent_team_score}, "
                    f"{game.playing_team.display_name or game.playing_team.name} {game.playing_team_score}"
                )

            formatted_h2h.append(
                {
                    "game_id": game.id,
                    "date": game.date.strftime("%m/%d/%Y") if game.date else "N/A",
                    "score": score_display,
                    "winner": winner,
                }
            )

        return formatted_h2h

    def _get_season_string(self, season_id: int) -> str:
        """
        Get season string from season ID.

        Args:
            season_id: The season ID

        Returns:
            Season string (e.g., "2024-2025")
        """
        season = self.db.query(Season).filter(Season.id == season_id).first()
        if season:
            return self._format_season_string(season)
        return self._get_current_season()  # Default fallback

    def _get_current_season(self) -> str:
        """
        Get the current or most recent season string.

        Returns:
            Current season string (e.g., "2024-2025")
        """
        from datetime import date

        # Try to get the active season first
        current_season = self.db.query(Season).filter(Season.is_active).first()
        if current_season:
            return self._format_season_string(current_season)

        # Fall back to the most recent season
        recent_season = self.db.query(Season).order_by(Season.start_date.desc()).first()
        if recent_season:
            return self._format_season_string(recent_season)

        # Final fallback to most recent season in the DB
        most_recent_season = self.db.query(Season).order_by(Season.start_date.desc()).first()
        if most_recent_season:
            return self._format_season_string(most_recent_season)

        # Absolute fallback if DB is empty
        current_year = date.today().year
        return f"{current_year - 1}-{current_year}"

    def _format_season_string(self, season) -> str:
        """Format a Season object into a season string."""
        # Prefer the season code if it exists, as that's what TeamSeasonStats uses
        if season.code:
            return season.code
        # Fallback to parsing the name
        if "-" in season.name:
            return season.name
        # Otherwise create from dates
        start_year = season.start_date.year
        end_year = season.end_date.year if season.end_date.year != start_year else start_year + 1
        return f"{start_year}-{end_year}"

    def _format_team_record(self, wins: int, losses: int) -> str:
        """Format team record as 'W-L' string."""
        return f"{wins}-{losses}"

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
        Get top players' season statistics for a team, ranked by total points.

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

        # Sort by total points and limit
        players_with_stats.sort(key=lambda x: x["total_points"], reverse=True)
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
