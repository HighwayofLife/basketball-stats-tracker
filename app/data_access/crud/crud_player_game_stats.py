"""
CRUD operations for PlayerGameStats model.
"""

from sqlalchemy.orm import Session

from app.data_access.models import PlayerGameStats


def create_player_game_stats(
    db: Session, game_id: int, player_id: int, fouls: int, playing_for_team_id: int | None = None
) -> PlayerGameStats:
    """
    Create a new player game statistics record.

    Args:
        db: SQLAlchemy database session
        game_id: ID of the game
        player_id: ID of the player
        fouls: Number of fouls committed by the player in the game
        playing_for_team_id: ID of the team the player played for (for substitutes)

    Returns:
        The created PlayerGameStats instance
    """
    stats = PlayerGameStats(game_id=game_id, player_id=player_id, fouls=fouls, playing_for_team_id=playing_for_team_id)
    db.add(stats)
    db.commit()
    db.refresh(stats)
    return stats


def update_player_game_stats_totals(db: Session, player_game_stat_id: int, totals: dict[str, int]) -> PlayerGameStats:
    """
    Update the totals for a player's game stats.

    Args:
        db: SQLAlchemy database session
        player_game_stat_id: ID of the PlayerGameStats record to update
        totals: Dictionary with keys corresponding to PlayerGameStats attributes
               (total_ftm, total_fta, total_2pm, total_2pa, total_3pm, total_3pa)

    Returns:
        The updated PlayerGameStats instance
    """
    stats = db.query(PlayerGameStats).filter(PlayerGameStats.id == player_game_stat_id).first()
    if stats is None:
        raise ValueError(f"PlayerGameStats with ID {player_game_stat_id} not found")

    # Update the fields from the totals dictionary
    for key, value in totals.items():
        if hasattr(stats, key):
            setattr(stats, key, value)

    db.commit()
    db.refresh(stats)
    return stats


def get_player_game_stats_by_game(db: Session, game_id: int) -> list[PlayerGameStats]:
    """
    Get all player game stats for a specific game.

    Args:
        db: SQLAlchemy database session
        game_id: ID of the game to get stats for

    Returns:
        List of PlayerGameStats instances for the specified game
    """
    return db.query(PlayerGameStats).filter(PlayerGameStats.game_id == game_id).all()


def get_player_game_stats(db: Session, game_id: int, player_id: int) -> PlayerGameStats | None:
    """
    Get a player's game stats for a specific game.

    Args:
        db: SQLAlchemy database session
        game_id: ID of the game
        player_id: ID of the player

    Returns:
        PlayerGameStats instance if found, None otherwise
    """
    return (
        db.query(PlayerGameStats)
        .filter(PlayerGameStats.game_id == game_id, PlayerGameStats.player_id == player_id)
        .first()
    )


def get_player_game_stats_by_game_and_player(db: Session, game_id: int, player_id: int) -> PlayerGameStats | None:
    """
    Get a player's game stats for a specific game.
    (Alias for get_player_game_stats for backward compatibility)

    Args:
        db: SQLAlchemy database session
        game_id: ID of the game
        player_id: ID of the player

    Returns:
        PlayerGameStats instance if found, None otherwise
    """
    return get_player_game_stats(db, game_id, player_id)


def get_player_game_stats_for_game_and_team(db: Session, game_id: int, team_id: int) -> list[PlayerGameStats]:
    """
    Get all player game stats for a specific team in a given game.

    Args:
        db: SQLAlchemy database session
        game_id: ID of the game
        team_id: ID of the team

    Returns:
        List of PlayerGameStats instances for the specified team in the game
    """
    from app.data_access.models import Player

    return (
        db.query(PlayerGameStats)
        .join(Player)
        .filter(PlayerGameStats.game_id == game_id, Player.team_id == team_id)
        .all()
    )
