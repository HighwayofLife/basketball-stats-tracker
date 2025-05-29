"""Authentication endpoints for the Basketball Stats Tracker."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User, UserRole
from app.auth.service import AuthService
from app.data_access.db_session import get_db_session

router = APIRouter(prefix="/auth", tags=["authentication"])


# Pydantic models for requests/responses
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db_session)):
    """Register a new user."""
    auth_service = AuthService(db)

    try:
        user = auth_service.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db_session)):
    """Login and receive access tokens."""
    auth_service = AuthService(db)

    user = auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = auth_service.create_tokens(user)
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db_session)):
    """Refresh access token using refresh token."""
    from app.auth.jwt_handler import verify_token

    # Verify refresh token
    payload = verify_token(token_data.refresh_token, token_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Get user
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(int(payload.get("sub")))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    tokens = auth_service.create_tokens(user)
    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db_session)
):
    """Change current user's password."""
    auth_service = AuthService(db)

    # Verify current password
    if not auth_service.authenticate_user(current_user.username, password_data.current_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    # Update password
    if auth_service.update_user_password(current_user.id, password_data.new_password):
        return {"message": "Password changed successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password")


# Admin endpoints
@router.get("/users", response_model=list[UserResponse])
async def list_users(admin_user: User = Depends(require_admin), db: Session = Depends(get_db_session)):
    """List all users (admin only)."""
    users = db.query(User).all()
    return users


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int, role: UserRole, admin_user: User = Depends(require_admin), db: Session = Depends(get_db_session)
):
    """Update user role (admin only)."""
    auth_service = AuthService(db)

    if auth_service.update_user_role(user_id, role):
        return {"message": f"User role updated to {role.value}"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db_session)
):
    """Deactivate a user (admin only)."""
    auth_service = AuthService(db)

    if auth_service.deactivate_user(user_id):
        return {"message": "User deactivated successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
