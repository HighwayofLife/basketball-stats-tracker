"""CRUD operations for player season statistics."""

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.data_access.transaction import transaction
from app.data_access.models import Player, PlayerSeasonStats


def get_player_season_stats(db: Session, player_id: int, season: str) -> PlayerSeasonStats | None:
    """Get season statistics for a specific player and season.

    Args:
        db: Database session
        player_id: ID of the player
        season: Season string (e.g., "2024-2025")

    Returns:
        PlayerSeasonStats object or None if not found
    """
    return (
        db.query(PlayerSeasonStats)
        .filter(and_(PlayerSeasonStats.player_id == player_id, PlayerSeasonStats.season == season))
        .first()
    )


def get_player_all_seasons(db: Session, player_id: int) -> list[PlayerSeasonStats]:
    """Get all season statistics for a player.

    Args:
        db: Database session
        player_id: ID of the player

    Returns:
        List of PlayerSeasonStats objects
    """
    return (
        db.query(PlayerSeasonStats)
        .filter(PlayerSeasonStats.player_id == player_id)
        .order_by(PlayerSeasonStats.season.desc())
        .all()
    )


def get_season_players(db: Session, season: str, team_id: int | None = None) -> list[PlayerSeasonStats]:
    """Get all player statistics for a specific season.

    Args:
        db: Database session
        season: Season string (e.g., "2024-2025")
        team_id: Optional team ID to filter by

    Returns:
        List of PlayerSeasonStats objects
    """
    query = (
        db.query(PlayerSeasonStats)
        .join(Player)
        .filter(PlayerSeasonStats.season == season)
        .options(joinedload(PlayerSeasonStats.player).joinedload(Player.team))
    )

    if team_id:
        query = query.filter(Player.team_id == team_id)

    return query.all()


def create_player_season_stats(db: Session, player_id: int, season: str) -> PlayerSeasonStats:
    """Create a new player season statistics record.

    Args:
        db: Database session
        player_id: ID of the player
        season: Season string (e.g., "2024-2025")

    Returns:
        Created PlayerSeasonStats object
    """
    db_stats = PlayerSeasonStats(
        player_id=player_id,
        season=season,
        games_played=0,
        total_fouls=0,
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


def update_player_season_stats(
    db: Session,
    player_id: int,
    season: str,
    games_played: int | None = None,
    total_fouls: int | None = None,
    total_ftm: int | None = None,
    total_fta: int | None = None,
    total_2pm: int | None = None,
    total_2pa: int | None = None,
    total_3pm: int | None = None,
    total_3pa: int | None = None,
) -> PlayerSeasonStats | None:
    """Update player season statistics.

    Args:
        db: Database session
        player_id: ID of the player
        season: Season string
        games_played: Number of games played
        total_fouls: Total fouls
        total_ftm: Total free throws made
        total_fta: Total free throws attempted
        total_2pm: Total 2-point field goals made
        total_2pa: Total 2-point field goals attempted
        total_3pm: Total 3-point field goals made
        total_3pa: Total 3-point field goals attempted

    Returns:
        Updated PlayerSeasonStats object or None if not found
    """
    db_stats = get_player_season_stats(db, player_id, season)
    if not db_stats:
        return None

    if games_played is not None:
        db_stats.games_played = games_played
    if total_fouls is not None:
        db_stats.total_fouls = total_fouls
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


def delete_player_season_stats(db: Session, player_id: int, season: str) -> bool:
    """Delete player season statistics.

    Args:
        db: Database session
        player_id: ID of the player
        season: Season string

    Returns:
        True if deleted, False if not found
    """
    db_stats = get_player_season_stats(db, player_id, season)
    if not db_stats:
        return False

    db.delete(db_stats)
    with transaction(db):
        pass
    return True
