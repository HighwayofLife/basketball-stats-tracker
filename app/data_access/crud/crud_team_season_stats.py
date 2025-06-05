"""CRUD operations for team season statistics."""

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.data_access.transaction import transaction
from app.data_access.models import TeamSeasonStats


def get_team_season_stats(db: Session, team_id: int, season: str) -> TeamSeasonStats | None:
    """Get season statistics for a specific team and season.

    Args:
        db: Database session
        team_id: ID of the team
        season: Season string (e.g., "2024-2025")

    Returns:
        TeamSeasonStats object or None if not found
    """
    return (
        db.query(TeamSeasonStats)
        .filter(and_(TeamSeasonStats.team_id == team_id, TeamSeasonStats.season == season))
        .first()
    )


def get_team_all_seasons(db: Session, team_id: int) -> list[TeamSeasonStats]:
    """Get all season statistics for a team.

    Args:
        db: Database session
        team_id: ID of the team

    Returns:
        List of TeamSeasonStats objects
    """
    return (
        db.query(TeamSeasonStats)
        .filter(TeamSeasonStats.team_id == team_id)
        .order_by(TeamSeasonStats.season.desc())
        .all()
    )


def get_season_teams(db: Session, season: str) -> list[TeamSeasonStats]:
    """Get all team statistics for a specific season.

    Args:
        db: Database session
        season: Season string (e.g., "2024-2025")

    Returns:
        List of TeamSeasonStats objects
    """
    return (
        db.query(TeamSeasonStats)
        .filter(TeamSeasonStats.season == season)
        .options(joinedload(TeamSeasonStats.team))
        .all()
    )


def create_team_season_stats(db: Session, team_id: int, season: str) -> TeamSeasonStats:
    """Create a new team season statistics record.

    Args:
        db: Database session
        team_id: ID of the team
        season: Season string (e.g., "2024-2025")

    Returns:
        Created TeamSeasonStats object
    """
    db_stats = TeamSeasonStats(
        team_id=team_id,
        season=season,
        games_played=0,
        wins=0,
        losses=0,
        total_points_for=0,
        total_points_against=0,
        total_ftm=0,
        total_fta=0,
        total_2pm=0,
        total_2pa=0,
        total_3pm=0,
        total_3pa=0,
    )
    db.add(db_stats)
    with transaction(db, refresh=[db_stats]):
        pass
    return db_stats


def update_team_season_stats(
    db: Session,
    team_id: int,
    season: str,
    games_played: int | None = None,
    wins: int | None = None,
    losses: int | None = None,
    total_points_for: int | None = None,
    total_points_against: int | None = None,
    total_ftm: int | None = None,
    total_fta: int | None = None,
    total_2pm: int | None = None,
    total_2pa: int | None = None,
    total_3pm: int | None = None,
    total_3pa: int | None = None,
) -> TeamSeasonStats | None:
    """Update team season statistics.

    Args:
        db: Database session
        team_id: ID of the team
        season: Season string
        games_played: Number of games played
        wins: Number of wins
        losses: Number of losses
        total_points_for: Total points scored
        total_points_against: Total points allowed
        total_ftm: Total free throws made
        total_fta: Total free throws attempted
        total_2pm: Total 2-point field goals made
        total_2pa: Total 2-point field goals attempted
        total_3pm: Total 3-point field goals made
        total_3pa: Total 3-point field goals attempted

    Returns:
        Updated TeamSeasonStats object or None if not found
    """
    db_stats = get_team_season_stats(db, team_id, season)
    if not db_stats:
        return None

    if games_played is not None:
        db_stats.games_played = games_played
    if wins is not None:
        db_stats.wins = wins
    if losses is not None:
        db_stats.losses = losses
    if total_points_for is not None:
        db_stats.total_points_for = total_points_for
    if total_points_against is not None:
        db_stats.total_points_against = total_points_against
    if total_ftm is not None:
        db_stats.total_ftm = total_ftm
    if total_fta is not None:
        db_stats.total_fta = total_fta
    if total_2pm is not None:
        db_stats.total_2pm = total_2pm
    if total_2pa is not None:
        db_stats.total_2pa = total_2pa
    if total_3pm is not None:
        db_stats.total_3pm = total_3pm
    if total_3pa is not None:
        db_stats.total_3pa = total_3pa

    with transaction(db, refresh=[db_stats]):
        pass
    return db_stats


def delete_team_season_stats(db: Session, team_id: int, season: str) -> bool:
    """Delete team season statistics.

    Args:
        db: Database session
        team_id: ID of the team
        season: Season string

    Returns:
        True if deleted, False if not found
    """
    db_stats = get_team_season_stats(db, team_id, season)
    if not db_stats:
        return False

    db.delete(db_stats)
    with transaction(db):
        pass
    return True
