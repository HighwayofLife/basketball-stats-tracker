# app/services/season_awards_service.py

import logging
from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.data_access.crud import crud_game
from app.data_access.crud.crud_player_award import (
    create_player_award_safe,
    get_player_awards_by_type,
)
from app.services.awards_service import get_current_season, get_season_from_date

logger = logging.getLogger(__name__)

# Season award type constants
SEASON_AWARD_TYPES = {
    "top_scorer": "top_scorer",
    "sharpshooter": "sharpshooter",
    "efficiency_expert": "efficiency_expert",
    "charity_stripe_regular": "charity_stripe_regular",
    "human_highlight_reel": "human_highlight_reel",
    "defensive_tackle": "defensive_tackle",
    "air_ball_artist": "air_ball_artist",
    "air_assault": "air_assault",
}


def calculate_season_awards(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate all season awards for a given season.

    Args:
        session: Database session
        season: Specific season to calculate (e.g., "2024"). If None, calculates current season.
        recalculate: If True, delete existing awards before calculation

    Returns:
        Dict with award_type -> number of awards given
    """
    if season is None:
        season = get_current_season()

    logger.info(f"Starting season awards calculation for season: {season}, recalculate: {recalculate}")

    results = {}

    # Calculate each season award type
    results["top_scorer"] = calculate_top_scorer(session, season, recalculate)
    results["sharpshooter"] = calculate_sharpshooter(session, season, recalculate)
    results["efficiency_expert"] = calculate_efficiency_expert(session, season, recalculate)
    results["charity_stripe_regular"] = calculate_charity_stripe_regular(session, season, recalculate)
    results["human_highlight_reel"] = calculate_human_highlight_reel(session, season, recalculate)
    results["defensive_tackle"] = calculate_defensive_tackle(session, season, recalculate)
    results["air_ball_artist"] = calculate_air_ball_artist(session, season, recalculate)
    results["air_assault"] = calculate_air_assault(session, season, recalculate)

    session.commit()
    logger.info(f"Season awards calculation completed for {season}. Results: {results}")
    return results


def calculate_top_scorer(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Award to player with most total points scored in the season.
    Calculation: Sum of (2pt made * 2) + (3pt made * 3) + (FT made * 1)
    """
    award_type = SEASON_AWARD_TYPES["top_scorer"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    # Get season stats for all players
    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        logger.info(f"No player stats found for {award_type} in season {season}")
        return 0

    # Calculate total points for each player
    player_points = {}
    for player_id, stats in player_stats.items():
        total_points = (stats["total_2pm"] * 2) + (stats["total_3pm"] * 3) + stats["total_ftm"]
        player_points[player_id] = total_points

    # Find winner(s)
    max_points = max(player_points.values())
    winners = [pid for pid, points in player_points.items() if points == max_points]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=award_type,
            week_date=None,  # Season awards don't have week_date
            points_scored=None,  # Not applicable for season awards
        )
        if award:
            # Update with stat value
            award.stat_value = float(max_points)
            awards_given += 1
            logger.debug(f"Awarded {award_type} to player {player_id} with {max_points} points")

    session.flush()
    logger.info(f"Awarded {award_type} to {awards_given} players with {max_points} points in season {season}")
    return awards_given


def calculate_sharpshooter(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Award to player with highest 3-point percentage meeting dynamic minimum threshold.

    Algorithm:
    1. Identify top 10 players by total 3pt FGs made
    2. Find highest 3pt % among those 10
    3. Use that player's 3pt attempts as minimum threshold
    4. Award to highest 3pt % among all players meeting threshold
    """
    award_type = SEASON_AWARD_TYPES["sharpshooter"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        logger.info(f"No player stats found for {award_type} in season {season}")
        return 0

    # Filter players with at least 1 3pt attempt
    eligible_players = {pid: stats for pid, stats in player_stats.items() if stats["total_3pa"] > 0}

    if not eligible_players:
        logger.info(f"No players with 3pt attempts for {award_type} in season {season}")
        return 0

    # Step 1: Find top 10 by 3pt made
    top_10_by_made = sorted(eligible_players.items(), key=lambda x: x[1]["total_3pm"], reverse=True)[:10]

    if not top_10_by_made:
        return 0

    # Step 2: Find highest 3pt % among top 10
    best_percentage_in_top10 = 0.0
    threshold_attempts = 0

    for _player_id, stats in top_10_by_made:
        percentage = stats["total_3pm"] / stats["total_3pa"]
        if percentage > best_percentage_in_top10:
            best_percentage_in_top10 = percentage
            threshold_attempts = stats["total_3pa"]

    # Step 3: Find all players meeting threshold with highest percentage
    qualified_players = {}
    for player_id, stats in eligible_players.items():
        if stats["total_3pa"] >= threshold_attempts:
            percentage = stats["total_3pm"] / stats["total_3pa"]
            qualified_players[player_id] = percentage

    if not qualified_players:
        return 0

    # Step 4: Award to highest percentage
    max_percentage = max(qualified_players.values())
    winners = [pid for pid, pct in qualified_players.items() if pct == max_percentage]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=award_type,
            week_date=None,
        )
        if award:
            award.stat_value = max_percentage
            awards_given += 1
            logger.debug(f"Awarded {award_type} to player {player_id} with {max_percentage:.3f} 3pt%")

    session.flush()
    logger.info(
        f"Awarded {award_type} to {awards_given} players with {max_percentage:.3f} 3pt% "
        f"(min {threshold_attempts} attempts)"
    )
    return awards_given


def calculate_efficiency_expert(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Award to player with highest overall FG percentage meeting dynamic minimum threshold.

    Same algorithm as Sharpshooter but for overall FG%:
    1. Identify top 10 players by total FGs made (2pt + 3pt)
    2. Find highest FG % among those 10
    3. Use that player's FG attempts as minimum threshold
    4. Award to highest FG % among all players meeting threshold
    """
    award_type = SEASON_AWARD_TYPES["efficiency_expert"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        logger.info(f"No player stats found for {award_type} in season {season}")
        return 0

    # Filter players with at least 1 FG attempt
    eligible_players = {}
    for pid, stats in player_stats.items():
        total_fga = stats["total_2pa"] + stats["total_3pa"]
        if total_fga > 0:
            total_fgm = stats["total_2pm"] + stats["total_3pm"]
            eligible_players[pid] = {"fgm": total_fgm, "fga": total_fga, "percentage": total_fgm / total_fga}

    if not eligible_players:
        logger.info(f"No players with FG attempts for {award_type} in season {season}")
        return 0

    # Step 1: Find top 10 by FG made
    top_10_by_made = sorted(eligible_players.items(), key=lambda x: x[1]["fgm"], reverse=True)[:10]

    # Step 2: Find highest FG % among top 10
    best_percentage_in_top10 = 0.0
    threshold_attempts = 0

    for _player_id, stats in top_10_by_made:
        if stats["percentage"] > best_percentage_in_top10:
            best_percentage_in_top10 = stats["percentage"]
            threshold_attempts = stats["fga"]

    # Step 3: Find all players meeting threshold
    qualified_players = {
        pid: stats["percentage"] for pid, stats in eligible_players.items() if stats["fga"] >= threshold_attempts
    }

    if not qualified_players:
        return 0

    # Step 4: Award to highest percentage
    max_percentage = max(qualified_players.values())
    winners = [pid for pid, pct in qualified_players.items() if pct == max_percentage]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=award_type,
            week_date=None,
        )
        if award:
            award.stat_value = max_percentage
            awards_given += 1
            logger.debug(f"Awarded {award_type} to player {player_id} with {max_percentage:.3f} FG%")

    session.flush()
    logger.info(
        f"Awarded {award_type} to {awards_given} players with {max_percentage:.3f} FG% "
        f"(min {threshold_attempts} attempts)"
    )
    return awards_given


def calculate_charity_stripe_regular(session: Session, season: str, recalculate: bool = False) -> int:
    """Award to player with most free throw attempts in the season."""
    award_type = SEASON_AWARD_TYPES["charity_stripe_regular"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        return 0

    # Find max FT attempts
    player_fta = {pid: stats["total_fta"] for pid, stats in player_stats.items()}
    max_fta = max(player_fta.values())
    winners = [pid for pid, fta in player_fta.items() if fta == max_fta]

    return _create_season_awards(session, winners, season, award_type, max_fta)


def calculate_human_highlight_reel(session: Session, season: str, recalculate: bool = False) -> int:
    """Award to player with most combined made shots (2pt + 3pt + FT) in the season."""
    award_type = SEASON_AWARD_TYPES["human_highlight_reel"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        return 0

    # Calculate total made shots
    player_makes = {}
    for pid, stats in player_stats.items():
        total_makes = stats["total_2pm"] + stats["total_3pm"] + stats["total_ftm"]
        player_makes[pid] = total_makes

    max_makes = max(player_makes.values())
    winners = [pid for pid, makes in player_makes.items() if makes == max_makes]

    return _create_season_awards(session, winners, season, award_type, max_makes)


def calculate_defensive_tackle(session: Session, season: str, recalculate: bool = False) -> int:
    """Award to player with most fouls committed in the season."""
    award_type = SEASON_AWARD_TYPES["defensive_tackle"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        return 0

    player_fouls = {pid: stats["total_fouls"] for pid, stats in player_stats.items()}
    max_fouls = max(player_fouls.values())
    winners = [pid for pid, fouls in player_fouls.items() if fouls == max_fouls]

    return _create_season_awards(session, winners, season, award_type, max_fouls)


def calculate_air_ball_artist(session: Session, season: str, recalculate: bool = False) -> int:
    """Award to player with most 3-point misses in the season."""
    award_type = SEASON_AWARD_TYPES["air_ball_artist"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        return 0

    # Calculate 3pt misses
    player_3pt_misses = {}
    for pid, stats in player_stats.items():
        misses = stats["total_3pa"] - stats["total_3pm"]
        player_3pt_misses[pid] = misses

    max_misses = max(player_3pt_misses.values())
    winners = [pid for pid, misses in player_3pt_misses.items() if misses == max_misses]

    return _create_season_awards(session, winners, season, award_type, max_misses)


def calculate_air_assault(session: Session, season: str, recalculate: bool = False) -> int:
    """Award to player with most total shot attempts (2pt + 3pt) in the season."""
    award_type = SEASON_AWARD_TYPES["air_assault"]

    if recalculate:
        _clear_season_awards(session, award_type, season)

    player_stats = _get_season_player_stats(session, season)

    if not player_stats:
        return 0

    # Calculate total shot attempts
    player_attempts = {}
    for pid, stats in player_stats.items():
        total_attempts = stats["total_2pa"] + stats["total_3pa"]
        player_attempts[pid] = total_attempts

    max_attempts = max(player_attempts.values())
    winners = [pid for pid, attempts in player_attempts.items() if attempts == max_attempts]

    return _create_season_awards(session, winners, season, award_type, max_attempts)


def finalize_season_awards(session: Session, season: str) -> int:
    """
    Mark all season awards for a given season as finalized.
    This should be called at the end of each season.
    """
    logger.info(f"Finalizing season awards for season {season}")

    finalized_count = 0
    for award_type in SEASON_AWARD_TYPES.values():
        awards = get_player_awards_by_type(session, None, award_type)  # Get all players
        for award in awards:
            if award.season == season and not award.is_finalized:
                award.is_finalized = True
                award.award_date = date.today()
                finalized_count += 1

    session.commit()
    logger.info(f"Finalized {finalized_count} season awards for season {season}")
    return finalized_count


# Helper functions


def _get_season_player_stats(session: Session, season: str) -> dict[int, dict[str, int]]:
    """Get aggregated player stats for a season."""
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        return {}

    # Aggregate stats by player
    player_stats = defaultdict(
        lambda: {
            "total_2pm": 0,
            "total_2pa": 0,
            "total_3pm": 0,
            "total_3pa": 0,
            "total_ftm": 0,
            "total_fta": 0,
            "total_fouls": 0,
        }
    )

    for game in season_games:
        for stat in game.player_game_stats:
            pid = stat.player_id
            player_stats[pid]["total_2pm"] += stat.total_2pm
            player_stats[pid]["total_2pa"] += stat.total_2pa
            player_stats[pid]["total_3pm"] += stat.total_3pm
            player_stats[pid]["total_3pa"] += stat.total_3pa
            player_stats[pid]["total_ftm"] += stat.total_ftm
            player_stats[pid]["total_fta"] += stat.total_fta
            player_stats[pid]["total_fouls"] += stat.fouls

    return dict(player_stats)


def _clear_season_awards(session: Session, award_type: str, season: str) -> None:
    """Clear existing season awards for recalculation."""
    # Get existing awards for this type and season
    existing_awards = session.query(
        session.get_bind().execute(
            "SELECT * FROM player_awards WHERE award_type = :award_type AND season = :season AND week_date IS NULL",
            {"award_type": award_type, "season": season},
        )
    ).fetchall()

    if existing_awards:
        session.execute(
            "DELETE FROM player_awards WHERE award_type = :award_type AND season = :season AND week_date IS NULL",
            {"award_type": award_type, "season": season},
        )
        logger.debug(f"Cleared {len(existing_awards)} existing {award_type} awards for season {season}")


def _create_season_awards(session: Session, winners: list[int], season: str, award_type: str, stat_value: float) -> int:
    """Helper to create season awards for winners."""
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=award_type,
            week_date=None,
        )
        if award:
            award.stat_value = float(stat_value)
            awards_given += 1
            logger.debug(f"Awarded {award_type} to player {player_id} with value {stat_value}")

    session.flush()
    logger.info(f"Awarded {award_type} to {awards_given} players with value {stat_value} in season {season}")
    return awards_given
