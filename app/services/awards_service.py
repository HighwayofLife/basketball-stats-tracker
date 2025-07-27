# app/services/awards_service.py

import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.data_access.crud import crud_game, crud_player
from app.data_access.crud.crud_player_award import (
    create_player_award_safe,
    delete_all_awards_by_type,
    delete_awards_by_season_and_type,
    get_awards_by_week,
    get_player_award_counts_by_season,
    get_player_awards_by_type,
)

logger = logging.getLogger(__name__)

# Constants
DUB_CLUB_POINT_THRESHOLD = 20

# Weekly award type constants
WEEKLY_AWARD_TYPES = {
    "player_of_the_week": "player_of_the_week",
    "quarterly_firepower": "quarterly_firepower",
    "weekly_ft_king": "weekly_ft_king",
    "hot_hand_weekly": "hot_hand_weekly",
    "clutch_man": "clutch_man",
    "trigger_finger": "trigger_finger",
    "weekly_whiffer": "weekly_whiffer",
    "human_howitzer": "human_howitzer",
    "dub_club": "dub_club",
    "marksman_award": "marksman_award",
    "perfect_performance": "perfect_performance",
    "breakout_performance": "breakout_performance",
}

# Season award type constants
SEASON_AWARD_TYPES = [
    "rick_barry_award",
    "top_scorer",
    "sharpshooter",
    "efficiency_expert",
    "human_highlight_reel",
    "charity_stripe_regular",
    "defensive_tackle",
    "air_ball_artist",
    "air_assault",
]


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

    logger.info(f"📅 Processing {len(games)} games for POTW calculation")

    # Group games by season and week
    games_by_season_week = defaultdict(lambda: defaultdict(list))

    for game in games:
        game_season = get_season_from_date(game.date)
        # Week starts on Monday (weekday() returns 0 for Monday)
        week_start = game.date - timedelta(days=game.date.weekday())
        games_by_season_week[game_season][week_start].append(game)

    # Count total weeks to process
    total_weeks = sum(len(weeks) for weeks in games_by_season_week.values())
    logger.info(f"📊 Found {total_weeks} total weeks across {len(games_by_season_week)} seasons")

    awards_given = defaultdict(int)

    # Process each season and week
    for season_key, weeks in games_by_season_week.items():
        logger.info(f"📅 Processing season {season_key} with {len(weeks)} weeks")

        for week_start, weekly_games in weeks.items():
            logger.info(f"  🗓️  Processing week {week_start} with {len(weekly_games)} games")
            # Calculate winner(s) for this week (safe function handles existing awards)
            _ = _calculate_week_winners(session, weekly_games, week_start, season_key, recalculate)

            # Count awards (both new and existing)
            week_awards = get_awards_by_week(session, "player_of_the_week", week_start, season_key)
            awards_given[season_key] += len(week_awards)
            logger.info(f"    ✅ Week {week_start} completed, {len(week_awards)} awards")

    session.commit()
    logger.info(f"POTW calculation completed. Awards given by season: {dict(awards_given)}")
    return dict(awards_given)


def _calculate_week_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """
    Calculate the winner(s) for a specific week based on best single-game performance.
    In case of ties, uses FG% from that same game as tie-breaker.

    Returns:
        List of player IDs who won awards
    """
    # Track best single-game performance for each player
    player_best_games = {}

    # Find best single-game performance for each player in the week
    for game in weekly_games:
        for stat in game.player_game_stats:
            total_points = (stat.total_2pm * 2) + (stat.total_3pm * 3) + stat.total_ftm
            player_id = stat.player_id
            fgm = stat.total_2pm + stat.total_3pm
            fga = stat.total_2pa + stat.total_3pa
            fg_pct = fgm / fga if fga > 0 else 0.0

            # Track the highest single-game point total for each player
            if player_id not in player_best_games or total_points > player_best_games[player_id]["points"]:
                player_best_games[player_id] = {
                    "points": total_points,
                    "fg_pct": fg_pct,
                    "game_id": game.id,
                }

    if not player_best_games:
        logger.debug(f"No player stats found for week starting {week_start}")
        return []

    # Find player(s) with highest single-game score
    max_points = max(data["points"] for data in player_best_games.values())
    top_players = [pid for pid, data in player_best_games.items() if data["points"] == max_points]

    # Apply FG% tie-breaker if there are multiple players with the same score
    if len(top_players) > 1:
        logger.info(
            f"Tie for week {week_start}: {len(top_players)} players with {max_points} points - applying FG% tie-breaker"
        )

        # Find player(s) with highest FG% among the tied players
        max_fg_percentage = max(player_best_games[pid]["fg_pct"] for pid in top_players)
        top_players = [pid for pid in top_players if player_best_games[pid]["fg_pct"] == max_fg_percentage]
        logger.info(f"After FG% tie-breaker: {len(top_players)} player(s) with {max_fg_percentage:.1%} FG%")

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
                game_id=player_best_games[player_id]["game_id"],
            )

            if award:
                winners.append(player_id)
                logger.debug(
                    f"Awarded Player of the Week to {player.name} (ID: {player_id}) "
                    f"for {max_points} points in single game in week {week_start}"
                )

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
    logger.info(f"🏆 Starting calculation of ALL weekly awards for season: {season}, recalculate: {recalculate}")
    results = {}

    logger.info("📊 Calculating Player of the Week...")
    results["player_of_the_week"] = calculate_player_of_the_week(session, season, recalculate)

    logger.info("🔥 Calculating Quarterly Firepower...")
    results["quarterly_firepower"] = calculate_quarterly_firepower(session, season, recalculate)

    logger.info("🎯 Calculating Weekly FT King...")
    results["weekly_ft_king"] = calculate_weekly_ft_king(session, season, recalculate)

    logger.info("🏀 Calculating Hot Hand Weekly...")
    results["hot_hand_weekly"] = calculate_hot_hand_weekly(session, season, recalculate)

    logger.info("⏰ Calculating Clutch-man...")
    results["clutch_man"] = calculate_clutch_man(session, season, recalculate)

    logger.info("🎪 Calculating Trigger Finger...")
    results["trigger_finger"] = calculate_trigger_finger(session, season, recalculate)

    logger.info("😅 Calculating Weekly Whiffer...")
    results["weekly_whiffer"] = calculate_weekly_whiffer(session, season, recalculate)

    logger.info("🚀 Calculating Human Howitzer...")
    results["human_howitzer"] = calculate_human_howitzer(session, season, recalculate)

    logger.info("🎖️ Calculating Dub Club...")
    results["dub_club"] = calculate_dub_club(session, season, recalculate)

    logger.info("🎯 Calculating Marksman Award...")
    results["marksman_award"] = calculate_marksman_award(session, season, recalculate)

    logger.info("💯 Calculating Perfect Performance...")
    results["perfect_performance"] = calculate_perfect_performance(session, season, recalculate)

    logger.info("⬆️ Calculating Breakout Performance...")
    results["breakout_performance"] = calculate_breakout_performance(session, season, recalculate)

    logger.info("✅ ALL weekly awards calculation completed!")
    return results


def calculate_rick_barry_award(
    session: Session, season: str | None = None, recalculate: bool = False
) -> dict[str, int]:
    """
    Calculate The Rick Barry Award - highest free-throw percentage in a season (minimum 10 free throw attempts).
    """
    award_type = "rick_barry_award"
    logger.info(f"Starting {award_type} calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_all_awards_by_type(session, award_type)
        session.commit()

    # Get all games, optionally filtered by season
    games = crud_game.get_all_games(session)
    if season:
        games = [g for g in games if get_season_from_date(g.date) == season]

    # Aggregate season stats for each player
    player_season_stats = defaultdict(lambda: {"ftm": 0, "fta": 0})
    for game in games:
        for stat in game.player_game_stats:
            player_season_stats[stat.player_id]["ftm"] += stat.total_ftm
            player_season_stats[stat.player_id]["fta"] += stat.total_fta

    # Filter players who meet the minimum 10 free throw attempts and calculate FT%
    qualified_players = {}
    for player_id, stats in player_season_stats.items():
        if stats["fta"] >= 10:  # Minimum 10 free throw attempts
            ft_percentage = stats["ftm"] / stats["fta"] if stats["fta"] > 0 else 0.0
            qualified_players[player_id] = ft_percentage

    if not qualified_players:
        logger.info(f"No players qualified for {award_type} in season {season}")
        return {}

    # Find winner(s) - players with the highest FT%
    max_ft_percentage = max(qualified_players.values())
    winners = [pid for pid, pct in qualified_players.items() if pct == max_ft_percentage]

    # Create awards
    awards_given = defaultdict(int)
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=award_type,
            week_date=None,  # Season award, no specific week
            points_scored=None,
        )
        if award:
            award.stat_value = max_ft_percentage
            awards_given[season] += 1
            logger.debug(f"Awarded {award_type} to player {player_id} with {max_ft_percentage:.1%} FT%")

    session.commit()
    return dict(awards_given)


def calculate_all_season_awards(
    session: Session, season: str | None = None, recalculate: bool = False
) -> dict[str, dict[str, int]]:
    """
    Calculate all season awards for a given season.

    Args:
        session: Database session
        season: Specific season to calculate. If None, calculates all seasons.
        recalculate: If True, delete existing awards before calculation

    Returns:
        Dict with award_type -> season -> awards_given count
    """
    logger.info(f"🏆 Starting calculation of ALL season awards for season: {season}, recalculate: {recalculate}")
    results = {}

    logger.info("⭐ Calculating The Rick Barry Award...")
    results["rick_barry_award"] = calculate_rick_barry_award(session, season, recalculate)

    logger.info("🏆 Calculating Top Scorer...")
    top_scorer_count = calculate_top_scorer(session, season, recalculate)
    results["top_scorer"] = {season: top_scorer_count} if season else {}

    logger.info("🎯 Calculating Sharpshooter...")
    sharpshooter_count = calculate_sharpshooter(session, season, recalculate)
    results["sharpshooter"] = {season: sharpshooter_count} if season else {}

    logger.info("💪 Calculating Efficiency Expert...")
    efficiency_count = calculate_efficiency_expert(session, season, recalculate)
    results["efficiency_expert"] = {season: efficiency_count} if season else {}

    logger.info("🎪 Calculating Human Highlight Reel...")
    highlight_count = calculate_human_highlight_reel(session, season, recalculate)
    results["human_highlight_reel"] = {season: highlight_count} if season else {}

    logger.info("🎯 Calculating Charity Stripe Regular...")
    charity_count = calculate_charity_stripe_regular(session, season, recalculate)
    results["charity_stripe_regular"] = {season: charity_count} if season else {}

    logger.info("🛡️ Calculating Defensive Tackle...")
    defensive_count = calculate_defensive_tackle(session, season, recalculate)
    results["defensive_tackle"] = {season: defensive_count} if season else {}

    logger.info("🎨 Calculating Air Ball Artist...")
    airball_count = calculate_air_ball_artist(session, season, recalculate)
    results["air_ball_artist"] = {season: airball_count} if season else {}

    logger.info("✈️ Calculating Air Assault...")
    assault_count = calculate_air_assault(session, season, recalculate)
    results["air_assault"] = {season: assault_count} if season else {}

    logger.info("✅ ALL season awards calculation completed!")
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
    Calculate Freethrow Merchant awards - most free throws made in a single game.
    """
    award_type = WEEKLY_AWARD_TYPES["weekly_ft_king"]
    return _calculate_per_game_stat_award(
        session, award_type, season, recalculate, lambda stats: stats.total_ftm, "FT made"
    )


def calculate_hot_hand_weekly(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate The Human Cheat Code awards - highest FG% with minimum 10 shot attempts in a single game.
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
    Calculate Trigger Finger awards - most total shot attempts (2pt + 3pt) in a single game.
    """
    award_type = WEEKLY_AWARD_TYPES["trigger_finger"]
    return _calculate_per_game_stat_award(
        session, award_type, season, recalculate, lambda stats: stats.total_2pa + stats.total_3pa, "shot attempts"
    )


def calculate_weekly_whiffer(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Weekly Whiffer awards - most total missed shots in a single game.
    """
    award_type = WEEKLY_AWARD_TYPES["weekly_whiffer"]
    return _calculate_per_game_stat_award(
        session,
        award_type,
        season,
        recalculate,
        lambda stats: (stats.total_2pa - stats.total_2pm)
        + (stats.total_3pa - stats.total_3pm)
        + (stats.total_fta - stats.total_ftm),
        "missed shots",
    )


def calculate_human_howitzer(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Human Howitzer awards - most 3-point shots made in a single game.
    """
    award_type = WEEKLY_AWARD_TYPES["human_howitzer"]
    return _calculate_per_game_stat_award(
        session, award_type, season, recalculate, lambda stats: stats.total_3pm, "3PM"
    )


def calculate_dub_club(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Dub Club awards - players who score 20+ points in a single game during the week.
    Multiple players can earn this award in the same week.
    """
    award_type = WEEKLY_AWARD_TYPES["dub_club"]
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
            _ = _calculate_dub_club_winners(session, weekly_games, week_start, season_key, recalculate)
            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    return dict(awards_given)


# Helper functions for weekly awards


def _calculate_weekly_stat_award(
    session: Session, award_type: str, season: str | None, recalculate: bool, stat_calculator, stat_name: str
) -> dict[str, int]:
    """
    Generic helper for calculating weekly awards based on a single stat (LEGACY - sums across all games).
    NOTE: This is now deprecated for most awards. Use _calculate_per_game_stat_award instead.
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


def _calculate_per_game_stat_award(
    session: Session, award_type: str, season: str | None, recalculate: bool, stat_calculator, stat_name: str
) -> dict[str, int]:
    """
    Generic helper for calculating awards based on best single-game performance.
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
            # Track best single-game performance for each player
            player_best_stats = {}

            for game in weekly_games:
                for stat in game.player_game_stats:
                    stat_value = stat_calculator(stat)
                    player_id = stat.player_id

                    # Track the best single-game performance for each player
                    if player_id not in player_best_stats or stat_value > player_best_stats[player_id]["value"]:
                        player_best_stats[player_id] = {
                            "value": stat_value,
                            "game_id": game.id,
                        }

            if not player_best_stats:
                continue

            # Find winner(s) - players with the highest single-game stat
            max_stat = max(data["value"] for data in player_best_stats.values())
            winners = [pid for pid, data in player_best_stats.items() if data["value"] == max_stat]

            # Create awards
            for player_id in winners:
                award = create_player_award_safe(
                    session=session,
                    player_id=player_id,
                    season=season_key,
                    award_type=award_type,
                    week_date=week_start,
                    points_scored=None,
                    game_id=player_best_stats[player_id]["game_id"],
                )
                if award:
                    award.stat_value = float(max_stat)
                    logger.debug(
                        f"Awarded {award_type} to player {player_id} with {max_stat} {stat_name} in single game"
                    )

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
    """Calculate winners for The Human Cheat Code award (highest FG% with 10+ attempts in single game)."""
    # Track best single-game FG% for each player
    player_best_fg_pct = {}

    # Check each game for qualifying performances
    for game in weekly_games:
        for stat in game.player_game_stats:
            fgm = stat.total_2pm + stat.total_3pm
            fga = stat.total_2pa + stat.total_3pa

            # Only consider games with 10+ attempts
            if fga >= 10:
                fg_pct = fgm / fga if fga > 0 else 0.0
                player_id = stat.player_id

                # Track the best single-game FG% for each player
                if player_id not in player_best_fg_pct or fg_pct > player_best_fg_pct[player_id]["percentage"]:
                    player_best_fg_pct[player_id] = {
                        "percentage": fg_pct,
                        "game_id": game.id,
                    }

    if not player_best_fg_pct:
        logger.info(f"No players qualified for Human Cheat Code (10+ attempts in single game) in week {week_start}")
        return []

    # Find winner(s) - players with the highest single-game FG%
    max_percentage = max(data["percentage"] for data in player_best_fg_pct.values())
    winners = [pid for pid, data in player_best_fg_pct.items() if data["percentage"] == max_percentage]

    # Create awards
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=WEEKLY_AWARD_TYPES["hot_hand_weekly"],
            week_date=week_start,
            points_scored=None,
            game_id=player_best_fg_pct[player_id]["game_id"],
        )
        if award:
            award.stat_value = max_percentage
            logger.debug(f"Awarded Human Cheat Code to player {player_id} with {max_percentage:.1%} FG% in single game")

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


def _calculate_dub_club_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """Calculate winners for Dub Club award (20+ points in a single game)."""
    # Track all qualifying games for award creation
    qualifying_performances = []

    # Check each game for 20+ point performances
    for game in weekly_games:
        for stat in game.player_game_stats:
            total_points = (stat.total_2pm * 2) + (stat.total_3pm * 3) + stat.total_ftm

            if total_points >= DUB_CLUB_POINT_THRESHOLD:
                qualifying_performances.append(
                    {
                        "player_id": stat.player_id,
                        "points": total_points,
                        "game_id": game.id,
                    }
                )

    if not qualifying_performances:
        return []

    # Create awards for all qualifying performances
    winners = set()
    for performance in qualifying_performances:
        award = create_player_award_safe(
            session=session,
            player_id=performance["player_id"],
            season=season,
            award_type=WEEKLY_AWARD_TYPES["dub_club"],
            week_date=week_start,
            points_scored=performance["points"],
            game_id=performance["game_id"],
        )
        if award:
            winners.add(performance["player_id"])
            logger.debug(
                f"Awarded Dub Club to player {performance['player_id']} "
                + f"for {performance['points']} points in game {performance['game_id']} "
                + f"in week {week_start}"
            )

    session.flush()
    return list(winners)


def calculate_marksman_award(session: Session, season: str | None = None, recalculate: bool = False) -> dict[str, int]:
    """
    Calculate Marksman Award - most efficient shooter with 4-8 field goal attempts in a single game.
    """
    award_type = WEEKLY_AWARD_TYPES["marksman_award"]
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
            _ = _calculate_marksman_winners(session, weekly_games, week_start, season_key, recalculate)
            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    return dict(awards_given)


def calculate_perfect_performance(
    session: Session, season: str | None = None, recalculate: bool = False
) -> dict[str, int]:
    """
    Calculate Perfect Performance Award - made 100% of shots (minimum 3 makes) in a single game.
    """
    award_type = WEEKLY_AWARD_TYPES["perfect_performance"]
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
            _ = _calculate_perfect_performance_winners(session, weekly_games, week_start, season_key, recalculate)
            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)

    session.commit()
    return dict(awards_given)


def calculate_breakout_performance(
    session: Session, season: str | None = None, recalculate: bool = False
) -> dict[str, int]:
    """
    Calculate Breakout Performance Award - biggest scoring improvement over season average in a single game.
    """
    award_type = WEEKLY_AWARD_TYPES["breakout_performance"]
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
        # Skip seasons we're not interested in
        if season and season_key != season:
            continue

        for week_start, weekly_games in weeks.items():
            logger.info(f"  🗓️  Processing breakout performance for week {week_start}")
            _ = _calculate_breakout_performance_winners(session, weekly_games, week_start, season_key, recalculate)
            week_awards = get_awards_by_week(session, award_type, week_start, season_key)
            awards_given[season_key] += len(week_awards)
            logger.info(f"    ✅ Week {week_start} completed, {len(week_awards)} awards")

    session.commit()
    return dict(awards_given)


def _calculate_marksman_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """Calculate winners for Marksman Award (most efficient shooter with 4-8 FGA in single game)."""
    # Track best single-game FG% for each player with 4-8 attempts
    player_best_fg_pct = {}

    # Check each game for qualifying performances
    for game in weekly_games:
        for stat in game.player_game_stats:
            fgm = stat.total_2pm + stat.total_3pm
            fga = stat.total_2pa + stat.total_3pa

            # Only consider games with 4-8 attempts (inclusive)
            if 4 <= fga <= 8:
                fg_pct = fgm / fga if fga > 0 else 0.0
                player_id = stat.player_id

                # Track the best single-game FG% for each player
                if player_id not in player_best_fg_pct or fg_pct > player_best_fg_pct[player_id]["percentage"]:
                    player_best_fg_pct[player_id] = {
                        "percentage": fg_pct,
                        "game_id": game.id,
                    }

    if not player_best_fg_pct:
        logger.info(f"No players qualified for Marksman Award (4-8 attempts in single game) in week {week_start}")
        return []

    # Find winner(s) - players with the highest single-game FG%
    max_percentage = max(data["percentage"] for data in player_best_fg_pct.values())
    winners = [pid for pid, data in player_best_fg_pct.items() if data["percentage"] == max_percentage]

    # Create awards
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=WEEKLY_AWARD_TYPES["marksman_award"],
            week_date=week_start,
            points_scored=None,
            game_id=player_best_fg_pct[player_id]["game_id"],
        )
        if award:
            award.stat_value = max_percentage
            logger.debug(f"Awarded Marksman to player {player_id} with {max_percentage:.1%} FG% in single game")

    session.flush()
    return winners


def _calculate_perfect_performance_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """Calculate winners for Perfect Performance Award (100% shooting with minimum 3 makes)."""
    winners = []

    # Check each game for perfect performances
    for game in weekly_games:
        for stat in game.player_game_stats:
            total_makes = stat.total_2pm + stat.total_3pm + stat.total_ftm

            # Must have at least 3 makes
            if total_makes >= 3:
                # Check if player missed any shots
                perfect_2pt = stat.total_2pa == stat.total_2pm
                perfect_3pt = stat.total_3pa == stat.total_3pm
                perfect_ft = stat.total_fta == stat.total_ftm

                if perfect_2pt and perfect_3pt and perfect_ft:
                    player_id = stat.player_id

                    # Create award (can have multiple winners in same week)
                    award = create_player_award_safe(
                        session=session,
                        player_id=player_id,
                        season=season,
                        award_type=WEEKLY_AWARD_TYPES["perfect_performance"],
                        week_date=week_start,
                        points_scored=None,
                        game_id=game.id,
                    )
                    if award:
                        award.stat_value = float(total_makes)
                        winners.append(player_id)
                        logger.debug(
                            f"Awarded Perfect Performance to player {player_id} with {total_makes} perfect makes"
                        )

    session.flush()
    return winners


def _get_player_season_averages_before_week(session: Session, season: str, week_start: date) -> dict:
    """Get season averages for all players before a specific week (optimized single query)."""
    from sqlalchemy import extract, func

    from app.data_access.models import Game, PlayerGameStats

    logger.info(f"    🔍 Querying season averages for season {season} before week {week_start}")

    # Single query to get all player averages before the specified week
    try:
        query = (
            session.query(
                PlayerGameStats.player_id,
                func.count(PlayerGameStats.id).label("games_played"),
                func.sum(
                    (PlayerGameStats.total_2pm * 2) + (PlayerGameStats.total_3pm * 3) + PlayerGameStats.total_ftm
                ).label("total_points"),
            )
            .join(Game)
            .filter(Game.date < week_start, extract("year", Game.date) == int(season))
            .group_by(PlayerGameStats.player_id)
            .having(func.count(PlayerGameStats.id) >= 3)  # Min 3 games
            .all()
        )
    except Exception as e:
        logger.error(f"    ❌ Error in season averages query: {e}")
        return {}

    query_len = len(query) if hasattr(query, "__len__") else "unknown"
    logger.info(f"    📊 Query returned {query_len} player records")

    player_averages = {}
    # Process query results - handle both real results and mocked objects
    try:
        query_items = list(query) if query else []
    except (TypeError, AttributeError):
        # Handle cases where query cannot be iterated (e.g., mocked objects)
        query_items = []

    for player_id, games_played, total_points in query_items:
        avg_ppg = total_points / games_played if games_played > 0 else 0.0
        if avg_ppg > 2.0:  # Filter low scorers
            player_averages[player_id] = {
                "games_played": games_played,
                "avg_points": avg_ppg,
                "total_points": total_points,
            }

    logger.info(f"    ✅ Filtered to {len(player_averages)} qualified players (>2.0 PPG)")
    return player_averages


def _calculate_breakout_performance_winners(
    session: Session, weekly_games: list, week_start: date, season: str, recalculate: bool = False
) -> list[int]:
    """Calculate winners for Breakout Performance Award (optimized version)."""

    # Pre-compute all player season averages before this week (single efficient query)
    player_averages = _get_player_season_averages_before_week(session, season, week_start)

    if not player_averages:
        logger.info(f"No qualified players for Breakout Performance Award in week {week_start}")
        return []

    player_improvement_scores = {}

    # Check each game for breakout performances
    for game in weekly_games:
        for stat in game.player_game_stats:
            player_id = stat.player_id

            # Skip if player doesn't have qualifying season average
            if player_id not in player_averages:
                continue

            current_game_points = (stat.total_2pm * 2) + (stat.total_3pm * 3) + stat.total_ftm
            avg_ppg = player_averages[player_id]["avg_points"]

            # Calculate improvement score
            improvement_score = (current_game_points - avg_ppg) / avg_ppg

            # Track the highest improvement score for each player
            if (
                player_id not in player_improvement_scores
                or improvement_score > player_improvement_scores[player_id]["score"]
            ):
                player_improvement_scores[player_id] = {
                    "score": improvement_score,
                    "game_points": current_game_points,
                    "avg_ppg": avg_ppg,
                    "game_id": game.id,
                }

    if not player_improvement_scores:
        logger.info(f"No players qualified for Breakout Performance Award in week {week_start}")
        return []

    # Find winner(s) - players with the highest improvement score
    max_improvement = max(data["score"] for data in player_improvement_scores.values())
    winners = [pid for pid, data in player_improvement_scores.items() if data["score"] == max_improvement]

    # Create awards
    for player_id in winners:
        data = player_improvement_scores[player_id]
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type=WEEKLY_AWARD_TYPES["breakout_performance"],
            week_date=week_start,
            points_scored=data["game_points"],
            game_id=data["game_id"],
        )
        if award:
            award.stat_value = data["score"]
            logger.debug(
                f"Awarded Breakout Performance to player {player_id} - "
                f"{data['game_points']} pts vs {data['avg_ppg']:.1f} avg ({data['score']:.1%} improvement)"
            )

    session.flush()
    return winners


# Season-end awards functions


def calculate_air_assault(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Air Assault award - most total shot attempts for the season.
    """

    logger.info(f"Starting Air Assault calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "air_assault", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total shot attempts for each player
    player_attempts = defaultdict(int)
    for game in season_games:
        for stat in game.player_game_stats:
            total_attempts = stat.total_2pa + stat.total_3pa + stat.total_fta
            player_attempts[stat.player_id] += total_attempts

    if not player_attempts:
        return 0

    # Find winner(s)
    max_attempts = max(player_attempts.values())
    winners = [pid for pid, attempts in player_attempts.items() if attempts == max_attempts]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type="air_assault",
            week_date=None,
            points_scored=None,
        )
        if award:
            award.stat_value = float(max_attempts)
            awards_given += 1
            logger.debug(f"Awarded Air Assault to player {player_id} with {max_attempts} total attempts")

    session.commit()
    return awards_given


def calculate_air_ball_artist(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Air Ball Artist award - most 3-point misses for the season.
    """
    logger.info(f"Starting Air Ball Artist calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "air_ball_artist", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total 3pt misses for each player
    player_misses = defaultdict(int)
    for game in season_games:
        for stat in game.player_game_stats:
            three_pt_misses = stat.total_3pa - stat.total_3pm
            player_misses[stat.player_id] += three_pt_misses

    if not player_misses:
        return 0

    # Find winner(s)
    max_misses = max(player_misses.values())
    winners = [pid for pid, misses in player_misses.items() if misses == max_misses]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type="air_ball_artist",
            week_date=None,
            points_scored=None,
        )
        if award:
            award.stat_value = float(max_misses)
            awards_given += 1
            logger.debug(f"Awarded Air Ball Artist to player {player_id} with {max_misses} 3pt misses")

    session.commit()
    return awards_given


def calculate_charity_stripe_regular(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Charity Stripe Regular award - most free throws made for the season.
    """
    logger.info(f"Starting Charity Stripe Regular calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "charity_stripe_regular", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total FT made for each player
    player_ftm = defaultdict(int)
    for game in season_games:
        for stat in game.player_game_stats:
            player_ftm[stat.player_id] += stat.total_ftm

    if not player_ftm:
        return 0

    # Find winner(s)
    max_ftm = max(player_ftm.values())
    winners = [pid for pid, ftm in player_ftm.items() if ftm == max_ftm]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type="charity_stripe_regular",
            week_date=None,
            points_scored=None,
        )
        if award:
            award.stat_value = float(max_ftm)
            awards_given += 1
            logger.debug(f"Awarded Charity Stripe Regular to player {player_id} with {max_ftm} FTM")

    session.commit()
    return awards_given


def calculate_defensive_tackle(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Defensive Tackle award - most fouls for the season.
    """
    logger.info(f"Starting Defensive Tackle calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "defensive_tackle", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total fouls for each player
    player_fouls = defaultdict(int)
    for game in season_games:
        for stat in game.player_game_stats:
            player_fouls[stat.player_id] += stat.fouls

    if not player_fouls:
        return 0

    # Find winner(s)
    max_fouls = max(player_fouls.values())
    winners = [pid for pid, fouls in player_fouls.items() if fouls == max_fouls]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type="defensive_tackle",
            week_date=None,
            points_scored=None,
        )
        if award:
            award.stat_value = float(max_fouls)
            awards_given += 1
            logger.debug(f"Awarded Defensive Tackle to player {player_id} with {max_fouls} fouls")

    session.commit()
    return awards_given


def calculate_efficiency_expert(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Efficiency Expert award - best field goal percentage for the season.
    """
    logger.info(f"Starting Efficiency Expert calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "efficiency_expert", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total FG stats for each player
    player_stats = defaultdict(lambda: {"made": 0, "attempted": 0})
    for game in season_games:
        for stat in game.player_game_stats:
            player_stats[stat.player_id]["made"] += stat.total_2pm + stat.total_3pm
            player_stats[stat.player_id]["attempted"] += stat.total_2pa + stat.total_3pa

    # Calculate percentages (minimum attempts required)
    player_percentages = {}
    for player_id, stats in player_stats.items():
        if stats["attempted"] >= 10:  # Minimum 10 attempts
            player_percentages[player_id] = stats["made"] / stats["attempted"]

    if not player_percentages:
        return 0

    # Find winner(s)
    max_percentage = max(player_percentages.values())
    winners = [pid for pid, pct in player_percentages.items() if pct == max_percentage]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type="efficiency_expert",
            week_date=None,
            points_scored=None,
        )
        if award:
            award.stat_value = max_percentage
            awards_given += 1
            logger.debug(f"Awarded Efficiency Expert to player {player_id} with {max_percentage:.1%} FG%")

    session.commit()
    return awards_given


def calculate_human_highlight_reel(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Human Highlight Reel award - most field goals made for the season.
    """
    logger.info(f"Starting Human Highlight Reel calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "human_highlight_reel", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total FG made for each player
    player_fgm = defaultdict(int)
    for game in season_games:
        for stat in game.player_game_stats:
            player_fgm[stat.player_id] += stat.total_2pm + stat.total_3pm

    if not player_fgm:
        return 0

    # Find winner(s)
    max_fgm = max(player_fgm.values())
    winners = [pid for pid, fgm in player_fgm.items() if fgm == max_fgm]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type="human_highlight_reel",
            week_date=None,
            points_scored=None,
        )
        if award:
            award.stat_value = float(max_fgm)
            awards_given += 1
            logger.debug(f"Awarded Human Highlight Reel to player {player_id} with {max_fgm} FGM")

    session.commit()
    return awards_given


def calculate_sharpshooter(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Sharpshooter award - best 3-point percentage for the season.
    """
    logger.info(f"Starting Sharpshooter calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "sharpshooter", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total 3pt stats for each player
    player_stats = defaultdict(lambda: {"made": 0, "attempted": 0})
    for game in season_games:
        for stat in game.player_game_stats:
            player_stats[stat.player_id]["made"] += stat.total_3pm
            player_stats[stat.player_id]["attempted"] += stat.total_3pa

    # Calculate percentages (minimum attempts required)
    player_percentages = {}
    for player_id, stats in player_stats.items():
        if stats["attempted"] >= 5:  # Minimum 5 attempts
            player_percentages[player_id] = stats["made"] / stats["attempted"]

    if not player_percentages:
        return 0

    # Find winner(s)
    max_percentage = max(player_percentages.values())
    winners = [pid for pid, pct in player_percentages.items() if pct == max_percentage]

    # Create awards
    awards_given = 0
    for player_id in winners:
        award = create_player_award_safe(
            session=session,
            player_id=player_id,
            season=season,
            award_type="sharpshooter",
            week_date=None,
            points_scored=None,
        )
        if award:
            award.stat_value = max_percentage
            awards_given += 1
            logger.debug(f"Awarded Sharpshooter to player {player_id} with {max_percentage:.1%} 3P%")

    session.commit()
    return awards_given


def _get_season_player_stats(session: Session, season: str) -> dict:
    """
    Aggregate player statistics for an entire season.

    Args:
        session: Database session
        season: Season string (e.g., "2024")

    Returns:
        Dict with player_id -> aggregated stats
    """
    from collections import defaultdict

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

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
            player_id = stat.player_id
            player_stats[player_id]["total_2pm"] += stat.total_2pm
            player_stats[player_id]["total_2pa"] += stat.total_2pa
            player_stats[player_id]["total_3pm"] += stat.total_3pm
            player_stats[player_id]["total_3pa"] += stat.total_3pa
            player_stats[player_id]["total_ftm"] += stat.total_ftm
            player_stats[player_id]["total_fta"] += stat.total_fta
            player_stats[player_id]["total_fouls"] += stat.fouls

    return dict(player_stats)


def calculate_top_scorer(session: Session, season: str, recalculate: bool = False) -> int:
    """
    Calculate Top Scorer award - most points scored for the season.
    """
    logger.info(f"Starting Top Scorer calculation for season: {season}, recalculate: {recalculate}")

    if recalculate:
        delete_awards_by_season_and_type(session, "top_scorer", season)
        session.commit()

    # Get all games for the season
    games = crud_game.get_all_games(session)
    season_games = [g for g in games if get_season_from_date(g.date) == season]

    if not season_games:
        logger.info(f"No games found for season {season}")
        return 0

    # Calculate total points for each player
    player_points = defaultdict(int)
    for game in season_games:
        for stat in game.player_game_stats:
            total_points = (stat.total_2pm * 2) + (stat.total_3pm * 3) + stat.total_ftm
            player_points[stat.player_id] += total_points

    if not player_points:
        return 0

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
            award_type="top_scorer",
            week_date=None,
            points_scored=max_points,
        )
        if award:
            award.stat_value = float(max_points)
            awards_given += 1
            logger.debug(f"Awarded Top Scorer to player {player_id} with {max_points} points")

    session.commit()
    return awards_given
