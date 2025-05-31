"""FastAPI dependencies for authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.dependencies import get_db

from .jwt_handler import verify_token
from .models import User, UserRole
from .service import AuthService

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from JWT token.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    import logging

    logger = logging.getLogger(__name__)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token
        payload = verify_token(token)
        if payload is None:
            logger.warning("Token verification failed - invalid token")
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token verification failed - no user ID in token")
            raise credentials_exception

        # Get user from database
        auth_service = AuthService(db)
        user = auth_service.get_user_by_id(int(user_id))

        if user is None:
            logger.warning(f"User not found in database: {user_id}")
            raise credentials_exception

        if not user.is_active:
            logger.warning(f"User {user_id} is inactive")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

        logger.info(f"Successfully authenticated user: {user.username} (ID: {user.id})")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role for access.

    Args:
        current_user: Current active user

    Returns:
        Admin user

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User | None:
    """Get current user if authenticated, None otherwise.

    Args:
        token: Optional JWT token
        db: Database session

    Returns:
        Current user or None
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


async def require_team_access(team_id: int, current_user: User = Depends(get_current_active_user)) -> User:
    """Require access to specific team (admin or team member).

    Args:
        team_id: ID of the team to check access for
        current_user: Current active user

    Returns:
        Current user if access is allowed

    Raises:
        HTTPException: If user doesn't have access to the team
    """
    # Admin users have access to all teams
    if current_user.role == UserRole.ADMIN:
        return current_user

    # Check if user belongs to the team
    if current_user.team_id != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You can only access your own team's data"
        )

    return current_user


async def require_player_access(
    player_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> User:
    """Require access to specific player (admin, team member, or the player themselves).

    Args:
        player_id: ID of the player to check access for
        current_user: Current active user
        db: Database session

    Returns:
        Current user if access is allowed

    Raises:
        HTTPException: If user doesn't have access to the player
    """
    # Admin users have access to all players
    if current_user.role == UserRole.ADMIN:
        return current_user

    # Get player to check team
    from app.data_access.models import Player

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    # Check if user belongs to the same team as the player
    if current_user.team_id != player.team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access players from your own team",
        )

    return current_user


async def require_game_access(
    game_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> User:
    """Require access to specific game (admin or team involved in game).

    Args:
        game_id: ID of the game to check access for
        current_user: Current active user
        db: Database session

    Returns:
        Current user if access is allowed

    Raises:
        HTTPException: If user doesn't have access to the game
    """
    # Admin users have access to all games
    if current_user.role == UserRole.ADMIN:
        return current_user

    # Get game to check teams
    from app.data_access.models import Game

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    # Check if user's team is involved in the game
    if current_user.team_id not in [game.playing_team_id, game.opponent_team_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You can only access games involving your team"
        )

    return current_user
