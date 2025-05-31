"""Unit tests for authentication dependencies."""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status

from app.auth.dependencies import get_current_active_user, get_current_user, require_admin
from app.auth.models import User, UserRole


class TestAuthDependencies:
    """Test cases for authentication dependencies."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.role = UserRole.USER
        user.is_active = True
        return user

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user for testing."""
        user = Mock(spec=User)
        user.id = 2
        user.username = "admin"
        user.email = "admin@example.com"
        user.role = UserRole.ADMIN
        user.is_active = True
        return user

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock()

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_user, mock_db):
        """Test successful user authentication."""
        with (
            patch("app.auth.dependencies.verify_token") as mock_verify,
            patch("app.auth.dependencies.AuthService") as mock_service_class,
        ):
            # Mock token verification
            mock_verify.return_value = {"sub": "1"}

            # Mock auth service
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_by_id.return_value = mock_user

            result = await get_current_user("valid_token", mock_db)

            assert result == mock_user
            mock_verify.assert_called_once_with("valid_token")
            mock_service.get_user_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, mock_db):
        """Test user authentication with invalid token."""
        with patch("app.auth.dependencies.verify_token") as mock_verify:
            mock_verify.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("invalid_token", mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_token_missing_sub(self, mock_db):
        """Test user authentication when token is missing 'sub' field."""
        with patch("app.auth.dependencies.verify_token") as mock_verify:
            mock_verify.return_value = {"username": "testuser"}  # Missing 'sub'

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("token_without_sub", mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, mock_db):
        """Test user authentication when user is not found in database."""
        with (
            patch("app.auth.dependencies.verify_token") as mock_verify,
            patch("app.auth.dependencies.AuthService") as mock_service_class,
        ):
            mock_verify.return_value = {"sub": "999"}

            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_by_id.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("valid_token", mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, mock_db):
        """Test user authentication with inactive user."""
        inactive_user = Mock(spec=User)
        inactive_user.is_active = False

        with (
            patch("app.auth.dependencies.verify_token") as mock_verify,
            patch("app.auth.dependencies.AuthService") as mock_service_class,
        ):
            mock_verify.return_value = {"sub": "1"}

            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_by_id.return_value = inactive_user

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user("valid_token", mock_db)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Inactive user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self, mock_user):
        """Test successful active user check."""
        result = await get_current_active_user(mock_user)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self):
        """Test active user check with inactive user."""
        inactive_user = Mock(spec=User)
        inactive_user.is_active = False

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(inactive_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Inactive user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_admin_success(self, mock_admin_user):
        """Test successful admin authorization."""
        result = await require_admin(mock_admin_user)
        assert result == mock_admin_user

    @pytest.mark.asyncio
    async def test_require_admin_non_admin_user(self, mock_user):
        """Test admin authorization with non-admin user."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_admin_viewer_user(self):
        """Test admin authorization with viewer user."""
        viewer_user = Mock(spec=User)
        viewer_user.role = UserRole.VIEWER
        viewer_user.is_active = True

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(viewer_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in exc_info.value.detail
