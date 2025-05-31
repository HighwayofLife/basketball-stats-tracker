"""Authentication endpoints for the Basketball Stats Tracker."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import User, UserRole
from app.auth.oauth import OAUTH_ENABLED, OAuthHandler, oauth
from app.auth.service import AuthService
from app.dependencies import get_db
from app.web_ui.schemas import RoleUpdateRequest

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


class ProfileUpdate(BaseModel):
    email: EmailStr
    full_name: str | None = None


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
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
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
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
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
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
    password_data: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
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
async def list_users(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """List all users (admin only)."""
    users = db.query(User).all()
    return users


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int, role: UserRole, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Update user role (admin only)."""
    auth_service = AuthService(db)

    if auth_service.update_user_role(user_id, role):
        return {"message": f"User role updated to {role.value}"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.delete("/users/{user_id}")
async def deactivate_user(user_id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Deactivate a user (admin only)."""
    auth_service = AuthService(db)

    if auth_service.deactivate_user(user_id):
        return {"message": "User deactivated successfully"}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


# OAuth endpoints
@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth login."""
    if not OAUTH_ENABLED:
        raise HTTPException(status_code=503, detail="OAuth is not configured")

    # Determine redirect URI based on request
    if request.url.hostname == "localhost":
        redirect_uri = f"{request.url.scheme}://{request.url.netloc}/auth/google/callback"
    else:
        # Production URL
        redirect_uri = "https://league-stats.net/auth/google/callback"

    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback."""
    oauth_handler = OAuthHandler(db)

    try:
        result = await oauth_handler.handle_google_callback(request)
        tokens = result["tokens"]

        # Create response with redirect to home page
        response = RedirectResponse(url="/", status_code=302)

        # Set cookies for tokens (you might want to use httponly cookies in production)
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=30 * 24 * 60 * 60,  # 30 days
        )

        return response

    except HTTPException:
        raise
    except Exception:
        # Redirect to login page with error
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)


@router.get("/oauth/status")
async def oauth_status():
    """Check if OAuth is configured."""
    return {"oauth_enabled": OAUTH_ENABLED}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile information."""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Update user profile information."""
    auth_service = AuthService(db)

    try:
        # Check if email is being changed and if it's already taken
        if profile_data.email != current_user.email:
            existing_user = auth_service.get_user_by_email(profile_data.email)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is already in use")

        # Update user profile
        current_user.email = profile_data.email
        if profile_data.full_name is not None:
            current_user.full_name = profile_data.full_name

        db.commit()
        db.refresh(current_user)

        return current_user

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Get all users (admin only)."""
    return db.query(User).all()


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int, role_data: RoleUpdateRequest, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Update user role (admin only)."""
    auth_service = AuthService(db)

    try:
        success = auth_service.update_user_role(user_id, role_data.role)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return {"message": "User role updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/users/{user_id}/deactivate")
async def deactivate_user_endpoint(
    user_id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Deactivate a user (admin only)."""
    auth_service = AuthService(db)

    success = auth_service.deactivate_user(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {"message": "User deactivated successfully"}


@router.post("/users/{user_id}/activate")
async def activate_user_endpoint(
    user_id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Activate a user (admin only)."""
    auth_service = AuthService(db)

    # Add activate method to auth service
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = True
    db.commit()

    return {"message": "User activated successfully"}
