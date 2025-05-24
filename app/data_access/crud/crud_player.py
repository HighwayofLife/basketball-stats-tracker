"""
CRUD operations for Player model.
"""

from sqlalchemy.orm import Session

from app.data_access.models import Player


def create_player(db: Session, name: str, jersey_number: int, team_id: int) -> Player:
    """
    Create a new player in the database.

    Args:
        db: SQLAlchemy database session
        name: Player's name
        jersey_number: Player's jersey number
        team_id: ID of the team the player belongs to

    Returns:
        The created Player instance
    """
    player = Player(team_id=team_id, name=name, jersey_number=jersey_number)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def get_player_by_team_and_jersey(db: Session, team_id: int, jersey_number: int) -> Player | None:
    """
    Get a player by their team ID and jersey number.

    Args:
        db: SQLAlchemy database session
        team_id: ID of the team the player belongs to
        jersey_number: Player's jersey number

    Returns:
        Player instance if found, None otherwise
    """
    return db.query(Player).filter(Player.team_id == team_id, Player.jersey_number == jersey_number).first()


def get_player_by_id(db: Session, player_id: int) -> Player | None:
    """
    Get a player by their ID.

    Args:
        db: SQLAlchemy database session
        player_id: ID of the player to find

    Returns:
        Player instance if found, None otherwise
    """
    return db.query(Player).filter(Player.id == player_id).first()


def get_players_by_team(db: Session, team_id: int) -> list[Player]:
    """
    Get all players belonging to a specific team.

    Args:
        db: SQLAlchemy database session
        team_id: ID of the team to get players for

    Returns:
        List of Player instances belonging to the team
    """
    return db.query(Player).filter(Player.team_id == team_id).all()


def get_all_players(db: Session) -> list[Player]:
    """
    Get all players from the database.

    Args:
        db: SQLAlchemy database session

    Returns:
        List of all Player instances
    """
    return db.query(Player).all()
