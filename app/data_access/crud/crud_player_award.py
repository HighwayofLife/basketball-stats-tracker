# app/data_access/crud/crud_player_award.py

from datetime import date

from sqlalchemy.orm import Session

from app.data_access.models import PlayerAward


def create_player_award(
    session: Session, player_id: int, season: str, award_type: str, week_date: date, points_scored: int | None = None
) -> PlayerAward:
    """Create a new player award record."""
    award = PlayerAward(
        player_id=player_id, season=season, award_type=award_type, week_date=week_date, points_scored=points_scored
    )
    session.add(award)
    session.flush()  # To get the ID
    return award


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


def delete_awards_for_week(session: Session, award_type: str, week_date: date, season: str) -> int:
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


def get_awards_by_week(session: Session, award_type: str, week_date: date, season: str) -> list[PlayerAward]:
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
