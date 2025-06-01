"""Integration tests for OAuth functionality."""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import User
from app.dependencies import get_db
from app.web_ui.api import app


class TestOAuthIntegration:
    """Test OAuth integration end-to-end."""

    def test_oauth_login_redirect(self):
        """Test OAuth login redirects to Google."""
        # Mock OAuth being enabled
        with patch("app.auth.oauth.OAUTH_ENABLED", True):
            with patch("app.auth.oauth.oauth") as mock_oauth:
                # Mock the authorize_redirect method
                mock_google = Mock()
                mock_google.authorize_redirect = Mock(return_value="https://accounts.google.com/oauth/authorize?...")
                mock_oauth.google = mock_google

                client = TestClient(app)
                response = client.get("/auth/google/login", follow_redirects=False)

                assert response.status_code == 307  # Temporary redirect
                assert "accounts.google.com" in str(mock_google.authorize_redirect.call_args)

    def test_oauth_disabled_returns_error(self):
        """Test OAuth endpoints return error when disabled."""
        with patch("app.auth.oauth.OAUTH_ENABLED", False):
            client = TestClient(app)
            response = client.get("/auth/google/login")

            assert response.status_code == 503
            assert response.json()["detail"] == "OAuth is not configured"

    @pytest.mark.asyncio
    async def test_oauth_callback_creates_new_user(self, db_session: Session):
        """Test OAuth callback creates new user."""
        with patch("app.auth.oauth.OAUTH_ENABLED", True):
            with patch("app.auth.oauth.oauth") as mock_oauth:
                # Mock Google OAuth response
                mock_google = Mock()
                mock_token = {
                    "userinfo": {
                        "email": "newuser@example.com",
                        "name": "New User",
                        "sub": "google-123456",
                    }
                }

                # Make authorize_access_token async
                mock_google.authorize_access_token = AsyncMock(return_value=mock_token)
                mock_oauth.google = mock_google

                # Override the database dependency
                def override_get_db():
                    yield db_session

                app.dependency_overrides[get_db] = override_get_db

                try:
                    client = TestClient(app)
                    response = client.get("/auth/google/callback?code=test-code", follow_redirects=False)

                    # Should redirect to home page
                    assert response.status_code == 302
                    assert response.headers["location"] == "/"

                    # Check user was created
                    user = db_session.query(User).filter_by(email="newuser@example.com").first()
                    assert user is not None
                    assert user.username == "newuser"
                    assert user.full_name == "New User"
                    assert user.provider == "google"
                    assert user.provider_id == "google-123456"
                    assert user.hashed_password is None

                    # Check cookie was set
                    assert "access_token" in response.cookies

                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_oauth_callback_existing_user(self, db_session: Session):
        """Test OAuth callback logs in existing user."""
        # Create existing user
        existing_user = User(
            username="existinguser",
            email="existing@example.com",
            full_name="Existing User",
            provider="google",
            provider_id="google-existing",
        )
        db_session.add(existing_user)
        db_session.commit()

        with patch("app.auth.oauth.OAUTH_ENABLED", True):
            with patch("app.auth.oauth.oauth") as mock_oauth:
                # Mock Google OAuth response
                mock_google = Mock()
                mock_token = {
                    "userinfo": {
                        "email": "existing@example.com",
                        "name": "Updated Name",
                        "sub": "google-existing",
                    }
                }

                mock_google.authorize_access_token = AsyncMock(return_value=mock_token)
                mock_oauth.google = mock_google

                # Override the database dependency
                def override_get_db():
                    yield db_session

                app.dependency_overrides[get_db] = override_get_db

                try:
                    client = TestClient(app)
                    response = client.get("/auth/google/callback?code=test-code", follow_redirects=False)

                    # Should redirect to home page
                    assert response.status_code == 302
                    assert response.headers["location"] == "/"

                    # Check user was updated
                    db_session.refresh(existing_user)
                    assert existing_user.full_name == "Updated Name"
                    assert existing_user.last_login is not None

                finally:
                    app.dependency_overrides.clear()

    def test_oauth_status_endpoint(self):
        """Test OAuth status endpoint."""
        # Test when enabled
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "test-id", "GOOGLE_CLIENT_SECRET": "test-secret"}):
            with patch("app.auth.oauth.OAUTH_ENABLED", True):
                client = TestClient(app)
                response = client.get("/auth/oauth/status")

                assert response.status_code == 200
                assert response.json()["oauth_enabled"] is True

        # Test when disabled
        with patch("app.auth.oauth.OAUTH_ENABLED", False):
            client = TestClient(app)
            response = client.get("/auth/oauth/status")

            assert response.status_code == 200
            assert response.json()["oauth_enabled"] is False
