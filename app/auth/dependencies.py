"""FastAPI dependencies for authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.data_access.db_session import get_db_session

from .jwt_handler import verify_token
from .models import User, UserRole
from .service import AuthService

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db_session)) -> User:
    """Get current authenticated user from JWT token.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(int(user_id))

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


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
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db_session)
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
