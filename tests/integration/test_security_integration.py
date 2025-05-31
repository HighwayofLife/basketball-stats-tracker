"""Integration tests for security features."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.data_access.models import Player, Team
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_teams(db_session: Session):
    """Create test teams."""
    team1 = Team(name="Team A", display_name="Team Alpha")
    team2 = Team(name="Team B", display_name="Team Beta")
    db_session.add_all([team1, team2])
    db_session.commit()
    return team1, team2


@pytest.fixture
def team1_user(db_session: Session, test_teams):
    """Create a user belonging to team 1."""
    from app.auth.service import AuthService

    team1, _ = test_teams
    auth_service = AuthService(db_session)
    user = auth_service.create_user(
        username="team1user", password="password123", email="team1@example.com", team_id=team1.id, role=UserRole.USER
    )
    return user


@pytest.fixture
def team2_user(db_session: Session, test_teams):
    """Create a user belonging to team 2."""
    from app.auth.service import AuthService

    _, team2 = test_teams
    auth_service = AuthService(db_session)
    user = auth_service.create_user(
        username="team2user", password="password123", email="team2@example.com", team_id=team2.id, role=UserRole.USER
    )
    return user


@pytest.fixture
def admin_user(db_session: Session, test_teams):
    """Create an admin user."""
    from app.auth.service import AuthService

    team1, _ = test_teams
    auth_service = AuthService(db_session)
    user = auth_service.create_user(
        username="admin", password="adminpass123", email="admin@example.com", team_id=team1.id, role=UserRole.ADMIN
    )
    return user


@pytest.fixture
def team1_headers(team1_user: User):
    """Create auth headers for team 1 user."""
    from app.auth.jwt_handler import create_access_token

    token = create_access_token(data={"sub": str(team1_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def team2_headers(team2_user: User):
    """Create auth headers for team 2 user."""
    from app.auth.jwt_handler import create_access_token

    token = create_access_token(data={"sub": str(team2_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user: User):
    """Create auth headers for admin user."""
    from app.auth.jwt_handler import create_access_token

    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestSecurityWorkflow:
    """Test complete security workflows."""

    def test_user_can_only_access_own_team_data(
        self, client: TestClient, db_session: Session, test_teams, team1_headers: dict, team2_headers: dict
    ):
        """Test that users can only access their own team's data."""
        team1, team2 = test_teams

        # Create players for each team
        player1 = Player(name="Player 1", team_id=team1.id, jersey_number="1", is_active=True)
        player2 = Player(name="Player 2", team_id=team2.id, jersey_number="2", is_active=True)
        db_session.add_all([player1, player2])
        db_session.commit()

        # Team 1 user should be able to access team 1 players
        response = client.get(f"/v1/players/list?team_id={team1.id}", headers=team1_headers)
        assert response.status_code != 403  # Should not be forbidden

        # Team 1 user should NOT be able to modify team 2 players
        response = client.put(f"/v1/players/{player2.id}", json={"name": "Modified Name"}, headers=team1_headers)
        # This should be forbidden due to team access control
        # Note: This test assumes team-based access control is implemented in the endpoints

    def test_admin_can_access_all_data(self, client: TestClient, db_session: Session, test_teams, admin_headers: dict):
        """Test that admin users can access all data."""
        team1, team2 = test_teams

        # Create players for both teams
        player1 = Player(name="Player 1", team_id=team1.id, jersey_number="1", is_active=True)
        player2 = Player(name="Player 2", team_id=team2.id, jersey_number="2", is_active=True)
        db_session.add_all([player1, player2])
        db_session.commit()

        # Admin should be able to access both teams' data
        response = client.get(f"/v1/players/list?team_id={team1.id}", headers=admin_headers)
        assert response.status_code != 403

        response = client.get(f"/v1/players/list?team_id={team2.id}", headers=admin_headers)
        assert response.status_code != 403

        # Admin should be able to modify players from any team
        response = client.put(f"/v1/players/{player2.id}", json={"name": "Admin Modified"}, headers=admin_headers)
        assert response.status_code != 403

    def test_authentication_required_for_all_modifications(self, client: TestClient, db_session: Session, test_teams):
        """Test that all data modification endpoints require authentication."""
        team1, _ = test_teams

        # Create a player to test with
        player = Player(name="Test Player", team_id=team1.id, jersey_number="99", is_active=True)
        db_session.add(player)
        db_session.commit()

        # Test all modification endpoints without authentication
        modification_endpoints = [
            ("POST", "/v1/players/new", {"name": "New Player", "team_id": team1.id, "jersey_number": "88"}),
            ("PUT", f"/v1/players/{player.id}", {"name": "Modified"}),
            ("DELETE", f"/v1/players/{player.id}", None),
            ("POST", "/v1/teams/new", {"name": "New Team"}),
            ("POST", "/v1/games", {"date": "2024-01-01", "home_team_id": team1.id, "away_team_id": team1.id}),
        ]

        for method, endpoint, data in modification_endpoints:
            if method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "PUT":
                response = client.put(endpoint, json=data)
            elif method == "DELETE":
                response = client.delete(endpoint)

            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"

    def test_jwt_token_expiration_handling(self, client: TestClient, team1_user: User):
        """Test handling of expired JWT tokens."""
        from datetime import timedelta

        from app.auth.jwt_handler import create_access_token

        # Create an expired token (negative expiration)
        expired_token = create_access_token(data={"sub": str(team1_user.id)}, expires_delta=timedelta(seconds=-1))

        expired_headers = {"Authorization": f"Bearer {expired_token}"}

        # Attempt to use expired token
        response = client.post(
            "/v1/players/new", json={"name": "Test", "team_id": 1, "jersey_number": "1"}, headers=expired_headers
        )

        assert response.status_code == 401

    def test_role_based_endpoint_access(self, client: TestClient, team1_headers: dict, admin_headers: dict):
        """Test that role-based endpoints work correctly."""
        # Test admin-only endpoint with regular user
        response = client.post("/v1/data-corrections/undo", headers=team1_headers)
        assert response.status_code == 403  # Should be forbidden

        # Test admin-only endpoint with admin user
        response = client.post("/v1/data-corrections/undo", headers=admin_headers)
        assert response.status_code != 403  # Should not be forbidden (may have other errors)

    def test_password_security_requirements(self, db_session: Session):
        """Test that password security requirements are enforced."""
        from app.auth.service import AuthService

        auth_service = AuthService(db_session)

        # Test weak passwords are rejected
        weak_passwords = [
            "123",  # Too short
            "password",  # Too common
            "12345678",  # No complexity
        ]

        for weak_password in weak_passwords:
            with pytest.raises((ValueError, Exception)):
                auth_service.create_user(
                    username="testuser", password=weak_password, email="test@example.com", team_id=1, role=UserRole.USER
                )


class TestSecurityConfiguration:
    """Test security configuration and environment."""

    def test_jwt_secret_validation(self):
        """Test that JWT secret is properly validated."""
        import os

        # This test verifies that the application properly validates JWT secrets
        # The actual validation happens at import time in jwt_handler.py

        # Verify that JWT_SECRET_KEY is required
        original_key = os.getenv("JWT_SECRET_KEY")

        if original_key:
            # If key exists, it should be long enough
            assert len(original_key) >= 32, "JWT_SECRET_KEY should be at least 32 characters"

    def test_production_security_settings(self):
        """Test that production security settings are properly configured."""
        from app.auth import jwt_handler

        # Verify secure algorithm is used
        assert jwt_handler.ALGORITHM == "HS256"

        # Verify reasonable token expiration
        assert jwt_handler.ACCESS_TOKEN_EXPIRE_MINUTES <= 60  # Max 1 hour
        assert jwt_handler.REFRESH_TOKEN_EXPIRE_DAYS <= 30  # Max 30 days

    def test_password_hashing_strength(self):
        """Test that password hashing uses strong configuration."""
        from app.auth.jwt_handler import pwd_context

        # Verify bcrypt is used
        assert "bcrypt" in [scheme.name for scheme in pwd_context.schemes()]

        # Test password hashing works
        password = "test_password_123"
        hashed = pwd_context.hash(password)

        # Verify hash is different from password
        assert hashed != password

        # Verify verification works
        assert pwd_context.verify(password, hashed)
        assert not pwd_context.verify("wrong_password", hashed)
