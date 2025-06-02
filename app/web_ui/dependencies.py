"""Dependency injection for FastAPI application."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_current_user
from app.auth.models import User
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


def get_template_auth_context(request: Request, current_user: User | None = Depends(get_optional_current_user)) -> dict:
    """Get authentication context for templates.

    Args:
        request: FastAPI request object
        current_user: Optional current user (None if not authenticated)

    Returns:
        Dictionary with authentication context for templates
    """
    context = {
        "request": request,
        "current_user": current_user,
        "is_authenticated": current_user is not None,
        "is_admin": current_user is not None and current_user.role.upper() == "ADMIN",
        "user_role": current_user.role if current_user else None,
    }
    return context
