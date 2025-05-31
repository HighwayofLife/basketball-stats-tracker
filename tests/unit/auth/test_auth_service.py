"""Unit tests for the authentication service."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.auth.models import User, UserRole


class TestAuthService:
    """Test cases for AuthService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return MagicMock(spec=Session)

    @pytest.fixture
    def auth_service(self, mock_db):
        """Create an AuthService instance with mock database."""
        return AuthService(mock_db)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$hashed_password",
            full_name="Test User",
            role=UserRole.USER,
            is_active=True,
            provider="local",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    def test_create_user_success(self, auth_service, mock_db):
        """Test successful user creation."""
        # Mock that username and email don't exist
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.auth.service.get_password_hash") as mock_hash:
            mock_hash.return_value = "hashed_password"

            user = auth_service.create_user(
                username="newuser",
                email="newuser@example.com",
                password="password123",
                full_name="New User",
                role=UserRole.USER,
            )

            # Verify password was hashed
            mock_hash.assert_called_once_with("password123")

            # Verify user was added to database
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    def test_create_user_duplicate_username(self, auth_service, mock_db, sample_user):
        """Test user creation with duplicate username."""
        # Mock that username already exists
        mock_db.query.return_value.filter.return_value.first.side_effect = [sample_user, None]

        with pytest.raises(ValueError, match="Username 'testuser' already exists"):
            auth_service.create_user(username="testuser", email="different@example.com", password="password123")

    def test_create_user_duplicate_email(self, auth_service, mock_db, sample_user):
        """Test user creation with duplicate email."""
        # Mock that email already exists
        mock_db.query.return_value.filter.return_value.first.side_effect = [None, sample_user]

        with pytest.raises(ValueError, match="Email 'test@example.com' already exists"):
            auth_service.create_user(username="differentuser", email="test@example.com", password="password123")

    def test_authenticate_user_success(self, auth_service, mock_db, sample_user):
        """Test successful user authentication."""
        # Mock user found
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        with patch("app.auth.service.verify_password") as mock_verify:
            mock_verify.return_value = True

            result = auth_service.authenticate_user("testuser", "password123")

            assert result == sample_user
            mock_verify.assert_called_once_with("password123", sample_user.hashed_password)
            mock_db.commit.assert_called_once()  # For updating last_login

    def test_authenticate_user_not_found(self, auth_service, mock_db):
        """Test authentication with non-existent user."""
        # Mock user not found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.authenticate_user("nonexistent", "password123")

        assert result is None

    def test_authenticate_user_wrong_password(self, auth_service, mock_db, sample_user):
        """Test authentication with wrong password."""
        # Mock user found but wrong password
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        with patch("app.auth.service.verify_password") as mock_verify:
            mock_verify.return_value = False

            result = auth_service.authenticate_user("testuser", "wrongpassword")

            assert result is None

    def test_authenticate_user_oauth_user(self, auth_service, mock_db, sample_user):
        """Test authentication of OAuth user (should fail)."""
        sample_user.provider = "google"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = auth_service.authenticate_user("testuser", "password123")

        assert result is None

    def test_authenticate_user_inactive(self, auth_service, mock_db, sample_user):
        """Test authentication of inactive user."""
        sample_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        with patch("app.auth.service.verify_password") as mock_verify:
            mock_verify.return_value = True

            result = auth_service.authenticate_user("testuser", "password123")

            assert result is None

    def test_get_user_by_id(self, auth_service, mock_db, sample_user):
        """Test getting user by ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = auth_service.get_user_by_id(1)

        assert result == sample_user

    def test_get_user_by_username(self, auth_service, mock_db, sample_user):
        """Test getting user by username."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = auth_service.get_user_by_username("testuser")

        assert result == sample_user

    def test_get_user_by_email(self, auth_service, mock_db, sample_user):
        """Test getting user by email."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = auth_service.get_user_by_email("test@example.com")

        assert result == sample_user

    def test_update_user_password_success(self, auth_service, mock_db, sample_user):
        """Test successful password update."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        with patch("app.auth.service.get_password_hash") as mock_hash:
            mock_hash.return_value = "new_hashed_password"

            result = auth_service.update_user_password(1, "newpassword123")

            assert result is True
            mock_hash.assert_called_once_with("newpassword123")
            assert sample_user.hashed_password == "new_hashed_password"
            mock_db.commit.assert_called_once()

    def test_update_user_password_user_not_found(self, auth_service, mock_db):
        """Test password update for non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.update_user_password(999, "newpassword123")

        assert result is False

    def test_update_user_role_success(self, auth_service, mock_db, sample_user):
        """Test successful role update."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = auth_service.update_user_role(1, UserRole.ADMIN)

        assert result is True
        assert sample_user.role == UserRole.ADMIN
        mock_db.commit.assert_called_once()

    def test_update_user_role_user_not_found(self, auth_service, mock_db):
        """Test role update for non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.update_user_role(999, UserRole.ADMIN)

        assert result is False

    def test_deactivate_user_success(self, auth_service, mock_db, sample_user):
        """Test successful user deactivation."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        result = auth_service.deactivate_user(1)

        assert result is True
        assert sample_user.is_active is False
        mock_db.commit.assert_called_once()

    def test_deactivate_user_not_found(self, auth_service, mock_db):
        """Test deactivation of non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = auth_service.deactivate_user(999)

        assert result is False

    def test_create_tokens(self, auth_service, sample_user):
        """Test token creation."""
        with (
            patch("app.auth.service.create_access_token") as mock_access,
            patch("app.auth.service.create_refresh_token") as mock_refresh,
        ):
            mock_access.return_value = "access_token"
            mock_refresh.return_value = "refresh_token"

            tokens = auth_service.create_tokens(sample_user)

            assert tokens == {"access_token": "access_token", "refresh_token": "refresh_token", "token_type": "bearer"}

            # Verify access token was created with correct data
            mock_access.assert_called_once()
            access_call_args = mock_access.call_args[0][0]
            assert access_call_args["sub"] == "1"
            assert access_call_args["username"] == "testuser"
            assert access_call_args["role"] == "user"

    def test_create_oauth_user(self, auth_service, mock_db):
        """Test OAuth user creation."""
        user = auth_service.create_oauth_user(
            username="googleuser",
            email="google@example.com",
            full_name="Google User",
            provider="google",
            provider_id="123456789",
            role=UserRole.USER,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_last_login(self, auth_service, mock_db, sample_user):
        """Test updating user's last login timestamp."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        auth_service.update_last_login(1)

        assert sample_user.last_login is not None
        mock_db.commit.assert_called_once()

    def test_update_last_login_user_not_found(self, auth_service, mock_db):
        """Test updating last login for non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Should not raise an exception
        auth_service.update_last_login(999)

        mock_db.commit.assert_not_called()
