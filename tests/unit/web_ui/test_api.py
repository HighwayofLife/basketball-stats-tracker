"""
Unit tests for the FastAPI application endpoints.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data_access.models import Game, Player, Team
from app.web_ui.api import app


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=None)
        return session

    @pytest.fixture
    def sample_game(self):
        """Create a sample game object."""
        game = MagicMock(spec=Game)
        game.id = 1
        game.date = date(2025, 5, 1)
        game.playing_team_id = 1
        game.opponent_team_id = 2

        # Create proper team mocks with name attributes
        playing_team = MagicMock(spec=Team)
        playing_team.id = 1
        playing_team.name = "Lakers"
        game.playing_team = playing_team

        opponent_team = MagicMock(spec=Team)
        opponent_team.id = 2
        opponent_team.name = "Warriors"
        game.opponent_team = opponent_team

        return game

    @pytest.fixture
    def sample_team(self):
        """Create a sample team object."""
        team = MagicMock(spec=Team)
        team.id = 1
        team.name = "Lakers"
        return team

    @pytest.fixture
    def sample_players(self):
        """Create sample player objects."""
        player1 = MagicMock(spec=Player)
        player1.id = 1
        player1.name = "LeBron James"
        player1.jersey_number = 23
        player1.team_id = 1

        player2 = MagicMock(spec=Player)
        player2.id = 2
        player2.name = "Anthony Davis"
        player2.jersey_number = 3
        player2.team_id = 1

        return [player1, player2]

    @patch("app.web_ui.api.templates")
    @patch("app.web_ui.api.get_db_session")
    def test_index_endpoint(self, mock_get_db_session, mock_templates, client, mock_db_session, sample_game):
        """Test the index endpoint."""
        # Set up database mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_game]

        # Set up template mock
        # pylint: disable=import-outside-toplevel
        from fastapi.responses import HTMLResponse

        mock_templates.TemplateResponse.return_value = HTMLResponse(
            content="<html>Basketball Stats Dashboard</html>", status_code=200
        )

        # Make request
        response = client.get("/")

        # Assertions
        assert response.status_code == 200
        mock_db_session.query.assert_called_once()
        mock_templates.TemplateResponse.assert_called_once()

    @patch("app.web_ui.api.get_db_session")
    def test_index_endpoint_error(self, mock_get_db_session, client):
        """Test the index endpoint with database error."""
        # Set up mock to raise exception
        mock_get_db_session.side_effect = Exception("Database error")

        # Make request
        response = client.get("/")

        # Assertions
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @patch("app.web_ui.api.get_db_session")
    def test_list_games_endpoint(self, mock_get_db_session, client, mock_db_session, sample_game):
        """Test the list games endpoint."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_game]

        # Make request
        response = client.get("/v1/games")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["home_team"] == "Lakers"
        assert data[0]["away_team"] == "Warriors"

    @patch("app.web_ui.api.get_db_session")
    def test_list_games_with_team_filter(self, mock_get_db_session, client, mock_db_session, sample_game):
        """Test the list games endpoint with team filter."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_game]

        # Make request with team filter
        response = client.get("/v1/games?team_id=1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mock_query.filter.assert_called_once()

    @patch("app.web_ui.api.get_db_session")
    def test_list_games_with_pagination(self, mock_get_db_session, client, mock_db_session):
        """Test the list games endpoint with pagination."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        # Make request with pagination
        response = client.get("/v1/games?limit=10&offset=20")

        # Assertions
        assert response.status_code == 200
        mock_query.offset.assert_called_once_with(20)
        mock_query.limit.assert_called_once_with(10)

    @patch("app.web_ui.api.get_db_session")
    def test_get_game_endpoint(self, mock_get_db_session, client, mock_db_session, sample_game):
        """Test the get game endpoint."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_game

        # Make request
        response = client.get("/v1/games/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["home_team"] == "Lakers"
        assert data["away_team"] == "Warriors"

    @patch("app.web_ui.api.get_db_session")
    def test_get_game_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test the get game endpoint when game not found."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        # Make request
        response = client.get("/v1/games/999")

        # Assertions
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    @patch("app.web_ui.api.get_db_session")
    @patch("app.web_ui.api.ReportGenerator")
    def test_get_box_score_endpoint(
        self, mock_report_gen_class, mock_get_db_session, client, mock_db_session, sample_game
    ):
        """Test the get box score endpoint."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock report generator
        mock_report_gen = MagicMock()
        mock_report_gen_class.return_value = mock_report_gen

        player_stats = [
            {
                "player_id": 1,
                "player_name": "LeBron James",
                "team_id": 1,
                "team_name": "Lakers",
                "points": 25,
                "rebounds": 7,
                "assists": 8,
            },
            {
                "player_id": 2,
                "player_name": "Anthony Davis",
                "team_id": 1,
                "team_name": "Lakers",
                "points": 22,
                "rebounds": 10,
                "assists": 3,
            },
        ]
        game_summary = {"playing_team": "Lakers", "opponent_team": "Warriors"}
        mock_report_gen.get_game_box_score_data.return_value = (player_stats, game_summary)

        # Mock game query
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_game

        # Make request
        response = client.get("/v1/games/1/box-score")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == 1
        assert data["home_team"]["name"] == "Lakers"
        assert data["home_team"]["score"] == 47  # 25 + 22
        assert len(data["home_team"]["players"]) == 2

    @patch("app.web_ui.api.get_db_session")
    @patch("app.web_ui.api.ReportGenerator")
    def test_get_box_score_not_found(self, mock_report_gen_class, mock_get_db_session, client, mock_db_session):
        """Test the get box score endpoint when game not found."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock report generator to return None
        mock_report_gen = MagicMock()
        mock_report_gen_class.return_value = mock_report_gen
        mock_report_gen.get_game_box_score_data.return_value = (None, None)

        # Make request
        response = client.get("/v1/games/999/box-score")

        # Assertions
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    @patch("app.web_ui.api.get_db_session")
    def test_list_teams_endpoint(self, mock_get_db_session, client, mock_db_session, sample_team):
        """Test the list teams endpoint."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.all.return_value = [sample_team]

        # Make request
        response = client.get("/v1/teams")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Lakers"

    @patch("app.web_ui.api.get_db_session")
    def test_list_teams_error(self, mock_get_db_session, client):
        """Test the list teams endpoint with error."""
        # Set up mock to raise exception
        mock_get_db_session.side_effect = Exception("Database error")

        # Make request
        response = client.get("/v1/teams")

        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve teams" in response.json()["detail"]

    @patch("app.web_ui.api.get_db_session")
    def test_get_team_endpoint(self, mock_get_db_session, client, mock_db_session, sample_team, sample_players):
        """Test the get team endpoint."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock team query
        mock_team_query = MagicMock()
        mock_team_filter = MagicMock()
        mock_team_query.filter.return_value = mock_team_filter
        mock_team_filter.first.return_value = sample_team

        # Mock players query
        mock_players_query = MagicMock()
        mock_players_filter = MagicMock()
        mock_players_query.filter.return_value = mock_players_filter
        mock_players_filter.all.return_value = sample_players

        # Set up query to return different mocks based on the model
        def query_side_effect(model):
            if model == Team:
                return mock_team_query
            elif model == Player:
                return mock_players_query
            return MagicMock()

        mock_db_session.query.side_effect = query_side_effect

        # Make request
        response = client.get("/v1/teams/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Lakers"
        assert len(data["roster"]) == 2
        assert data["roster"][0]["name"] == "LeBron James"
        assert data["roster"][0]["jersey_number"] == 23

    @patch("app.web_ui.api.get_db_session")
    def test_get_team_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test the get team endpoint when team not found."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        # Make request
        response = client.get("/v1/teams/999")

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    @patch("app.web_ui.api.templates")
    def test_games_page(self, mock_templates, client):
        """Test the games HTML page endpoint."""
        # Set up mock
        # pylint: disable=import-outside-toplevel
        from fastapi.responses import HTMLResponse

        mock_templates.TemplateResponse.return_value = HTMLResponse(content="<html>Games Page</html>", status_code=200)

        # Make request
        response = client.get("/games")

        # Assertions
        assert response.status_code == 200
        mock_templates.TemplateResponse.assert_called_once()
        args = mock_templates.TemplateResponse.call_args[0]
        assert args[0] == "games/index.html"

    @patch("app.web_ui.api.get_db_session")
    @patch("app.web_ui.api.templates")
    def test_game_detail_page(self, mock_templates, mock_get_db_session, client, mock_db_session, sample_game):
        """Test the game detail HTML page endpoint."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_game

        # pylint: disable=import-outside-toplevel
        from fastapi.responses import HTMLResponse

        mock_templates.TemplateResponse.return_value = HTMLResponse(content="<html>Game Detail</html>", status_code=200)

        # Make request
        response = client.get("/games/1")

        # Assertions
        assert response.status_code == 200
        mock_templates.TemplateResponse.assert_called_once()
        args = mock_templates.TemplateResponse.call_args[0]
        assert args[0] == "games/detail.html"

    @patch("app.web_ui.api.get_db_session")
    def test_game_detail_page_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test the game detail page when game not found."""
        # Set up mock
        mock_get_db_session.return_value = mock_db_session
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        # Make request
        response = client.get("/games/999")

        # Assertions
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]
