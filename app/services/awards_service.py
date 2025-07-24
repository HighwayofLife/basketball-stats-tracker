# app/services/awards_service.py

import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.data_access.crud import crud_game, crud_player
from app.data_access.crud.crud_player_award import (
    create_player_award,
    create_player_award_safe,
    delete_all_awards_by_type,
    get_awards_by_week,
    get_player_award_counts_by_season,
    get_player_awards_by_type,
)

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
    Calculate Player of the Week awards using PlayerAward table.

    Args:
        session: Database session
        season: Specific season to calculate (e.g., "2024"). If None, calculates all seasons.
        recalculate: If True, delete existing awards before calculation

    Returns:
        Dict with season -> awards_given count
    """
    logger.info(f"Starting POTW calculation for season: {season}, recalculate: {recalculate}")

    # Reset awards if recalculating
    if recalculate:
        logger.info("Deleting existing POTW awards for recalculation")
        deleted_count = delete_all_awards_by_type(session, "player_of_the_week")
        logger.info(f"Deleted {deleted_count} existing awards")
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
            # Calculate winner(s) for this week (safe function handles existing awards)
            winners = _calculate_week_winners(session, weekly_games, week_start, season_key, recalculate)
            
            # Count awards (both new and existing)
            week_awards = get_awards_by_week(session, "player_of_the_week", week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    logger.info(f"POTW calculation completed. Awards given by season: {dict(awards_given)}")
    return dict(awards_given)


def _calculate_week_winners(session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False) -> list[int]:
    """
    Calculate the winner(s) for a specific week and create PlayerAward records.

    Returns:
        List of player IDs who won awards
    """
    player_scores = defaultdict(int)

    # Calculate total points for each player in the week
    for game in weekly_games:
        for stat in game.player_game_stats:
            total_points = (stat.total_2pm * 2) + (stat.total_3pm * 3) + stat.total_ftm
            player_scores[stat.player_id] += total_points

    if not player_scores:
        logger.debug(f"No player stats found for week starting {week_start}")
        return []

    # Find player(s) with highest score
    max_points = max(player_scores.values())
    top_players = [pid for pid, points in player_scores.items() if points == max_points]

    # Handle recalculation by deleting existing awards first
    if recalculate:
        from app.data_access.crud.crud_player_award import delete_awards_for_week
        delete_awards_for_week(session, "player_of_the_week", week_start, season)

    # Create PlayerAward records for winner(s)
    winners = []
    for player_id in top_players:
        player = crud_player.get_player_by_id(session, player_id)
        if player:
            # Create detailed award record (safe version handles conflicts)
            award = create_player_award_safe(
                session=session,
                player_id=player_id,
                season=season,
                award_type="player_of_the_week",
                week_date=week_start,
                points_scored=max_points,
            )

            if award:
                winners.append(player_id)
                logger.debug(
                    f"Awarded POTW to {player.name} (ID: {player_id}) for {max_points} points in week {week_start}"
                )

    if len(top_players) > 1:
        logger.info(f"Tie for week {week_start}: {len(top_players)} players with {max_points} points")

    session.flush()  # Ensure records are created
    return winners


def get_player_potw_summary(session: Session, player_id: int) -> dict:
    """
    Get comprehensive POTW summary for a player.

    Returns:
        Dict with current_season_count, total_count, awards_by_season, recent_awards
    """
    current_season = get_current_season()

    # Get awards by season
    awards_by_season = get_player_award_counts_by_season(session, player_id)

    # Get current season count
    current_season_count = awards_by_season.get(current_season, 0)

    # Get total count
    total_count = sum(awards_by_season.values())

    # Get recent awards (last 5)
    recent_awards = get_player_awards_by_type(session, player_id, "player_of_the_week")[:5]

    return {
        "current_season_count": current_season_count,
        "total_count": total_count,
        "awards_by_season": awards_by_season,
        "recent_awards": [
            {
                "season": award.season,
                "week_date": award.week_date.isoformat(),
                "points_scored": award.points_scored,
                "created_at": award.created_at.isoformat() if award.created_at else None,
            }
            for award in recent_awards
        ],
    }
