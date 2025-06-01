"""Service layer for season statistics management."""

import logging
from datetime import date, datetime

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session, joinedload

from app.data_access.models import (
    Game,
    Player,
    PlayerGameStats,
    PlayerSeasonStats,
    Season,
    Team,
    TeamSeasonStats,
)
from app.utils.stats_calculator import calculate_efg, calculate_percentage

logger = logging.getLogger(__name__)


class SeasonStatsService:
    """Service for managing season-long statistics."""

    def __init__(self, db_session: Session):
        """Initialize the season stats service.

        Args:
            db_session: The database session to use
        """
        self.db_session = db_session

    def get_season_from_date(self, game_date: date) -> str:
        """Determine the season based on a date.

        Basketball seasons typically run from October to April.
        A season is denoted as "YYYY-YYYY" (e.g., "2024-2025").

        Args:
            game_date: The date to determine season for

        Returns:
            Season string in format "YYYY-YYYY"
        """
        # If month is October or later, it's the start of next year's season
        if game_date.month >= 10:
            return f"{game_date.year}-{game_date.year + 1}"
        # Otherwise, it's part of the current year's season
        return f"{game_date.year - 1}-{game_date.year}"

    def get_or_create_season_from_date(self, game_date: date) -> "Season | None":
        """Get or create a Season object based on a date.

        Args:
            game_date: The date to determine season for

        Returns:
            Season object or None if unable to determine season
        """
        from app.data_access.models import Season

        # Determine season code based on date
        # For simplicity, we'll use the year-based season approach
        season_string = self.get_season_from_date(game_date)

        # Create a season code (e.g., "2024-2025" becomes "2024-25")
        years = season_string.split("-")
        if len(years) == 2:
            season_code = f"{years[0]}-{years[1][-2:]}"
            season_name = f"Season {season_string}"
        else:
            return None

        # Check if season exists
        season = self.db_session.query(Season).filter(Season.code == season_code).first()

        if not season:
            # Create new season with reasonable defaults
            # Season starts in October and ends in May
            start_year = int(years[0])
            end_year = int(years[1])

            season = Season(
                name=season_name,
                code=season_code,
                start_date=date(start_year, 10, 1),  # October 1st
                end_date=date(end_year, 5, 31),  # May 31st
                is_active=True,  # Assume active
            )
            self.db_session.add(season)
            self.db_session.flush()

        return season

    def update_player_season_stats(self, player_id: int, season: str | None = None) -> PlayerSeasonStats | None:
        """Update or create season statistics for a player.

        Args:
            player_id: ID of the player
            season: Season to update (if None, updates current season)

        Returns:
            Updated PlayerSeasonStats object or None if:
            - No games found for the player in the specified season
            - Specified season record is not found in the database
            - Unable to determine season from game data
        """
        # Get all games for the player in the season
        query = self.db_session.query(PlayerGameStats).join(Game).filter(PlayerGameStats.player_id == player_id)

        if season:
            # Look up the actual season record to get the correct date range
            season_record = self.db_session.query(Season).filter(Season.code == season).first()
            if season_record:
                query = query.filter(and_(Game.date >= season_record.start_date, Game.date <= season_record.end_date))
            else:
                logger.warning(f"Season {season} not found in database")
                return None

        game_stats = query.all()

        if not game_stats:
            logger.warning(f"No games found for player {player_id} in season {season}")
            return None

        # Determine season from first game if not provided
        if not season and game_stats:
            first_game = self.db_session.query(Game).get(game_stats[0].game_id)
            if first_game:
                season = self.get_season_from_date(first_game.date)
            else:
                logger.warning(f"Could not find game with ID {game_stats[0].game_id}")
                return None

        # Calculate totals
        games_played = len(game_stats)
        total_fouls = sum(gs.fouls for gs in game_stats)
        total_ftm = sum(gs.total_ftm for gs in game_stats)
        total_fta = sum(gs.total_fta for gs in game_stats)
        total_2pm = sum(gs.total_2pm for gs in game_stats)
        total_2pa = sum(gs.total_2pa for gs in game_stats)
        total_3pm = sum(gs.total_3pm for gs in game_stats)
        total_3pa = sum(gs.total_3pa for gs in game_stats)

        # Get or create season stats record
        season_stats = self.db_session.query(PlayerSeasonStats).filter_by(player_id=player_id, season=season).first()

        if not season_stats:
            season_stats = PlayerSeasonStats(player_id=player_id, season=season)
            self.db_session.add(season_stats)

        # Update values
        season_stats.games_played = games_played
        season_stats.total_fouls = total_fouls
        season_stats.total_ftm = total_ftm
        season_stats.total_fta = total_fta
        season_stats.total_2pm = total_2pm
        season_stats.total_2pa = total_2pa
        season_stats.total_3pm = total_3pm
        season_stats.total_3pa = total_3pa
        season_stats.last_updated = datetime.utcnow()

        self.db_session.commit()
        return season_stats

    def update_team_season_stats(self, team_id: int, season: str | None = None) -> TeamSeasonStats | None:
        """Update or create season statistics for a team.

        Args:
            team_id: ID of the team
            season: Season to update (if None, updates current season)

        Returns:
            Updated TeamSeasonStats object or None if:
            - No games found for the team in the specified season
            - Specified season record is not found in the database
        """
        # Get all games for the team in the season
        query = self.db_session.query(Game).filter(
            (Game.playing_team_id == team_id) | (Game.opponent_team_id == team_id)
        )

        if season:
            # Look up the actual season record to get the correct date range
            season_record = self.db_session.query(Season).filter(Season.code == season).first()
            if season_record:
                query = query.filter(and_(Game.date >= season_record.start_date, Game.date <= season_record.end_date))
            else:
                logger.warning(f"Season {season} not found in database")
                return None

        games = query.all()

        if not games:
            logger.warning(f"No games found for team {team_id} in season {season}")
            return None

        # Determine season from first game if not provided
        if not season and games:
            season = self.get_season_from_date(games[0].date)

        # Calculate team statistics
        games_played = len(games)
        wins = 0
        losses = 0
        total_points_for = 0
        total_points_against = 0
        total_ftm = 0
        total_fta = 0
        total_2pm = 0
        total_2pa = 0
        total_3pm = 0
        total_3pa = 0

        for game in games:
            # Get all player stats for this game
            team_stats = (
                self.db_session.query(PlayerGameStats)
                .join(Player)
                .filter(PlayerGameStats.game_id == game.id, Player.team_id == team_id)
                .all()
            )

            # Calculate team totals for this game
            game_ftm = sum(ps.total_ftm for ps in team_stats)
            game_fta = sum(ps.total_fta for ps in team_stats)
            game_2pm = sum(ps.total_2pm for ps in team_stats)
            game_2pa = sum(ps.total_2pa for ps in team_stats)
            game_3pm = sum(ps.total_3pm for ps in team_stats)
            game_3pa = sum(ps.total_3pa for ps in team_stats)

            game_points = game_ftm + (game_2pm * 2) + (game_3pm * 3)

            # Update season totals
            total_ftm += game_ftm
            total_fta += game_fta
            total_2pm += game_2pm
            total_2pa += game_2pa
            total_3pm += game_3pm
            total_3pa += game_3pa

            # Determine if home or away and calculate opponent points
            if game.playing_team_id == team_id:
                total_points_for += game_points
                # Calculate opponent points
                opp_stats = (
                    self.db_session.query(PlayerGameStats)
                    .join(Player)
                    .filter(PlayerGameStats.game_id == game.id, Player.team_id == game.opponent_team_id)
                    .all()
                )
                opp_points = sum(ps.total_ftm + (ps.total_2pm * 2) + (ps.total_3pm * 3) for ps in opp_stats)
                total_points_against += opp_points

                if game_points > opp_points:
                    wins += 1
                else:
                    losses += 1
            else:
                total_points_for += game_points
                # Calculate opponent points (home team in this case)
                opp_stats = (
                    self.db_session.query(PlayerGameStats)
                    .join(Player)
                    .filter(PlayerGameStats.game_id == game.id, Player.team_id == game.playing_team_id)
                    .all()
                )
                opp_points = sum(ps.total_ftm + (ps.total_2pm * 2) + (ps.total_3pm * 3) for ps in opp_stats)
                total_points_against += opp_points

                if game_points > opp_points:
                    wins += 1
                else:
                    losses += 1

        # Get or create season stats record
        season_stats = self.db_session.query(TeamSeasonStats).filter_by(team_id=team_id, season=season).first()

        if not season_stats:
            season_stats = TeamSeasonStats(team_id=team_id, season=season)
            self.db_session.add(season_stats)

        # Update values
        season_stats.games_played = games_played
        season_stats.wins = wins
        season_stats.losses = losses
        season_stats.total_points_for = total_points_for
        season_stats.total_points_against = total_points_against
        season_stats.total_ftm = total_ftm
        season_stats.total_fta = total_fta
        season_stats.total_2pm = total_2pm
        season_stats.total_2pa = total_2pa
        season_stats.total_3pm = total_3pm
        season_stats.total_3pa = total_3pa
        season_stats.last_updated = datetime.utcnow()

        self.db_session.commit()
        return season_stats

    def update_all_season_stats(self, season: str | None = None):
        """Update season statistics for all players and teams.

        Args:
            season: Season to update (if None, updates current season)
        """
        # Update all player stats
        players = self.db_session.query(Player).filter_by(is_active=True).all()
        for player in players:
            try:
                self.update_player_season_stats(player.id, season)
            except Exception as e:
                logger.error(f"Error updating stats for player {player.id}: {e}")

        # Update all team stats
        teams = self.db_session.query(Team).all()
        for team in teams:
            try:
                self.update_team_season_stats(team.id, season)
            except Exception as e:
                logger.error(f"Error updating stats for team {team.id}: {e}")

    def get_player_rankings(
        self, stat_category: str, season: str | None = None, limit: int = 10, min_games: int = 1
    ) -> list[dict]:
        """Get player rankings for a specific statistical category.

        Args:
            stat_category: Category to rank by (ppg, fpg, ft_pct, fg_pct, etc.)
            season: Season to get rankings for (if None, uses current season)
            limit: Number of players to return
            min_games: Minimum games played to be included

        Returns:
            List of player ranking dictionaries
        """
        if not season:
            # Determine current season
            latest_game = self.db_session.query(Game).order_by(desc(Game.date)).first()
            if latest_game:
                season = self.get_season_from_date(latest_game.date)
            else:
                return []

        query = (
            self.db_session.query(PlayerSeasonStats)
            .join(Player)
            .join(Team, Player.team_id == Team.id)
            .filter(PlayerSeasonStats.season == season, PlayerSeasonStats.games_played >= min_games)
            .options(joinedload(PlayerSeasonStats.player).joinedload(Player.team))
        )

        rankings = []
        for stats in query.all():
            player_dict = {
                "player_id": stats.player_id,
                "player_name": stats.player.name,
                "team_name": stats.player.team.name,
                "games_played": stats.games_played,
            }

            # Calculate the requested stat
            value: float = 0.0  # Default value for unknown stat categories
            if stat_category == "ppg":
                total_points = stats.total_ftm + (stats.total_2pm * 2) + (stats.total_3pm * 3)
                value = total_points / stats.games_played if stats.games_played > 0 else 0
            elif stat_category == "fpg":
                value = stats.total_fouls / stats.games_played if stats.games_played > 0 else 0
            elif stat_category == "ft_pct":
                value = calculate_percentage(stats.total_ftm, stats.total_fta) or 0
            elif stat_category == "fg_pct":
                fgm = stats.total_2pm + stats.total_3pm
                fga = stats.total_2pa + stats.total_3pa
                value = calculate_percentage(fgm, fga) or 0
            elif stat_category == "fg3_pct":
                value = calculate_percentage(stats.total_3pm, stats.total_3pa) or 0
            elif stat_category == "efg_pct":
                fgm = stats.total_2pm + stats.total_3pm
                fga = stats.total_2pa + stats.total_3pa
                value = calculate_efg(fgm, fga, stats.total_3pm) or 0

            player_dict["value"] = value
            rankings.append(player_dict)

        # Sort by value (descending) and add rank
        rankings.sort(
            key=lambda x: (
                float(x["value"]) if x["value"] is not None and isinstance(x["value"], int | float | str) else -1.0
            ),
            reverse=True,
        )
        for i, player in enumerate(rankings[:limit]):
            player["rank"] = i + 1

        return rankings[:limit]

    def get_team_standings(self, season: str | None = None) -> list[dict]:
        """Get team standings for a season.

        Args:
            season: Season to get standings for (if None, uses current season)

        Returns:
            List of team standing dictionaries
        """
        if not season:
            # Determine current season
            latest_game = self.db_session.query(Game).order_by(desc(Game.date)).first()
            if latest_game:
                season = self.get_season_from_date(latest_game.date)
            else:
                return []

        standings: list[dict] = []
        team_stats = (
            self.db_session.query(TeamSeasonStats)
            .join(Team)
            .filter(TeamSeasonStats.season == season)
            .options(joinedload(TeamSeasonStats.team))
            .all()
        )

        # Calculate standings
        for stats in team_stats:
            win_pct = stats.wins / stats.games_played if stats.games_played > 0 else 0
            ppg = stats.total_points_for / stats.games_played if stats.games_played > 0 else 0
            opp_ppg = stats.total_points_against / stats.games_played if stats.games_played > 0 else 0
            point_diff = ppg - opp_ppg

            standings.append(
                {
                    "team_id": stats.team_id,
                    "team_name": stats.team.name,
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "win_pct": win_pct,
                    "ppg": ppg,
                    "opp_ppg": opp_ppg,
                    "point_diff": point_diff,
                    "games_played": stats.games_played,
                }
            )

        # Sort by win percentage
        standings.sort(key=lambda x: float(x["win_pct"]), reverse=True)

        # Add rank and games back
        if standings:
            leader_wins = standings[0]["wins"]
            leader_losses = standings[0]["losses"]

            for i, team in enumerate(standings):
                team["rank"] = i + 1
                # Calculate games back
                if i == 0:
                    team["games_back"] = None
                else:
                    gb = ((leader_wins - int(team["wins"])) + (int(team["losses"]) - leader_losses)) / 2
                    team["games_back"] = gb

        return standings
