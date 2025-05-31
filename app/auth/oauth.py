"""OAuth 2.0 configuration and handlers for Google authentication."""

import os

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from starlette.config import Config

from app.auth.service import AuthService

# OAuth configuration
config = Config()  # This will read from environment
oauth = OAuth(config)

# Configure Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Check if OAuth is configured
OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

if OAUTH_ENABLED:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
        },
    )


class OAuthHandler:
    """Handles OAuth authentication flow."""

    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthService(db)

    async def handle_google_callback(self, request: Request) -> dict:
        """Handle Google OAuth callback."""
        if not OAUTH_ENABLED:
            raise HTTPException(status_code=503, detail="OAuth is not configured")

        try:
            # Get the token from Google
            token = await oauth.google.authorize_access_token(request)

            # Get user info from token
            user_info = token.get("userinfo")
            if not user_info:
                # If userinfo not in token, fetch it separately
                user_info = await oauth.google.parse_id_token(token)

            if not user_info:
                raise HTTPException(status_code=400, detail="Failed to get user information from Google")

            # Extract user details
            email = user_info.get("email")
            name = user_info.get("name", "")
            google_id = user_info.get("sub")  # Google's unique user ID

            if not email:
                raise HTTPException(status_code=400, detail="Email not provided by Google")

            # Check if user exists by email
            user = self.auth_service.get_user_by_email(email)

            if user:
                # Update user if needed (e.g., name changed in Google)
                if user.full_name != name and name:
                    user.full_name = name
                    self.db.commit()
            else:
                # Create new user
                username = email.split("@")[0]  # Use email prefix as username
                # Ensure username is unique
                base_username = username
                counter = 1
                while self.auth_service.get_user_by_username(username):
                    username = f"{base_username}{counter}"
                    counter += 1

                user = self.auth_service.create_oauth_user(
                    username=username,
                    email=email,
                    full_name=name,
                    provider="google",
                    provider_id=google_id,
                )

            # Update last login
            self.auth_service.update_last_login(user.id)

            # Create tokens
            tokens = self.auth_service.create_tokens(user)

            return {
                "user": user,
                "tokens": tokens,
            }

        except OAuthError as e:
            raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


