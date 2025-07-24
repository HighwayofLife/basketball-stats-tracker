# app/services/awards_service.py

import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.data_access.crud import crud_game, crud_player

logger = logging.getLogger(__name__)


def get_season_from_date(game_date: date) -> str:
    """
    Convert a game date to season string.
    Uses calendar year approach: January-December = "YYYY" season
    """
    return str(game_date.year)


def get_current_season() -> str:
    """Get the current season based on today's date."""
    return get_season_from_date(date.today())


def calculate_player_of_the_week(
    session: Session, season: str | None = None, recalculate: bool = False
) -> dict[str, int]:
    """
    Calculate Player of the Week awards for games.

    Args:
        session: Database session
        season: Specific season to calculate (e.g., "2024"). If None, calculates all seasons.
        recalculate: If True, reset existing awards before calculation

    Returns:
        Dict with season -> awards_given count
    """
    logger.info(f"Starting POTW calculation for season: {season}, recalculate: {recalculate}")

    # Reset awards if recalculating
    if recalculate:
        logger.info("Resetting all player awards for recalculation")
        from app.data_access.models import Player

        session.query(Player).update({"player_of_the_week_awards": 0})
        session.commit()

    # Get all games, optionally filtered by season
    games = crud_game.get_all_games(session)
    if season:
        games = [g for g in games if get_season_from_date(g.date) == season]

    logger.info(f"Processing {len(games)} games for POTW calculation")

    # Group games by season and week
    games_by_season_week = defaultdict(lambda: defaultdict(list))

    for game in games:
        game_season = get_season_from_date(game.date)
        # Week starts on Monday (weekday() returns 0 for Monday)
        week_start = game.date - timedelta(days=game.date.weekday())
        games_by_season_week[game_season][week_start].append(game)

    awards_given = defaultdict(int)

    # Process each season and week
    for season_key, weeks in games_by_season_week.items():
        logger.info(f"Processing season {season_key} with {len(weeks)} weeks")

        for week_start, weekly_games in weeks.items():
            winner_id = _calculate_week_winner(session, weekly_games, week_start)
            if winner_id:
                awards_given[season_key] += 1

    session.commit()
    logger.info(f"POTW calculation completed. Awards given by season: {dict(awards_given)}")
    return dict(awards_given)


def _calculate_week_winner(session: Session, weekly_games: list, week_start: date) -> int | None:
    """
    Calculate the winner for a specific week of games.

    Returns:
        Player ID of the winner, or None if no games/stats
    """
    player_scores = defaultdict(int)

    # Calculate total points for each player in the week
    for game in weekly_games:
        for stat in game.player_game_stats:
            total_points = (stat.total_2pm * 2) + (stat.total_3pm * 3) + stat.total_ftm
            player_scores[stat.player_id] += total_points

    if not player_scores:
        logger.debug(f"No player stats found for week starting {week_start}")
        return None

    # Find player(s) with highest score
    max_points = max(player_scores.values())
    top_players = [pid for pid, points in player_scores.items() if points == max_points]

    if len(top_players) > 1:
        logger.info(f"Tie for week {week_start}: {len(top_players)} players with {max_points} points")
        # For ties, award to all tied players (could implement tiebreaker logic here)
        for player_id in top_players:
            player = crud_player.get_player_by_id(session, player_id)
            if player:
                player.player_of_the_week_awards += 1
                logger.debug(f"Awarded POTW to {player.name} (ID: {player_id}) for {max_points} points")
        return top_players[0]  # Return first for logging purposes
    else:
        # Single winner
        winner_id = top_players[0]
        player = crud_player.get_player_by_id(session, winner_id)
        if player:
            player.player_of_the_week_awards += 1
            logger.debug(f"Awarded POTW to {player.name} (ID: {winner_id}) for {max_points} points")
        return winner_id
