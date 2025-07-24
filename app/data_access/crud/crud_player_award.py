# app/data_access/crud/crud_player_award.py

from datetime import date

from sqlalchemy.orm import Session

from app.data_access.models import PlayerAward


def create_player_award(
    session: Session,
    player_id: int,
    season: str,
    award_type: str,
    week_date: date | None,
    points_scored: int | None = None,
) -> PlayerAward:
    """Create a new player award record."""
    award = PlayerAward(
        player_id=player_id, season=season, award_type=award_type, week_date=week_date, points_scored=points_scored
    )
    session.add(award)
    session.flush()  # To get the ID
    return award


def create_player_award_safe(
    session: Session,
    player_id: int,
    season: str,
    award_type: str,
    week_date: date | None,
    points_scored: int | None = None,
) -> PlayerAward | None:
    """Create a new player award record, or return existing one if it already exists."""
    # First check if an award already exists for this week/season
    existing_award = (
        session.query(PlayerAward)
        .filter(PlayerAward.award_type == award_type, PlayerAward.week_date == week_date, PlayerAward.season == season)
        .first()
    )

    if existing_award:
        # Award already exists, return it
        return existing_award

    # No existing award, create a new one
    try:
        return create_player_award(session, player_id, season, award_type, week_date, points_scored)
    except Exception as e:
        # If we still get a conflict (race condition), rollback and try to get existing
        session.rollback()
        if "unique_weekly_award" in str(e):
            existing_award = (
                session.query(PlayerAward)
                .filter(
                    PlayerAward.award_type == award_type,
                    PlayerAward.week_date == week_date,
                    PlayerAward.season == season,
                )
                .first()
            )
            return existing_award
        else:
            raise


def get_player_awards_by_season(session: Session, player_id: int, season: str) -> list[PlayerAward]:
    """Get all awards for a player in a specific season."""
    return (
        session.query(PlayerAward)
        .filter(PlayerAward.player_id == player_id, PlayerAward.season == season)
        .order_by(PlayerAward.week_date.desc())
        .all()
    )


def get_player_awards_by_type(session: Session, player_id: int, award_type: str) -> list[PlayerAward]:
    """Get all awards of a specific type for a player."""
    return (
        session.query(PlayerAward)
        .filter(PlayerAward.player_id == player_id, PlayerAward.award_type == award_type)
        .order_by(PlayerAward.season.desc(), PlayerAward.week_date.desc())
        .all()
    )


def get_player_award_counts_by_season(session: Session, player_id: int) -> dict[str, int]:
    """Get award counts grouped by season for a player."""
    from sqlalchemy import func

    results = (
        session.query(PlayerAward.season, func.count(PlayerAward.id).label("count"))
        .filter(PlayerAward.player_id == player_id)
        .group_by(PlayerAward.season)
        .all()
    )

    return {result.season: result.count for result in results}


def get_all_awards_for_player(session: Session, player_id: int) -> list[PlayerAward]:
    """Get all awards for a player across all seasons."""
    return (
        session.query(PlayerAward)
        .filter(PlayerAward.player_id == player_id)
        .order_by(PlayerAward.season.desc(), PlayerAward.week_date.desc())
        .all()
    )


def delete_awards_for_week(session: Session, award_type: str, week_date: date | None, season: str) -> int:
    """Delete all awards for a specific week (used for recalculation)."""
    deleted_count = (
        session.query(PlayerAward)
        .filter(PlayerAward.award_type == award_type, PlayerAward.week_date == week_date, PlayerAward.season == season)
        .delete()
    )
    return deleted_count


def delete_all_awards_by_type(session: Session, award_type: str) -> int:
    """Delete all awards of a specific type (used for full recalculation)."""
    deleted_count = session.query(PlayerAward).filter(PlayerAward.award_type == award_type).delete()
    return deleted_count


def get_awards_by_week(session: Session, award_type: str, week_date: date | None, season: str) -> list[PlayerAward]:
    """Get all awards for a specific week (useful for checking existing awards)."""
    return (
        session.query(PlayerAward)
        .filter(PlayerAward.award_type == award_type, PlayerAward.week_date == week_date, PlayerAward.season == season)
        .all()
    )


def get_recent_awards(session: Session, award_type: str, limit: int = 10) -> list[PlayerAward]:
    """Get the most recent awards of a specific type."""
    return (
        session.query(PlayerAward)
        .filter(PlayerAward.award_type == award_type)
        .order_by(PlayerAward.created_at.desc())
        .limit(limit)
        .all()
    )


def count_awards_for_player(session: Session, player_id: int, award_type: str | None = None) -> int:
    """Count total awards for a player, optionally filtered by type."""
    query = session.query(PlayerAward).filter(PlayerAward.player_id == player_id)

    if award_type:
        query = query.filter(PlayerAward.award_type == award_type)

    return query.count()


def get_season_awards(session: Session, season: str, award_type: str | None = None) -> list[PlayerAward]:
    """Get all season awards (week_date=NULL) for a specific season."""
    query = session.query(PlayerAward).filter(PlayerAward.season == season, PlayerAward.week_date.is_(None))

    if award_type:
        query = query.filter(PlayerAward.award_type == award_type)

    return query.order_by(PlayerAward.award_type, PlayerAward.created_at.desc()).all()


def get_weekly_awards(session: Session, season: str, award_type: str | None = None) -> list[PlayerAward]:
    """Get all weekly awards (week_date!=NULL) for a specific season."""
    query = session.query(PlayerAward).filter(PlayerAward.season == season, PlayerAward.week_date.isnot(None))

    if award_type:
        query = query.filter(PlayerAward.award_type == award_type)

    return query.order_by(PlayerAward.week_date.desc(), PlayerAward.award_type).all()


def delete_season_awards(session: Session, season: str, award_type: str | None = None) -> int:
    """Delete season awards for a specific season and optionally specific type."""
    query = session.query(PlayerAward).filter(PlayerAward.season == season, PlayerAward.week_date.is_(None))

    if award_type:
        query = query.filter(PlayerAward.award_type == award_type)

    deleted_count = query.delete()
    return deleted_count


def finalize_season_award(session: Session, award_id: int) -> PlayerAward | None:
    """Mark a season award as finalized."""
    award = session.query(PlayerAward).filter(PlayerAward.id == award_id).first()
    if award and not award.is_finalized:
        award.is_finalized = True
        award.award_date = date.today()
        session.flush()
    return award


def get_comprehensive_player_award_summary(session: Session, player_id: int) -> dict:
    """Get comprehensive award summary for a player including both weekly and season awards."""
    from app.services.awards_service import get_current_season

    current_season = get_current_season()

    # Get all awards for the player
    all_awards = get_all_awards_for_player(session, player_id)

    # Separate by type
    weekly_awards = [a for a in all_awards if a.week_date is not None]
    season_awards = [a for a in all_awards if a.week_date is None]

    # Group weekly awards by type
    weekly_by_type = {}
    for award in weekly_awards:
        if award.award_type not in weekly_by_type:
            weekly_by_type[award.award_type] = []
        weekly_by_type[award.award_type].append(award)

    # Group season awards by season and type
    season_by_year = {}
    for award in season_awards:
        if award.season not in season_by_year:
            season_by_year[award.season] = []
        season_by_year[award.season].append(award.award_type)

    # Calculate current season counts for weekly awards
    weekly_summary = {}
    for award_type, awards in weekly_by_type.items():
        current_season_count = len([a for a in awards if a.season == current_season])
        total_count = len(awards)
        recent_awards = sorted(awards, key=lambda x: x.created_at, reverse=True)[:5]

        weekly_summary[award_type] = {
            "current_season_count": current_season_count,
            "total_count": total_count,
            "recent_awards": [
                {
                    "season": a.season,
                    "week_date": a.week_date.isoformat() if a.week_date else None,
                    "points_scored": a.points_scored,
                    "stat_value": a.stat_value,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in recent_awards
            ],
        }

    return {
        "weekly_awards": weekly_summary,
        "season_awards": season_by_year,
        "current_season": current_season,
    }


def get_current_week_awards(session: Session) -> dict:
    """Get current week's award winners for dashboard display."""
    import logging
    from datetime import datetime, timedelta

    from app.data_access.models import Player

    logger = logging.getLogger(__name__)

    try:
        # First try current week Monday
        today = datetime.now().date()
        days_since_monday = today.weekday()
        current_week_monday = today - timedelta(days=days_since_monday)

        logger.info(f"get_current_week_awards: Today={today}, Current week Monday={current_week_monday}")

        # Get all weekly awards for the current week
        current_week_awards = (
            session.query(PlayerAward, Player)
            .join(Player, PlayerAward.player_id == Player.id)
            .filter(
                PlayerAward.week_date == current_week_monday,
                PlayerAward.week_date.is_not(None),  # Only weekly awards
            )
            .all()
        )

        logger.info(f"get_current_week_awards: Found {len(current_week_awards)} awards for current week")

        # If no awards for current week, get the most recent week with awards
        if not current_week_awards:
            logger.info("get_current_week_awards: No awards for current week, looking for most recent")
            most_recent_week = (
                session.query(PlayerAward.week_date)
                .filter(PlayerAward.week_date.is_not(None))
                .order_by(PlayerAward.week_date.desc())
                .first()
            )

            if most_recent_week:
                current_week_monday = most_recent_week[0]
                logger.info(f"get_current_week_awards: Most recent week with awards: {current_week_monday}")
                current_week_awards = (
                    session.query(PlayerAward, Player)
                    .join(Player, PlayerAward.player_id == Player.id)
                    .filter(
                        PlayerAward.week_date == current_week_monday,
                        PlayerAward.week_date.is_not(None),
                    )
                    .all()
                )
                logger.info(f"get_current_week_awards: Found {len(current_week_awards)} awards for most recent week")
            else:
                logger.warning("get_current_week_awards: No weekly awards found in database at all")

        # Group by award type using centralized config
        from app.config_data.awards import get_award_display_data

        awards_by_type = {}
        for award, player in current_week_awards:
            if award.award_type not in awards_by_type:
                awards_by_type[award.award_type] = []

            # Get display data from centralized config
            display_data = get_award_display_data(
                award.award_type, stat_value=award.stat_value, points_scored=award.points_scored
            )

            awards_by_type[award.award_type].append(
                {
                    "player_id": player.id,
                    "player_name": player.name,
                    "team_name": player.team.name if player.team else "Unknown",
                    "stat_value": award.stat_value,
                    "points_scored": award.points_scored,
                    **display_data,  # Includes award_name, award_icon, award_desc, formatted_stat, show_points
                }
            )

        result = {
            "current_week": current_week_monday.isoformat(),
            "awards": awards_by_type,
            "total_awards": len(current_week_awards),
        }

        logger.info(
            f"get_current_week_awards: Returning {result['total_awards']} total awards "
            f"for week {result['current_week']}"
        )
        return result

    except Exception as e:
        logger.error(f"get_current_week_awards: Exception occurred: {e}", exc_info=True)
        return {
            "current_week": datetime.now().date().isoformat(),
            "awards": {},
            "total_awards": 0,
        }


def get_available_award_weeks(session: Session) -> list[dict]:
    """Get all weeks that have weekly awards for the dropdown selector."""
    import logging
    from datetime import datetime, timedelta

    logger = logging.getLogger(__name__)

    try:
        # Get all distinct weeks with awards, ordered by most recent first
        weeks_with_awards = (
            session.query(PlayerAward.week_date)
            .filter(PlayerAward.week_date.is_not(None))
            .distinct()
            .order_by(PlayerAward.week_date.desc())
            .all()
        )

        weeks_list = []
        today = datetime.now().date()

        for week_tuple in weeks_with_awards:
            week_date = week_tuple[0]

            # Count awards for this week
            award_count = session.query(PlayerAward).filter(PlayerAward.week_date == week_date).count()

            # Determine if this is the current week
            days_since_monday = today.weekday()
            current_week_monday = today - timedelta(days=days_since_monday)
            is_current_week = week_date == current_week_monday

            # Format the display label
            week_label = f"Week of {week_date.strftime('%B %d, %Y')}"
            if is_current_week:
                week_label += " (Current Week)"

            weeks_list.append(
                {
                    "week_date": week_date.isoformat(),
                    "week_label": week_label,
                    "award_count": award_count,
                    "is_current": is_current_week,
                }
            )

        logger.info(f"get_available_award_weeks: Found {len(weeks_list)} weeks with awards")
        return weeks_list

    except Exception as e:
        logger.error(f"get_available_award_weeks: Exception occurred: {e}", exc_info=True)
        return []


def get_week_awards_by_date(session: Session, week_date_str: str) -> dict:
    """Get awards for a specific week date."""
    import logging
    from datetime import datetime

    from app.data_access.models import Player

    logger = logging.getLogger(__name__)

    try:
        # Parse the week date
        week_date = datetime.strptime(week_date_str, "%Y-%m-%d").date()

        # Get all weekly awards for the specified week
        week_awards = (
            session.query(PlayerAward, Player)
            .join(Player, PlayerAward.player_id == Player.id)
            .filter(
                PlayerAward.week_date == week_date,
                PlayerAward.week_date.is_not(None),
            )
            .all()
        )

        # Group by award type using centralized config
        from app.config_data.awards import get_award_display_data

        awards_by_type = {}
        for award, player in week_awards:
            if award.award_type not in awards_by_type:
                awards_by_type[award.award_type] = []

            # Get display data from centralized config
            display_data = get_award_display_data(
                award.award_type, stat_value=award.stat_value, points_scored=award.points_scored
            )

            awards_by_type[award.award_type].append(
                {
                    "player_id": player.id,
                    "player_name": player.name,
                    "team_name": player.team.name if player.team else "Unknown",
                    "stat_value": award.stat_value,
                    "points_scored": award.points_scored,
                    **display_data,  # Includes award_name, award_icon, award_desc, formatted_stat, show_points
                }
            )

        return {
            "current_week": week_date.isoformat(),
            "awards": awards_by_type,
            "total_awards": len(week_awards),
        }

    except Exception as e:
        logger.error(f"get_week_awards_by_date: Exception occurred: {e}", exc_info=True)
        return {
            "current_week": week_date_str,
            "awards": {},
            "total_awards": 0,
        }
