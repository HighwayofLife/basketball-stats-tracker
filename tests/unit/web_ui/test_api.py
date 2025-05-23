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

    @patch("app.web_ui.routers.pages.templates")
    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
    def test_index_endpoint_error(self, mock_get_db_session, client):
        """Test the index endpoint with database error."""
        # Set up mock to raise exception
        mock_get_db_session.side_effect = Exception("Database error")

        # Make request
        response = client.get("/")

        # Assertions
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
    @patch("app.reports.ReportGenerator")
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

    @patch("app.data_access.db_session.get_db_session")
    @patch("app.reports.ReportGenerator")
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

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
    def test_list_teams_error(self, mock_get_db_session, client):
        """Test the list teams endpoint with error."""
        # Set up mock to raise exception
        mock_get_db_session.side_effect = Exception("Database error")

        # Make request
        response = client.get("/v1/teams")

        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve teams" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
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

    @patch("app.data_access.db_session.get_db_session")
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

    # Team CRUD API Tests

    @patch("app.data_access.db_session.get_db_session")
    def test_list_teams_with_counts(self, mock_get_db_session, client, mock_db_session):
        """Test listing teams with player counts."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock teams
        mock_team1 = MagicMock(spec=Team)
        mock_team1.id = 1
        mock_team1.name = "Lakers"
        mock_team2 = MagicMock(spec=Team)
        mock_team2.id = 2
        mock_team2.name = "Warriors"

        mock_db_session.query.return_value.all.return_value = [mock_team1, mock_team2]

        # Mock player counts
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [5, 8]

        # Make request
        response = client.get("/v1/teams/detail")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[0]["name"] == "Lakers"
        assert data[0]["player_count"] == 5
        assert data[1]["id"] == 2
        assert data[1]["name"] == "Warriors"
        assert data[1]["player_count"] == 8

    @patch("app.data_access.db_session.get_db_session")
    def test_create_team_success(self, mock_get_db_session, client, mock_db_session):
        """Test creating a new team successfully."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None  # No existing team

        # Mock the created team
        created_team = MagicMock()
        created_team.id = 1
        created_team.name = "New Team"
        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()

        # Make request
        response = client.post("/v1/teams/new", json={"name": "New Team"})

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "New Team"
        assert data["player_count"] == 0
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @patch("app.data_access.db_session.get_db_session")
    def test_create_team_duplicate_name(self, mock_get_db_session, client, mock_db_session):
        """Test creating a team with duplicate name."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        existing_team = MagicMock(spec=Team)
        existing_team.name = "Existing Team"
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_team

        # Make request
        response = client.post("/v1/teams/new", json={"name": "Existing Team"})

        # Assertions
        assert response.status_code == 400
        assert "Team name already exists" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_get_team_detail_success(self, mock_get_db_session, client, mock_db_session, sample_team, sample_players):
        """Test getting team detail with players."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock team query
        mock_team_query = MagicMock()
        mock_team_filter = MagicMock()
        mock_team_query.filter.return_value = mock_team_filter
        mock_team_filter.first.return_value = sample_team

        # Mock players query with ordering
        mock_players_query = MagicMock()
        mock_players_filter = MagicMock()
        mock_players_order = MagicMock()
        mock_players_query.filter.return_value = mock_players_filter
        mock_players_filter.order_by.return_value = mock_players_order
        mock_players_order.all.return_value = sample_players

        # Set up query to return different mocks based on call
        mock_db_session.query.side_effect = [mock_team_query, mock_players_query]

        # Make request
        response = client.get("/v1/teams/1/detail")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Lakers"
        assert len(data["players"]) == 2
        assert data["players"][0]["name"] == "LeBron James"
        assert data["players"][0]["jersey_number"] == 23

    @patch("app.data_access.db_session.get_db_session")
    def test_get_team_detail_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test getting team detail when team not found."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.get("/v1/teams/999/detail")

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_update_team_success(self, mock_get_db_session, client, mock_db_session, sample_team):
        """Test updating a team successfully."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock queries for team and name check
        def query_side_effect(*args):
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_query.filter.return_value = mock_filter
            if "Team.id" in str(args) or len(args) == 1:  # First query for team by ID
                mock_filter.first.return_value = sample_team
            else:  # Second query for name conflict check
                mock_filter.first.return_value = None
            return mock_query

        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.commit = MagicMock()
        mock_db_session.query.return_value.filter.return_value.count.return_value = 3  # Player count

        # Make request
        response = client.put("/v1/teams/1", json={"name": "Updated Lakers"})

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Lakers"
        assert sample_team.name == "Updated Lakers"
        mock_db_session.commit.assert_called_once()

    @patch("app.data_access.db_session.get_db_session")
    def test_update_team_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test updating a team that doesn't exist."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.put("/v1/teams/999", json={"name": "New Name"})

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_update_team_duplicate_name(self, mock_get_db_session, client, mock_db_session, sample_team):
        """Test updating a team with a name that already exists."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock existing team with different ID
        existing_team = MagicMock(spec=Team)
        existing_team.id = 2
        existing_team.name = "Existing Name"

        def query_side_effect(*args):
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_query.filter.return_value = mock_filter
            if "Team.id == team_id" in str(args) or len(args) == 1:  # First query
                mock_filter.first.return_value = sample_team
            else:  # Name conflict query
                mock_filter.first.return_value = existing_team
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        # Make request
        response = client.put("/v1/teams/1", json={"name": "Existing Name"})

        # Assertions
        assert response.status_code == 400
        assert "Team name already exists" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_delete_team_success(self, mock_get_db_session, client, mock_db_session, sample_team):
        """Test deleting a team successfully."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_team
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0  # No games
        mock_db_session.delete = MagicMock()
        mock_db_session.commit = MagicMock()

        # Make request
        response = client.delete("/v1/teams/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Team deleted successfully"
        mock_db_session.delete.assert_called_once_with(sample_team)
        mock_db_session.commit.assert_called_once()

    @patch("app.data_access.db_session.get_db_session")
    def test_delete_team_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test deleting a team that doesn't exist."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.delete("/v1/teams/999")

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_delete_team_with_games(self, mock_get_db_session, client, mock_db_session, sample_team):
        """Test deleting a team that has existing games."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_team
        mock_db_session.query.return_value.filter.return_value.count.return_value = 3  # Has games

        # Make request
        response = client.delete("/v1/teams/1")

        # Assertions
        assert response.status_code == 400
        assert "Cannot delete team with existing games" in response.json()["detail"]

    # Player CRUD API Tests

    @patch("app.data_access.db_session.get_db_session")
    def test_list_players_all(self, mock_get_db_session, client, mock_db_session, sample_players):
        """Test listing all players."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        # Mock the join query
        mock_query = MagicMock()
        mock_join = MagicMock()
        mock_filter_active = MagicMock()
        mock_order = MagicMock()

        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter_active
        mock_filter_active.order_by.return_value = mock_order

        # Create player-team tuples
        team1 = MagicMock(spec=Team)
        team1.name = "Lakers"
        team2 = MagicMock(spec=Team)
        team2.name = "Warriors"

        mock_order.all.return_value = [
            (sample_players[0], team1),
            (sample_players[1], team1),
        ]

        mock_db_session.query.return_value = mock_query

        # Make request
        response = client.get("/v1/players/list")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "LeBron James"
        assert data[0]["team_name"] == "Lakers"
        assert data[0]["jersey_number"] == 23

    @patch("app.data_access.db_session.get_db_session")
    def test_list_players_by_team(self, mock_get_db_session, client, mock_db_session, sample_players):
        """Test listing players filtered by team."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        mock_query = MagicMock()
        mock_join = MagicMock()
        mock_filter_team = MagicMock()
        mock_filter_active = MagicMock()
        mock_order = MagicMock()

        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter_team
        mock_filter_team.filter.return_value = mock_filter_active
        mock_filter_active.order_by.return_value = mock_order

        team1 = MagicMock(spec=Team)
        team1.name = "Lakers"

        mock_order.all.return_value = [(sample_players[0], team1)]
        mock_db_session.query.return_value = mock_query

        # Make request
        response = client.get("/v1/players/list?team_id=1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "LeBron James"
        assert data[0]["team_name"] == "Lakers"

    @patch("app.data_access.db_session.get_db_session")
    def test_create_player_success(self, mock_get_db_session, client, mock_db_session, sample_team):
        """Test creating a new player successfully."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        def query_side_effect(model):
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_query.filter.return_value = mock_filter
            if model == Team:
                mock_filter.first.return_value = sample_team
            else:  # Player query for duplicate check
                mock_filter.first.return_value = None
            return mock_query

        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.add = MagicMock()
        mock_db_session.commit = MagicMock()

        player_data = {
            "name": "New Player",
            "team_id": 1,
            "jersey_number": 24,
            "position": "SF",
            "height": 79,
            "weight": 220,
            "year": "Senior",
        }

        # Make request
        response = client.post("/v1/players/new", json=player_data)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Player"
        assert data["team_id"] == 1
        assert data["jersey_number"] == 24
        assert data["position"] == "SF"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @patch("app.data_access.db_session.get_db_session")
    def test_create_player_team_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test creating a player with non-existent team."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        player_data = {"name": "New Player", "team_id": 999, "jersey_number": 24}

        # Make request
        response = client.post("/v1/players/new", json=player_data)

        # Assertions
        assert response.status_code == 400
        assert "Team not found" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_create_player_duplicate_jersey(
        self, mock_get_db_session, client, mock_db_session, sample_team, sample_players
    ):
        """Test creating a player with duplicate jersey number."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session

        def query_side_effect(model):
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_query.filter.return_value = mock_filter
            if model == Team:
                mock_filter.first.return_value = sample_team
            else:  # Player query for duplicate check
                mock_filter.first.return_value = sample_players[0]  # Existing player
            return mock_query

        mock_db_session.query.side_effect = query_side_effect

        player_data = {
            "name": "New Player",
            "team_id": 1,
            "jersey_number": 23,  # Same as existing player
        }

        # Make request
        response = client.post("/v1/players/new", json=player_data)

        # Assertions
        assert response.status_code == 400
        assert "Jersey number 23 already exists" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_get_player_success(self, mock_get_db_session, client, mock_db_session, sample_players, sample_team):
        """Test getting a player successfully."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        player = sample_players[0]
        player.team = sample_team
        mock_db_session.query.return_value.filter.return_value.first.return_value = player

        # Make request
        response = client.get("/v1/players/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "LeBron James"
        assert data["team_name"] == "Lakers"
        assert data["jersey_number"] == 23

    @patch("app.data_access.db_session.get_db_session")
    def test_get_player_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test getting a player that doesn't exist."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.get("/v1/players/999")

        # Assertions
        assert response.status_code == 404
        assert "Player not found" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_update_player_success(self, mock_get_db_session, client, mock_db_session, sample_players, sample_team):
        """Test updating a player successfully."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        player = sample_players[0]
        player.team = sample_team

        def query_side_effect(model):
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_query.filter.return_value = mock_filter
            if model == Player and "Player.id" in str(mock_filter):
                mock_filter.first.return_value = player
            else:
                mock_filter.first.return_value = None  # No conflicts
            return mock_query

        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.commit = MagicMock()

        update_data = {"name": "Updated Name", "jersey_number": 24, "position": "PF"}

        # Make request
        response = client.put("/v1/players/1", json=update_data)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["jersey_number"] == 24
        assert data["position"] == "PF"
        assert player.name == "Updated Name"
        assert player.jersey_number == 24
        assert player.position == "PF"
        mock_db_session.commit.assert_called_once()

    @patch("app.data_access.db_session.get_db_session")
    def test_update_player_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test updating a player that doesn't exist."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.put("/v1/players/999", json={"name": "New Name"})

        # Assertions
        assert response.status_code == 404
        assert "Player not found" in response.json()["detail"]

    @patch("app.data_access.db_session.get_db_session")
    def test_delete_player_with_stats(self, mock_get_db_session, client, mock_db_session, sample_players):
        """Test deleting a player that has game stats (should deactivate)."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        player = sample_players[0]

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Player:
                mock_query.filter.return_value.first.return_value = player
            else:  # PlayerGameStats
                mock_query.filter.return_value.count.return_value = 5  # Has stats
            return mock_query

        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.commit = MagicMock()

        # Make request
        response = client.delete("/v1/players/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "deactivated successfully" in data["message"]
        assert player.is_active is False
        mock_db_session.commit.assert_called_once()

    @patch("app.data_access.db_session.get_db_session")
    def test_delete_player_without_stats(self, mock_get_db_session, client, mock_db_session, sample_players):
        """Test deleting a player that has no game stats (should delete)."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        player = sample_players[0]

        def query_side_effect(model):
            mock_query = MagicMock()
            if model == Player:
                mock_query.filter.return_value.first.return_value = player
            else:  # PlayerGameStats
                mock_query.filter.return_value.count.return_value = 0  # No stats
            return mock_query

        mock_db_session.query.side_effect = query_side_effect
        mock_db_session.delete = MagicMock()
        mock_db_session.commit = MagicMock()

        # Make request
        response = client.delete("/v1/players/1")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        mock_db_session.delete.assert_called_once_with(player)
        mock_db_session.commit.assert_called_once()

    @patch("app.data_access.db_session.get_db_session")
    def test_delete_player_not_found(self, mock_get_db_session, client, mock_db_session):
        """Test deleting a player that doesn't exist."""
        # Set up mocks
        mock_get_db_session.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Make request
        response = client.delete("/v1/players/999")

        # Assertions
        assert response.status_code == 404
        assert "Player not found" in response.json()["detail"]
