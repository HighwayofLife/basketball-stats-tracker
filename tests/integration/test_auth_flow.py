"""Integration tests for authentication flow and authenticated endpoints."""

import os

# Set JWT_SECRET_KEY for all tests in this module
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"
os.environ["ADMIN_PASSWORD"] = "TestAdminPassword123!"

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.auth.jwt_handler import get_password_hash
from app.auth.models import User, UserRole
from app.data_access.models import Season, Team
from app.web_ui.api import app


@pytest.fixture
def test_client(test_db_file_engine, monkeypatch):
    """Create a test client with proper database dependency override."""
    from contextlib import contextmanager

    from sqlalchemy.orm import Session

    from app.dependencies import get_db

    # Create a context manager that yields a new session connected to the same db
    @contextmanager
    def test_get_db_session():
        # Create a new session from the same engine
        new_session = Session(bind=test_db_file_engine)
        try:
            yield new_session
        finally:
            new_session.close()

    # Monkey-patch the get_db_session function in all the modules that import it
    import app.data_access.db_session as db_session_module
    import app.web_ui.routers.admin as admin_module
    import app.web_ui.routers.games as games_module

    monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)
    monkeypatch.setattr(games_module, "get_db_session", test_get_db_session)
    monkeypatch.setattr(admin_module, "get_db_session", test_get_db_session)

    # Also override the dependency for endpoints that use proper DI
    def override_get_db():
        new_session = Session(bind=test_db_file_engine)
        try:
            yield new_session
        finally:
            new_session.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()


@pytest.fixture
def create_admin_user(test_db_file_engine):
    """Create an admin user in the database."""
    from sqlalchemy.orm import Session

    # Create admin user directly in database
    with Session(bind=test_db_file_engine) as session:
        # Check if user already exists
        existing_user = session.query(User).filter(User.username == "admin").first()
        if not existing_user:
            admin_user = User(
                username="admin",
                email="admin@test.com",
                hashed_password=get_password_hash("TestAdminPassword123!"),
                role=UserRole.ADMIN,
                is_active=True,
                provider="local",  # Required for password authentication
            )
            session.add(admin_user)
            session.commit()


@pytest.fixture
def auth_headers(test_client, test_db_file_engine, create_admin_user):
    """Create an authenticated user and return auth headers."""
    # Login to get token
    response = test_client.post(
        "/auth/token",
        data={"username": "admin", "password": "TestAdminPassword123!"},
    )
    assert response.status_code == 200
    token_data = response.json()

    return {"Authorization": f"Bearer {token_data['access_token']}"}


@pytest.fixture
def sample_teams(test_db_file_engine):
    """Create sample teams for testing."""
    from sqlalchemy.orm import Session

    with Session(bind=test_db_file_engine) as session:
        teams = [
            Team(id=1, name="Red", display_name="Red Dragons"),
            Team(id=2, name="Blue", display_name="Blue Knights"),
            Team(id=3, name="Green", display_name="Green Machine"),
            Team(id=4, name="Black", display_name="Black Panthers"),
        ]
        session.add_all(teams)
        session.commit()


@pytest.fixture
def sample_season(test_db_file_engine):
    """Create a sample active season for testing."""
    from sqlalchemy.orm import Session

    with Session(bind=test_db_file_engine) as session:
        # Check if season already exists
        existing_season = session.query(Season).filter(Season.name == "Spring 2025").first()
        if not existing_season:
            season = Season(
                id=1,
                name="Spring 2025",
                code="2025-spring",
                start_date=date(2025, 5, 1),
                end_date=date(2025, 7, 31),
                is_active=True,
            )
            session.add(season)
            session.commit()


class TestAuthenticationFlow:
    """Test authentication flow matching manual curl tests."""

    def test_login_with_invalid_credentials(self, test_client):
        """Test login with invalid credentials returns 401."""
        response = test_client.post(
            "/auth/token",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"

    def test_login_with_valid_credentials(self, test_client, test_db_file_engine, create_admin_user):
        """Test login with valid credentials returns tokens."""
        response = test_client.post(
            "/auth/token",
            data={"username": "admin", "password": "TestAdminPassword123!"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_access_protected_endpoint_without_auth(self, test_client):
        """Test accessing protected endpoint without authentication."""
        response = test_client.get("/v1/seasons")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_access_protected_endpoint_with_auth(self, test_client, auth_headers, sample_season):
        """Test accessing protected endpoint with valid authentication."""
        response = test_client.get("/v1/seasons", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "seasons" in data
        # At least one season should exist
        assert len(data["seasons"]) >= 1
        # Our test season should be in the list
        spring_2025 = next((s for s in data["seasons"] if s["name"] == "Spring 2025"), None)
        assert spring_2025 is not None
        assert spring_2025["is_active"] is True


class TestScheduledGameCreation:
    """Test scheduled game creation matching manual curl tests."""

    def test_create_scheduled_game_without_auth(self, test_client, sample_teams, sample_season):
        """Test creating scheduled game without authentication fails."""
        game_data = {
            "scheduled_date": "2025-06-10",
            "home_team_id": 1,
            "away_team_id": 2,
            "season_id": 1,
            "scheduled_time": "19:00",
            "location": "Main Gym",
            "notes": "Test game",
        }

        response = test_client.post("/v1/games/scheduled", json=game_data)
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_create_scheduled_game_with_auth(self, test_client, auth_headers, sample_teams, sample_season):
        """Test creating scheduled game with valid authentication."""
        game_data = {
            "scheduled_date": "2025-06-10",
            "home_team_id": 1,
            "away_team_id": 2,
            "season_id": 1,
            "scheduled_time": "19:00",
            "location": "Main Gym",
            "notes": "Test game",
        }

        response = test_client.post("/v1/games/scheduled", headers=auth_headers, json=game_data)
        assert response.status_code == 200

        data = response.json()
        assert data["home_team_id"] == 1
        assert data["home_team_name"] == "Red Dragons"
        assert data["away_team_id"] == 2
        assert data["away_team_name"] == "Blue Knights"
        assert data["scheduled_date"] == "2025-06-10"
        assert data["scheduled_time"] == "19:00"
        assert data["status"] == "scheduled"
        assert data["location"] == "Main Gym"
        assert data["notes"] == "Test game"

    def test_create_duplicate_scheduled_game(self, test_client, auth_headers, sample_teams, sample_season):
        """Test creating duplicate scheduled game fails."""
        game_data = {
            "scheduled_date": "2025-06-10",
            "home_team_id": 1,
            "away_team_id": 2,
            "season_id": 1,
            "scheduled_time": "19:00",
        }

        # Create first game
        response = test_client.post("/v1/games/scheduled", headers=auth_headers, json=game_data)
        assert response.status_code == 200

        # Try to create duplicate - should return 400 Bad Request
        response = test_client.post("/v1/games/scheduled", headers=auth_headers, json=game_data)
        assert response.status_code == 400
        assert "already exists between these teams" in response.json()["detail"]

    def test_create_scheduled_game_same_teams(self, test_client, auth_headers, sample_teams, sample_season):
        """Test creating scheduled game with same team as home and away fails."""
        game_data = {
            "scheduled_date": "2025-06-10",
            "home_team_id": 1,
            "away_team_id": 1,  # Same as home team
            "season_id": 1,
            "scheduled_time": "19:00",
        }

        response = test_client.post("/v1/games/scheduled", headers=auth_headers, json=game_data)
        assert response.status_code == 400
        assert "cannot be the same" in response.json()["detail"]


class TestPublicEndpoints:
    """Test public endpoints that don't require authentication."""

    def test_teams_endpoint_is_public(self, test_client, sample_teams):
        """Test that teams endpoint works without authentication."""
        response = test_client.get("/v1/teams")
        assert response.status_code == 200

        teams = response.json()
        assert len(teams) == 4
        assert any(team["name"] == "Red" and team["display_name"] == "Red Dragons" for team in teams)
        assert any(team["name"] == "Blue" and team["display_name"] == "Blue Knights" for team in teams)

    def test_health_endpoint_is_public(self, test_client):
        """Test that health endpoint works without authentication."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
