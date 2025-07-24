"""Integration tests for scheduled games API endpoints."""

import os
from datetime import date, time

# Set JWT_SECRET_KEY for all tests in this module
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"

import pytest
from fastapi.testclient import TestClient

from app.data_access.models import ScheduledGame, ScheduledGameStatus, Team
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
    import app.web_ui.routers.games as games_module

    monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)
    monkeypatch.setattr(games_module, "get_db_session", test_get_db_session)

    # Also override the dependency for endpoints that use proper DI
    def override_get_db():
        new_session = Session(bind=test_db_file_engine)
        try:
            yield new_session
        finally:
            new_session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Override authentication dependencies for testing
    from app.auth.dependencies import get_current_user, require_admin
    from app.auth.models import User, UserRole

    def mock_current_user():
        """Mock current user for testing."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            role=UserRole.ADMIN,
            is_active=True,
            provider="local",
        )
        return user

    def mock_admin_user():
        """Mock admin user for testing."""
        return mock_current_user()

    # Set up auth mocks
    app.dependency_overrides[get_current_user] = mock_current_user
    app.dependency_overrides[require_admin] = mock_admin_user

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


class TestScheduledGamesAPI:
    """Test scheduled games API endpoints."""

    def test_create_scheduled_game(self, test_client, test_db_file_session):
        """Test creating a scheduled game via API."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams first
        home_team_name = f"HomeTeam_{unique_suffix}"
        away_team_name = f"AwayTeam_{unique_suffix}"
        home_team = Team(name=home_team_name)
        away_team = Team(name=away_team_name)
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        # Create scheduled game
        scheduled_game_data = {
            "scheduled_date": "2025-06-15",
            "scheduled_time": "19:30",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "location": "Test Arena",
            "notes": "Test game",
        }

        response = test_client.post("/v1/games/scheduled", json=scheduled_game_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["scheduled_date"] == "2025-06-15"
        assert data["scheduled_time"] == "19:30"
        assert data["home_team_id"] == home_team.id
        assert data["away_team_id"] == away_team.id
        assert data["location"] == "Test Arena"
        assert data["notes"] == "Test game"
        assert data["status"] == "scheduled"

    def test_create_scheduled_game_validation(self, test_client):
        """Test validation when creating scheduled game."""
        # Missing required fields
        response = test_client.post("/v1/games/scheduled", json={})
        assert response.status_code == 422

        # Invalid team IDs (team validation happens in service layer)
        response = test_client.post(
            "/v1/games/scheduled", json={"scheduled_date": "2025-06-15", "home_team_id": 999, "away_team_id": 998}
        )
        assert response.status_code in [400, 422, 500]

    def test_get_scheduled_games_list(self, test_client, test_db_file_session):
        """Test getting list of scheduled games."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams
        team1_name = f"Team1_{unique_suffix}"
        team2_name = f"Team2_{unique_suffix}"
        team1 = Team(name=team1_name)
        team2 = Team(name=team2_name)
        test_db_file_session.add(team1)
        test_db_file_session.add(team2)
        test_db_file_session.commit()

        # Create scheduled games
        game1 = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=team1.id,
            away_team_id=team2.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        game2 = ScheduledGame(
            scheduled_date=date(2025, 6, 20),
            home_team_id=team2.id,
            away_team_id=team1.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(game1)
        test_db_file_session.add(game2)
        test_db_file_session.commit()

        # Get list
        response = test_client.get("/v1/games/scheduled")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert any(game["id"] == game1.id for game in data)
        assert any(game["id"] == game2.id for game in data)

    def test_get_scheduled_game_detail(self, test_client, test_db_file_session):
        """Test getting a specific scheduled game."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams and game with unique names
        home_team_name = f"ScheduledHomeTeam_{unique_suffix}"
        away_team_name = f"ScheduledAwayTeam_{unique_suffix}"
        home_team = Team(name=home_team_name)
        away_team = Team(name=away_team_name)
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            scheduled_time=time(19, 30),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            location="Test Arena",
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(game)
        test_db_file_session.commit()

        # Get detail
        response = test_client.get(f"/v1/games/scheduled/{game.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == game.id
        assert data["scheduled_date"] == "2025-06-15"
        assert data["scheduled_time"] == "19:30"
        assert data["home_team_name"] == home_team_name
        assert data["away_team_name"] == away_team_name

    def test_update_scheduled_game(self, test_client, test_db_file_session):
        """Test updating a scheduled game."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams and game
        team1_name = f"Team1_{unique_suffix}"
        team2_name = f"Team2_{unique_suffix}"
        team3_name = f"Team3_{unique_suffix}"
        team1 = Team(name=team1_name)
        team2 = Team(name=team2_name)
        team3 = Team(name=team3_name)
        test_db_file_session.add_all([team1, team2, team3])
        test_db_file_session.commit()

        game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=team1.id,
            away_team_id=team2.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(game)
        test_db_file_session.commit()

        # Update game
        update_data = {
            "scheduled_date": "2025-06-20",
            "scheduled_time": "20:00",
            "home_team_id": team1.id,
            "away_team_id": team3.id,  # Changed opponent
            "location": "New Arena",
        }

        response = test_client.put(f"/v1/games/scheduled/{game.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["scheduled_date"] == "2025-06-20"
        assert data["scheduled_time"] == "20:00"
        assert data["away_team_id"] == team3.id
        assert data["location"] == "New Arena"

    def test_cancel_scheduled_game(self, test_client, test_db_file_session):
        """Test canceling a scheduled game."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams and game
        home_team_name = f"HomeTeam_{unique_suffix}"
        away_team_name = f"AwayTeam_{unique_suffix}"
        home_team = Team(name=home_team_name)
        away_team = Team(name=away_team_name)
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(game)
        test_db_file_session.commit()

        # Cancel game endpoint doesn't exist - use update with status
        response = test_client.put(
            f"/v1/games/scheduled/{game.id}", json={"status": "cancelled", "notes": "Weather conditions"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert "Weather conditions" in data["notes"]

    def test_delete_scheduled_game(self, test_client, test_db_file_session):
        """Test deleting a scheduled game."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams and game
        home_team_name = f"HomeTeam_{unique_suffix}"
        away_team_name = f"AwayTeam_{unique_suffix}"
        home_team = Team(name=home_team_name)
        away_team = Team(name=away_team_name)
        test_db_file_session.add(home_team)
        test_db_file_session.add(away_team)
        test_db_file_session.commit()

        game = ScheduledGame(
            scheduled_date=date(2025, 6, 15),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(game)
        test_db_file_session.commit()

        # Delete game
        response = test_client.delete(f"/v1/games/scheduled/{game.id}")

        # Assert
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify soft deleted
        test_db_file_session.expire_all()
        deleted_game = test_db_file_session.query(ScheduledGame).filter(ScheduledGame.id == game.id).first()
        # Game should still exist but be marked as deleted
        assert deleted_game is not None
        assert deleted_game.is_deleted is True

    def test_create_scheduled_game_without_auth(self, test_client):
        """Test that creating scheduled game requires authentication."""
        # Clear auth overrides to test actual auth
        app.dependency_overrides.clear()

        response = test_client.post(
            "/v1/games/scheduled", json={"scheduled_date": "2025-06-15", "home_team_id": 1, "away_team_id": 2}
        )

        # Should require authentication
        assert response.status_code == 401

    def test_scheduled_games_appear_in_games_list(self, test_client, test_db_file_session):
        """Test that scheduled games appear in the main games list with negative IDs."""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]

        # Create teams with unique names
        team1_name = f"ScheduledTeam1_{unique_suffix}"
        team2_name = f"ScheduledTeam2_{unique_suffix}"
        team1 = Team(name=team1_name)
        team2 = Team(name=team2_name)
        test_db_file_session.add(team1)
        test_db_file_session.add(team2)
        test_db_file_session.commit()

        # Create a scheduled game directly in database
        scheduled_game = ScheduledGame(
            scheduled_date=date(2025, 12, 25),
            scheduled_time=time(15, 0),
            home_team_id=team1.id,
            away_team_id=team2.id,
            location="Test Arena",
            status=ScheduledGameStatus.SCHEDULED,
        )
        test_db_file_session.add(scheduled_game)
        test_db_file_session.commit()

        # Get the games list
        response = test_client.get("/v1/games")
        assert response.status_code == 200
        games = response.json()

        # Find the scheduled game in the list (should have negative ID)
        scheduled_game_in_list = next((g for g in games if g["id"] == -scheduled_game.id), None)

        assert scheduled_game_in_list is not None
        assert scheduled_game_in_list["date"] == "2025-12-25"
        assert scheduled_game_in_list["home_score"] == 0
        assert scheduled_game_in_list["away_score"] == 0
        assert scheduled_game_in_list["home_team"] == team1_name
        assert scheduled_game_in_list["away_team"] == team2_name

    def test_csv_import_matches_scheduled_game(self, test_client, test_db_file_session):
        """Test that CSV import matches and updates scheduled games."""
        # This test would verify the CSV import integration
        # Since CSV import is complex, this is a placeholder for the actual test
        pass  # TODO: Implement when CSV import service is testable
