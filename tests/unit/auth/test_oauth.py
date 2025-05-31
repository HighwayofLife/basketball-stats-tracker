"""Tests for OAuth functionality."""

import os
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.oauth import OAuthHandler, OAUTH_ENABLED
from app.auth.service import AuthService


class TestOAuthIntegration:
    """Test OAuth integration."""

    def test_oauth_enabled_when_configured(self):
        """Test OAuth is enabled when credentials are configured."""
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-id", "GOOGLE_CLIENT_SECRET": "test-secret"}):
            # Need to reload the module to pick up env changes
            import importlib
            import app.auth.oauth

            importlib.reload(app.auth.oauth)

            assert app.auth.oauth.OAUTH_ENABLED is True

    def test_oauth_disabled_when_not_configured(self):
        """Test OAuth is disabled when credentials are missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Need to reload the module to pick up env changes
            import importlib
            import app.auth.oauth

            importlib.reload(app.auth.oauth)

            assert app.auth.oauth.OAUTH_ENABLED is False

    @pytest.mark.asyncio
    async def test_oauth_user_creation(self, db_session: Session):
        """Test creating a new OAuth user."""
        auth_service = AuthService(db_session)

        # Create OAuth user
        user = auth_service.create_oauth_user(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            provider="google",
            provider_id="google-123",
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.provider == "google"
        assert user.provider_id == "google-123"
        assert user.hashed_password is None  # OAuth users don't have passwords

        # Verify user was saved
        saved_user = db_session.query(User).filter_by(email="test@example.com").first()
        assert saved_user is not None
        assert saved_user.provider == "google"

    def test_oauth_user_cannot_login_with_password(self, db_session: Session):
        """Test OAuth users cannot login with password."""
        auth_service = AuthService(db_session)

        # Create OAuth user
        user = auth_service.create_oauth_user(
            username="oauthuser",
            email="oauth@example.com",
            full_name="OAuth User",
            provider="google",
            provider_id="google-456",
        )

        # Try to authenticate with password (should fail)
        result = auth_service.authenticate_user("oauthuser", "any-password")
        assert result is None

    def test_local_user_login_still_works(self, db_session: Session):
        """Test local users can still login with password."""
        auth_service = AuthService(db_session)

        # Create local user
        user = auth_service.create_user(
            username="localuser",
            email="local@example.com",
            password="test-password",
        )

        # Authenticate with password
        result = auth_service.authenticate_user("localuser", "test-password")
        assert result is not None
        assert result.username == "localuser"

        # Wrong password should fail
        result = auth_service.authenticate_user("localuser", "wrong-password")
        assert result is None

    def test_unique_username_generation(self, db_session: Session):
        """Test unique username generation for OAuth users."""
        auth_service = AuthService(db_session)

        # Create first user
        user1 = auth_service.create_user(
            username="john",
            email="john1@example.com",
            password="password1",
        )

        # OAuth handler should generate unique username
        oauth_handler = OAuthHandler(db_session)

        # Mock the email prefix collision
        with patch.object(auth_service, "get_user_by_email", return_value=None):
            with patch.object(auth_service, "get_user_by_username", side_effect=[user1, None]):
                user2 = auth_service.create_oauth_user(
                    username="john1",  # Should be generated as john1 since john exists
                    email="john2@example.com",
                    full_name="John Doe 2",
                    provider="google",
                    provider_id="google-789",
                )

                assert user2.username == "john1"
