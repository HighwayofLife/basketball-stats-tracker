# app/services/awards_service.py

import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.data_access.crud import crud_game, crud_player
from app.data_access.crud.crud_player_award import (
    create_player_award_safe,
    delete_all_awards_by_type,
    get_awards_by_week,
    get_player_award_counts_by_season,
    get_player_awards_by_type,
)

logger = logging.getLogger(__name__)

# Weekly award type constants
WEEKLY_AWARD_TYPES = {
    "player_of_the_week": "player_of_the_week",
    "quarterly_firepower": "quarterly_firepower",
    "weekly_ft_king": "weekly_ft_king",
    "hot_hand_weekly": "hot_hand_weekly",
    "clutch_man": "clutch_man",
    "trigger_finger": "trigger_finger",
    "weekly_whiffer": "weekly_whiffer",
}


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
            _ = _calculate_week_winners(session, weekly_games, week_start, season_key, recalculate)

            # Count awards (both new and existing)
            week_awards = get_awards_by_week(session, "player_of_the_week", week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    logger.info(f"POTW calculation completed. Awards given by season: {dict(awards_given)}")
    return dict(awards_given)


def _calculate_week_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
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


def calculate_all_weekly_awards(
    session: Session, season: str | None = None, recalculate: bool = False
) -> dict[str, dict[str, int]]:
    """
    Calculate all weekly awards for a given season.

    Args:
        session: Database session
        season: Specific season to calculate. If None, calculates all seasons.
        recalculate: If True, delete existing awards before calculation

    Returns:
        Dict with award_type -> season -> awards_given count
    """
    results = {}
    results["player_of_the_week"] = calculate_player_of_the_week(session, season, recalculate)
    results["quarterly_firepower"] = calculate_quarterly_firepower(session, season, recalculate)
    results["weekly_ft_king"] = calculate_weekly_ft_king(session, season, recalculate)
    results["hot_hand_weekly"] = calculate_hot_hand_weekly(session, season, recalculate)
    results["clutch_man"] = calculate_clutch_man(session, season, recalculate)
    results["trigger_finger"] = calculate_trigger_finger(session, season, recalculate)
    results["weekly_whiffer"] = calculate_weekly_whiffer(session, season, recalculate)

    return results


def calculate_quarterly_firepower(
    session: Session, season: str | None = None, recalculate: bool = False
) -> dict[str, int]:
    """
    Calculate Quarterly Firepower awards - highest point total in any single quarter for the week.
    """
    award_type = WEEKLY_AWARD_TYPES["quarterly_firepower"]
    logger.info(f"Starting {award_type} calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_all_awards_by_type(session, award_type)
        session.commit()

    # Get all games, optionally filtered by season
    games = crud_game.get_all_games(session)
    if season:
        games = [g for g in games if get_season_from_date(g.date) == season]

    # Group games by season and week
    games_by_season_week = defaultdict(lambda: defaultdict(list))
    for game in games:
        game_season = get_season_from_date(game.date)
        week_start = game.date - timedelta(days=game.date.weekday())
        games_by_season_week[game_season][week_start].append(game)

    awards_given = defaultdict(int)

    # Process each season and week
    for season_key, weeks in games_by_season_week.items():
        for week_start, weekly_games in weeks.items():
            _ = _calculate_quarterly_firepower_winners(session, weekly_games, week_start, season_key, recalculate)
            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    return dict(awards_given)


def calculate_weekly_ft_king(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Weekly Free Throw King/Queen awards - most free throws made for the week.
    """
    award_type = WEEKLY_AWARD_TYPES["weekly_ft_king"]
    return _calculate_weekly_stat_award(
        session, award_type, season, recalculate, lambda stats: stats.total_ftm, "FT made"
    )


def calculate_hot_hand_weekly(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Hot Hand Weekly awards - highest FG% with minimum 10 shot attempts for the week.
    """
    award_type = WEEKLY_AWARD_TYPES["hot_hand_weekly"]
    logger.info(f"Starting {award_type} calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_all_awards_by_type(session, award_type)
        session.commit()

    # Get all games, optionally filtered by season
    games = crud_game.get_all_games(session)
    if season:
        games = [g for g in games if get_season_from_date(g.date) == season]

    # Group games by season and week
    games_by_season_week = defaultdict(lambda: defaultdict(list))
    for game in games:
        game_season = get_season_from_date(game.date)
        week_start = game.date - timedelta(days=game.date.weekday())
        games_by_season_week[game_season][week_start].append(game)

    awards_given = defaultdict(int)

    # Process each season and week
    for season_key, weeks in games_by_season_week.items():
        for week_start, weekly_games in weeks.items():
            _ = _calculate_hot_hand_winners(session, weekly_games, week_start, season_key, recalculate)
            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    return dict(awards_given)


def calculate_clutch_man(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Clutch-man awards - most shots made in 4th quarter for the week.
    """
    award_type = WEEKLY_AWARD_TYPES["clutch_man"]
    logger.info(f"Starting {award_type} calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_all_awards_by_type(session, award_type)
        session.commit()

    # Get all games, optionally filtered by season
    games = crud_game.get_all_games(session)
    if season:
        games = [g for g in games if get_season_from_date(g.date) == season]

    # Group games by season and week
    games_by_season_week = defaultdict(lambda: defaultdict(list))
    for game in games:
        game_season = get_season_from_date(game.date)
        week_start = game.date - timedelta(days=game.date.weekday())
        games_by_season_week[game_season][week_start].append(game)

    awards_given = defaultdict(int)

    # Process each season and week
    for season_key, weeks in games_by_season_week.items():
        for week_start, weekly_games in weeks.items():
            _ = _calculate_clutch_man_winners(session, weekly_games, week_start, season_key, recalculate)
            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    return dict(awards_given)


def calculate_trigger_finger(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Trigger Finger awards - most total shot attempts (2pt + 3pt) for the week.
    """
    award_type = WEEKLY_AWARD_TYPES["trigger_finger"]
    return _calculate_weekly_stat_award(
        session, award_type, season, recalculate, lambda stats: stats.total_2pa + stats.total_3pa, "shot attempts"
    )


def calculate_weekly_whiffer(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Weekly Whiffer awards - most total missed shots for the week.
    """
    award_type = WEEKLY_AWARD_TYPES["weekly_whiffer"]
    return _calculate_weekly_stat_award(
        session,
        award_type,
        season,
        recalculate,
        lambda stats: (stats.total_2pa - stats.total_2pm)
        + (stats.total_3pa - stats.total_3pm)
        + (stats.total_fta - stats.total_ftm),
        "missed shots",
    )


# Helper functions for weekly awards


def _calculate_weekly_stat_award(
    session: Session, award_type: str, season: str | None, recalculate: bool, stat_calculator, stat_name: str
) -> dict[str, int]:
    """
    Generic helper for calculating weekly awards based on a single stat.
    """
    logger.info(f"Starting {award_type} calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_all_awards_by_type(session, award_type)
        session.commit()

    # Get all games, optionally filtered by season
    games = crud_game.get_all_games(session)
    if season:
        games = [g for g in games if get_season_from_date(g.date) == season]

    # Group games by season and week
    games_by_season_week = defaultdict(lambda: defaultdict(list))
    for game in games:
        game_season = get_season_from_date(game.date)
        week_start = game.date - timedelta(days=game.date.weekday())
        games_by_season_week[game_season][week_start].append(game)

    awards_given = defaultdict(int)

    # Process each season and week
    for season_key, weeks in games_by_season_week.items():
        for week_start, weekly_games in weeks.items():
            # Calculate stat totals for each player in the week
            player_stats = defaultdict(int)
            for game in weekly_games:
                for stat in game.player_game_stats:
                    player_stats[stat.player_id] += stat_calculator(stat)

            if not player_stats:
                continue

            # Find winner(s)
            max_stat = max(player_stats.values())
            winners = [pid for pid, stat_val in player_stats.items() if stat_val == max_stat]

            # Create awards
            for player_id in winners:
                award = create_player_award_safe(
                    session=session,
                    player_id=player_id,
                    season=season_key,
                    award_type=award_type,
                    week_date=week_start,
                    points_scored=None,
                )
                if award:
                    award.stat_value = float(max_stat)
                    logger.debug(f"Awarded {award_type} to player {player_id} with {max_stat} {stat_name}")

            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    return dict(awards_given)


def _calculate_quarterly_firepower_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """Calculate winners for Quarterly Firepower award."""
    player_max_quarter_points = defaultdict(int)

    # Find max quarter points for each player in the week
    for game in weekly_games:
        for stat in game.player_game_stats:
            # Check each quarter's stats via quarter_stats
            for quarter_stat in stat.quarter_stats:
                quarter_points = (quarter_stat.fg2m * 2) + (quarter_stat.fg3m * 3) + quarter_stat.ftm
                if quarter_points > player_max_quarter_points[stat.player_id]:
                    player_max_quarter_points[stat.player_id] = quarter_points

    if not player_max_quarter_points:
        return []

    # Find overall winner(s)
    max_quarter_points = max(player_max_quarter_points.values())
    winners = [pid for pid, points in player_max_quarter_points.items() if points == max_quarter_points]

    # Create awards
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=WEEKLY_AWARD_TYPES["quarterly_firepower"],
            week_date=week_start,
            points_scored=None,
        )
        if award:
            award.stat_value = float(max_quarter_points)

    session.flush()
    return winners


def _calculate_hot_hand_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """Calculate winners for Hot Hand Weekly award (highest FG% with 10+ attempts)."""
    player_stats = defaultdict(lambda: {"fgm": 0, "fga": 0})

    # Calculate week totals
    for game in weekly_games:
        for stat in game.player_game_stats:
            player_stats[stat.player_id]["fgm"] += stat.total_2pm + stat.total_3pm
            player_stats[stat.player_id]["fga"] += stat.total_2pa + stat.total_3pa

    # Filter players with 10+ attempts and calculate percentages
    qualified_players = {}
    for player_id, stats in player_stats.items():
        if stats["fga"] >= 10:
            qualified_players[player_id] = stats["fgm"] / stats["fga"]

    if not qualified_players:
        logger.info(f"No players qualified for Hot Hand (10+ attempts) in week {week_start}")
        return []

    # Find winner(s)
    max_percentage = max(qualified_players.values())
    winners = [pid for pid, pct in qualified_players.items() if pct == max_percentage]

    # Create awards
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=WEEKLY_AWARD_TYPES["hot_hand_weekly"],
            week_date=week_start,
            points_scored=None,
        )
        if award:
            award.stat_value = max_percentage

    session.flush()
    return winners


def _calculate_clutch_man_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """Calculate winners for Clutch-man award (most shots made in Q4)."""
    player_q4_makes = defaultdict(int)

    # Calculate Q4 makes for each player
    for game in weekly_games:
        for stat in game.player_game_stats:
            # Find Q4 stats
            for quarter_stat in stat.quarter_stats:
                if quarter_stat.quarter_number == 4:  # Q4
                    q4_makes = quarter_stat.fg2m + quarter_stat.fg3m + quarter_stat.ftm
                    player_q4_makes[stat.player_id] += q4_makes

    if not player_q4_makes:
        return []

    # Find winner(s)
    max_q4_makes = max(player_q4_makes.values())
    winners = [pid for pid, makes in player_q4_makes.items() if makes == max_q4_makes]

    # Create awards
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=WEEKLY_AWARD_TYPES["clutch_man"],
            week_date=week_start,
            points_scored=None,
        )
        if award:
            award.stat_value = float(max_q4_makes)

    session.flush()
    return winners
