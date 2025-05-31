"""Unit tests for authentication router endpoints."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException, status

from app.auth.models import User, UserRole
from app.web_ui.routers.auth import router


class TestAuthRouter:
    """Test cases for authentication router endpoints."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.full_name = "Test User"
        user.role = UserRole.USER
        user.is_active = True
        user.provider = "local"
        return user

    @pytest.fixture
    def mock_admin_user(self):
        """Create a mock admin user for testing."""
        user = Mock(spec=User)
        user.id = 2
        user.username = "admin"
        user.email = "admin@example.com"
        user.full_name = "Admin User"
        user.role = UserRole.ADMIN
        user.is_active = True
        user.provider = "local"
        return user

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/auth")
        return TestClient(app)

    def test_register_success(self, client):
        """Test successful user registration."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "newuser"
            mock_user.email = "new@example.com"
            mock_user.role = UserRole.USER
            mock_user.is_active = True
            mock_service.create_user.return_value = mock_user
            
            response = client.post("/auth/register", json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
                "full_name": "New User"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "newuser"
            assert data["email"] == "new@example.com"

    def test_register_duplicate_user(self, client):
        """Test registration with duplicate username."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.create_user.side_effect = ValueError("Username already exists")
            
            response = client.post("/auth/register", json={
                "username": "existinguser",
                "email": "new@example.com",
                "password": "password123"
            })
            
            assert response.status_code == 400
            assert "Username already exists" in response.json()["detail"]

    def test_login_success(self, client, mock_user):
        """Test successful login."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.authenticate_user.return_value = mock_user
            mock_service.create_tokens.return_value = {
                "access_token": "access_token",
                "refresh_token": "refresh_token",
                "token_type": "bearer"
            }
            
            response = client.post("/auth/token", data={
                "username": "testuser",
                "password": "password123"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "access_token"
            assert data["refresh_token"] == "refresh_token"
            assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.authenticate_user.return_value = None
            
            response = client.post("/auth/token", data={
                "username": "testuser",
                "password": "wrongpassword"
            })
            
            assert response.status_code == 401
            assert "Incorrect username or password" in response.json()["detail"]

    def test_refresh_token_success(self, client, mock_user):
        """Test successful token refresh."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.verify_token') as mock_verify:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_by_id.return_value = mock_user
            mock_service.create_tokens.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "token_type": "bearer"
            }
            
            mock_verify.return_value = {"sub": "1"}
            
            response = client.post("/auth/refresh", json={
                "refresh_token": "valid_refresh_token"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_access_token"

    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token."""
        with patch('app.web_ui.routers.auth.verify_token') as mock_verify:
            mock_verify.return_value = None
            
            response = client.post("/refresh", json={
                "refresh_token": "invalid_refresh_token"
            })
            
            assert response.status_code == 401
            assert "Invalid refresh token" in response.json()["detail"]

    def test_change_password_success(self, client, mock_user):
        """Test successful password change."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.get_current_user') as mock_get_user:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.authenticate_user.return_value = mock_user
            mock_service.update_user_password.return_value = True
            mock_get_user.return_value = mock_user
            
            response = client.post("/change-password", json={
                "current_password": "oldpassword",
                "new_password": "newpassword123"
            })
            
            assert response.status_code == 200
            assert "Password updated successfully" in response.json()["message"]

    def test_change_password_wrong_current(self, client, mock_user):
        """Test password change with wrong current password."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.get_current_user') as mock_get_user:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.authenticate_user.return_value = None  # Wrong password
            mock_get_user.return_value = mock_user
            
            response = client.post("/change-password", json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123"
            })
            
            assert response.status_code == 400
            assert "Current password is incorrect" in response.json()["detail"]

    def test_get_current_user_profile(self, client, mock_user):
        """Test getting current user profile."""
        with patch('app.web_ui.routers.auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = mock_user
            
            response = client.get("/me")
            
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"

    def test_update_profile_success(self, client, mock_user):
        """Test successful profile update."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.get_current_user') as mock_get_user:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_by_email.return_value = None  # Email not taken
            mock_get_user.return_value = mock_user
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            response = client.put("/profile", json={
                "email": "newemail@example.com",
                "full_name": "New Full Name"
            })
            
            assert response.status_code == 200
            assert mock_user.email == "newemail@example.com"
            assert mock_user.full_name == "New Full Name"
            mock_db.commit.assert_called_once()

    def test_update_profile_email_taken(self, client, mock_user):
        """Test profile update with email already taken."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.get_current_user') as mock_get_user:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock another user with the same email
            other_user = Mock()
            other_user.id = 999
            mock_service.get_user_by_email.return_value = other_user
            mock_get_user.return_value = mock_user
            
            response = client.put("/profile", json={
                "email": "taken@example.com",
                "full_name": "New Full Name"
            })
            
            assert response.status_code == 400
            assert "Email address is already in use" in response.json()["detail"]

    def test_get_all_users_admin(self, client, mock_admin_user):
        """Test getting all users as admin."""
        with patch('app.web_ui.routers.auth.require_admin') as mock_require_admin, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db:
            
            mock_require_admin.return_value = mock_admin_user
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            mock_users = [mock_admin_user]
            mock_db.query.return_value.all.return_value = mock_users
            
            response = client.get("/users")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["username"] == "admin"

    def test_update_user_role_admin(self, client, mock_admin_user):
        """Test updating user role as admin."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.require_admin') as mock_require_admin:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.update_user_role.return_value = True
            mock_require_admin.return_value = mock_admin_user
            
            response = client.put("/users/1/role", json={
                "role": "admin"
            })
            
            assert response.status_code == 200
            assert "User role updated successfully" in response.json()["message"]

    def test_update_user_role_invalid_role(self, client, mock_admin_user):
        """Test updating user role with invalid role."""
        with patch('app.web_ui.routers.auth.require_admin') as mock_require_admin:
            mock_require_admin.return_value = mock_admin_user
            
            response = client.put("/users/1/role", json={
                "role": "invalid_role"
            })
            
            assert response.status_code == 400
            assert "Invalid role" in response.json()["detail"]

    def test_deactivate_user_admin(self, client, mock_admin_user):
        """Test deactivating user as admin."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.require_admin') as mock_require_admin:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.deactivate_user.return_value = True
            mock_require_admin.return_value = mock_admin_user
            
            response = client.post("/users/1/deactivate")
            
            assert response.status_code == 200
            assert "User deactivated successfully" in response.json()["message"]

    def test_activate_user_admin(self, client, mock_admin_user):
        """Test activating user as admin."""
        with patch('app.web_ui.routers.auth.AuthService') as mock_service_class, \
             patch('app.web_ui.routers.auth.get_db') as mock_get_db, \
             patch('app.web_ui.routers.auth.require_admin') as mock_require_admin:
            
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_user = Mock()
            mock_user.is_active = False
            mock_service.get_user_by_id.return_value = mock_user
            mock_require_admin.return_value = mock_admin_user
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            response = client.post("/users/1/activate")
            
            assert response.status_code == 200
            assert "User activated successfully" in response.json()["message"]
            assert mock_user.is_active is True
            mock_db.commit.assert_called_once()

    def test_oauth_status(self, client):
        """Test OAuth status endpoint."""
        with patch('app.web_ui.routers.auth.OAUTH_ENABLED', True):
            response = client.get("/oauth/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["oauth_enabled"] is True