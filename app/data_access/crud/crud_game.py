"""
CRUD operations for Game model.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.data_access.transaction import transaction
from app.data_access.models import Game


def create_game(db: Session, date_str: str, playing_team_id: int, opponent_team_id: int) -> Game:
    """
    Create a new game in the database.

    Args:
        db: SQLAlchemy database session
        date_str: Date of the game in YYYY-MM-DD or M/D/YYYY format
        playing_team_id: ID of the home/playing team
        opponent_team_id: ID of the away/opponent team

    Returns:
        The created Game instance
    """
    # Convert string date to date object - handle both formats
    # Parse the date string as a naive datetime first
    try:
        # Try YYYY-MM-DD format first
        naive_dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            # Try M/D/YYYY format
            naive_dt = datetime.strptime(date_str, "%m/%d/%Y")
        except ValueError as e:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or M/D/YYYY") from e

    # Get just the date component without timezone issues
    # This ensures the date is interpreted as-is without timezone conversion
    game_date = naive_dt.date()

    game = Game(date=game_date, playing_team_id=playing_team_id, opponent_team_id=opponent_team_id)
    db.add(game)
    with transaction(db, refresh=[game]):
        pass
    return game


def get_game_by_id(db: Session, game_id: int) -> Game | None:
    """
    Get a game by its ID.

    Args:
        db: SQLAlchemy database session
        game_id: ID of the game to find

    Returns:
        Game instance if found, None otherwise
    """
    return db.query(Game).filter(Game.id == game_id).first()


def get_games_by_team(db: Session, team_id: int) -> list[Game]:
    """
    Get all games played by a specific team (either as home or away).

    Args:
        db: SQLAlchemy database session
        team_id: ID of the team to get games for

    Returns:
        List of Game instances involving the team
    """
    return db.query(Game).filter((Game.playing_team_id == team_id) | (Game.opponent_team_id == team_id)).all()


def get_games_by_date_range(db: Session, start_date: str, end_date: str) -> list[Game]:
    """
    Get all games within a date range.

    Args:
        db: SQLAlchemy database session
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of Game instances within the date range
    """
    # Convert string dates to date objects
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    return db.query(Game).filter(Game.date >= start_date_obj, Game.date <= end_date_obj).all()


def get_all_games(db: Session) -> list[Game]:
    """
    Get all games from the database.

    Args:
        db: SQLAlchemy database session

    Returns:
        List of all Game instances
    """
    return db.query(Game).all()
