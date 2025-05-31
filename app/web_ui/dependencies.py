"""Dependency injection for FastAPI application."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories import GameRepository, PlayerRepository, TeamRepository
from app.services.game_state_service import GameStateService


def get_team_repository(db: Session = Depends(get_db)) -> TeamRepository:  # noqa: B008
    """Get team repository dependency.

    Args:
        db: Database session

    Returns:
        Team repository instance
    """
    return TeamRepository(db)


def get_player_repository(db: Session = Depends(get_db)) -> PlayerRepository:  # noqa: B008
    """Get player repository dependency.

    Args:
        db: Database session

    Returns:
        Player repository instance
    """
    return PlayerRepository(db)


def get_game_repository(db: Session = Depends(get_db)) -> GameRepository:  # noqa: B008
    """Get game repository dependency.

    Args:
        db: Database session

    Returns:
        Game repository instance
    """
    return GameRepository(db)


def get_game_state_service(db: Session = Depends(get_db)) -> GameStateService:  # noqa: B008
    """Get game state service dependency.

    Args:
        db: Database session

    Returns:
        Game state service instance
    """
    return GameStateService(db)
