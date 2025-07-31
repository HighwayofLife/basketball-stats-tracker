"""Unit tests for the playoffs router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import require_admin
from app.web_ui.api import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestPlayoffsRouter:
    """Test cases for playoffs API endpoints."""

    @patch("app.web_ui.routers.playoffs.get_db")
    @patch("app.web_ui.routers.playoffs.PlayoffsService")
    def test_get_playoff_bracket(self, mock_service_class, mock_get_db, client):
        """Test GET /v1/playoffs/bracket endpoint."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock service instance and response
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_playoff_bracket.return_value = {
            "season": "2025",
            "champion": {"team_id": 1, "team_name": "Champions"},
            "finals": {
                "matchup": {
                    "game_id": 101,
                    "team1": {"team_id": 1, "team_name": "Team A", "score": 100},
                    "team2": {"team_id": 2, "team_name": "Team B", "score": 95},
                }
            },
            "semi_finals": [],
        }

        # Make request
        response = client.get("/v1/playoffs/bracket")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == "2025"
        assert data["champion"]["team_name"] == "Champions"
        assert data["finals"]["matchup"]["game_id"] == 101

        # Verify service was called correctly
        mock_service_class.assert_called_once()
        mock_service.get_playoff_bracket.assert_called_once_with(season=None)

    @patch("app.web_ui.routers.playoffs.get_db")
    @patch("app.web_ui.routers.playoffs.PlayoffsService")
    def test_get_playoff_bracket_with_season(self, mock_service_class, mock_get_db, client):
        """Test GET /v1/playoffs/bracket with season parameter."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock service instance and response
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_playoff_bracket.return_value = {
            "season": "2024",
            "champion": None,
            "finals": None,
            "semi_finals": [],
        }

        # Make request with season parameter
        response = client.get("/v1/playoffs/bracket?season=2024")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["season"] == "2024"

        # Verify service was called with season
        mock_service.get_playoff_bracket.assert_called_once_with(season="2024")

    @patch("app.web_ui.routers.playoffs.get_db")
    @patch("app.web_ui.routers.playoffs.PlayoffsService")
    def test_mark_game_as_playoff(self, mock_service_class, mock_get_db, client):
        """Test POST /v1/playoffs/games/{game_id}/mark-playoff endpoint."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock admin user using dependency override
        def mock_admin_user():
            admin = MagicMock()
            admin.username = "admin"
            admin.role = "admin"
            return admin

        app.dependency_overrides[require_admin] = mock_admin_user

        # Mock service instance and game
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_game = MagicMock(id=1)
        mock_service.mark_game_as_playoff.return_value = mock_game

        try:
            # Make request
            response = client.post("/v1/playoffs/games/1/mark-playoff")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["game_id"] == 1
            assert "marked as playoff game" in data["message"]

            # Verify service was called
            mock_service.mark_game_as_playoff.assert_called_once_with(1)
        finally:
            # Cleanup dependency override
            app.dependency_overrides.clear()

    @patch("app.web_ui.routers.playoffs.get_db")
    @patch("app.web_ui.routers.playoffs.PlayoffsService")
    def test_mark_game_as_playoff_not_found(self, mock_service_class, mock_get_db, client):
        """Test marking non-existent game as playoff."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock admin user using dependency override
        def mock_admin_user():
            admin = MagicMock()
            admin.username = "admin"
            admin.role = "admin"
            return admin

        app.dependency_overrides[require_admin] = mock_admin_user

        # Mock service instance to raise GameNotFoundError
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        from app.services.playoffs_service import GameNotFoundError

        mock_service.mark_game_as_playoff.side_effect = GameNotFoundError("Game with ID 999 not found")

        try:
            # Make request
            response = client.post("/v1/playoffs/games/999/mark-playoff")

            # Verify error response - Should return 404 for not found
            assert response.status_code == 404
        finally:
            # Cleanup dependency override
            app.dependency_overrides.clear()

    @patch("app.web_ui.routers.playoffs.get_db")
    @patch("app.web_ui.routers.playoffs.PlayoffsService")
    def test_unmark_game_as_playoff(self, mock_service_class, mock_get_db, client):
        """Test DELETE /v1/playoffs/games/{game_id}/mark-playoff endpoint."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock admin user using dependency override
        def mock_admin_user():
            admin = MagicMock()
            admin.username = "admin"
            admin.role = "admin"
            return admin

        app.dependency_overrides[require_admin] = mock_admin_user

        # Mock service instance and game
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_game = MagicMock(id=1)
        mock_service.unmark_game_as_playoff.return_value = mock_game

        try:
            # Make request
            response = client.delete("/v1/playoffs/games/1/mark-playoff")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["game_id"] == 1
            assert "no longer marked as playoff game" in data["message"]

            # Verify service was called
            mock_service.unmark_game_as_playoff.assert_called_once_with(1)
        finally:
            # Cleanup dependency override
            app.dependency_overrides.clear()

    @patch("app.web_ui.routers.playoffs.get_db")
    @patch("app.web_ui.routers.playoffs.PlayoffsService")
    def test_unmark_game_as_playoff_not_found(self, mock_service_class, mock_get_db, client):
        """Test unmarking non-existent game as playoff."""
        # Mock database session
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock admin user using dependency override
        def mock_admin_user():
            admin = MagicMock()
            admin.username = "admin"
            admin.role = "admin"
            return admin

        app.dependency_overrides[require_admin] = mock_admin_user

        # Mock service instance to raise GameNotFoundError
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        from app.services.playoffs_service import GameNotFoundError

        mock_service.unmark_game_as_playoff.side_effect = GameNotFoundError("Game with ID 999 not found")

        try:
            # Make request
            response = client.delete("/v1/playoffs/games/999/mark-playoff")

            # Verify error response - Should return 404 for not found
            assert response.status_code == 404
        finally:
            # Cleanup dependency override
            app.dependency_overrides.clear()
