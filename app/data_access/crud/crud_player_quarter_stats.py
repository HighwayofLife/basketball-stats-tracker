"""
CRUD operations for PlayerQuarterStats model.
"""

from sqlalchemy.orm import Session

from app.data_access.models import PlayerQuarterStats


def create_player_quarter_stats(
    db: Session, player_game_stat_id: int, quarter_number: int, stats: dict[str, int]
) -> PlayerQuarterStats:
    """
    Create a new player quarter statistics record.

    Args:
        db: SQLAlchemy database session
        player_game_stat_id: ID of the PlayerGameStats record this quarter stats belongs to
        quarter_number: The quarter number (1-4)
        stats: Dictionary with keys corresponding to PlayerQuarterStats attributes
               (ftm, fta, fg2m, fg2a, fg3m, fg3a)

    Returns:
        The created PlayerQuarterStats instance
    """
    # Create with required fields
    quarter_stats = PlayerQuarterStats(player_game_stat_id=player_game_stat_id, quarter_number=quarter_number)

    # Update with optional stats fields from the dictionary
    for key, value in stats.items():
        if hasattr(quarter_stats, key):
            setattr(quarter_stats, key, value)

    db.add(quarter_stats)
    db.commit()
    db.refresh(quarter_stats)
    return quarter_stats


def get_player_quarter_stats(db: Session, player_game_stat_id: int) -> list[PlayerQuarterStats]:
    """
    Get all quarter stats for a specific player game stats record.

    Args:
        db: SQLAlchemy database session
        player_game_stat_id: ID of the PlayerGameStats to get quarter stats for

    Returns:
        List of PlayerQuarterStats instances for all quarters
    """
    return (
        db.query(PlayerQuarterStats)
        .filter(PlayerQuarterStats.player_game_stat_id == player_game_stat_id)
        .order_by(PlayerQuarterStats.quarter_number)
        .all()
    )


def get_player_quarter_stats_by_game_stat(db: Session, player_game_stat_id: int) -> list[PlayerQuarterStats]:
    """
    Get all quarter stats for a specific player game stats record.
    (Alias for get_player_quarter_stats for backward compatibility)

    Args:
        db: SQLAlchemy database session
        player_game_stat_id: ID of the PlayerGameStats to get quarter stats for

    Returns:
        List of PlayerQuarterStats instances for all quarters
    """
    return get_player_quarter_stats(db, player_game_stat_id)


def get_quarter_stats_by_quarter(
    db: Session, player_game_stat_id: int, quarter_number: int
) -> PlayerQuarterStats | None:
    """
    Get a specific quarter's stats for a player.

    Args:
        db: SQLAlchemy database session
        player_game_stat_id: ID of the PlayerGameStats
        quarter_number: The quarter number (1-4)

    Returns:
        PlayerQuarterStats instance if found, None otherwise
    """
    return (
        db.query(PlayerQuarterStats)
        .filter(
            PlayerQuarterStats.player_game_stat_id == player_game_stat_id,
            PlayerQuarterStats.quarter_number == quarter_number,
        )
        .first()
    )
