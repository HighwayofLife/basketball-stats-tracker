"""Dependency injection for FastAPI application."""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.data_access.db_session import get_db_session
from app.repositories import GameRepository, PlayerRepository, TeamRepository
from app.services.game_state_service import GameStateService


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency.

    Yields:
        Database session
    """
    with get_db_session() as session:
        yield session


def get_team_repository(db: Session = Depends(get_db)) -> TeamRepository:
    """Get team repository dependency.

    Args:
        db: Database session

    Returns:
        Team repository instance
    """
    return TeamRepository(db)


def get_player_repository(db: Session = Depends(get_db)) -> PlayerRepository:
    """Get player repository dependency.

    Args:
        db: Database session

    Returns:
        Player repository instance
    """
    return PlayerRepository(db)


def get_game_repository(db: Session = Depends(get_db)) -> GameRepository:
    """Get game repository dependency.

    Args:
        db: Database session

    Returns:
        Game repository instance
    """
    return GameRepository(db)


def get_game_state_service(db: Session = Depends(get_db)) -> GameStateService:
    """Get game state service dependency.

    Args:
        db: Database session

    Returns:
        Game state service instance
    """
    return GameStateService(db)
