"""
Unit tests for the FastAPI application endpoints.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data_access.models import Base, Game, Player, PlayerGameStats, Team
from app.web_ui.api import app
from app.web_ui.dependencies import get_db


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    @pytest.fixture(scope="class")
    def test_db_file(self, tmp_path_factory):
        """Create a temporary database file for testing."""
        # Create a temporary file for the database
        db_file = tmp_path_factory.mktemp("data") / "test.db"
        return str(db_file)

    @pytest.fixture
    def test_db_engine(self, test_db_file):
        """Create a database engine with a file-based database for sharing between sessions."""
        from sqlalchemy import create_engine

        engine = create_engine(f"sqlite:///{test_db_file}")
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)

    @pytest.fixture
    def db_session(self, test_db_engine):
        """Override the db_session fixture to use our test engine."""
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    @pytest.fixture
    def client(self, db_session, test_db_engine, monkeypatch):
        """Create a test client with proper database dependency override."""
        from contextlib import contextmanager

        from sqlalchemy.orm import Session

        # Important: We need to ensure all database access uses the same underlying
        # database. We'll commit data in db_session so it's visible to other sessions.
        db_session.commit()

        # Create a context manager that yields a new session connected to the same db
        @contextmanager
        def test_get_db_session():
            # Create a new session from the same engine
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Monkey-patch the get_db_session function in all the modules that import it
        import app.data_access.db_session as db_session_module
        import app.web_ui.routers.admin as admin_module
        import app.web_ui.routers.games as games_module
        import app.web_ui.routers.pages as pages_module
        import app.web_ui.routers.players as players_module

        monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(pages_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(games_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(players_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(admin_module, "get_db_session", test_get_db_session)

        # Also override the dependency for endpoints that use proper DI (teams router)
        def override_get_db():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        app.dependency_overrides[get_db] = override_get_db

        yield TestClient(app)

        # Clean up
        app.dependency_overrides.clear()

    @pytest.fixture
    def sample_team(self, db_session):
        """Create a sample team in the database."""
        team = Team(name="Lakers", is_deleted=False, deleted_at=None, deleted_by=None)
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        return team

    @pytest.fixture
    def sample_team_2(self, db_session):
        """Create a second sample team in the database."""
        team = Team(name="Warriors", is_deleted=False, deleted_at=None, deleted_by=None)
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        return team

    @pytest.fixture
    def sample_players(self, db_session, sample_team):
        """Create sample players in the database."""
        player1 = Player(
            name="LeBron James",
            jersey_number=23,
            team_id=sample_team.id,
            position="SF",
            height=81,
            weight=250,
            year="Veteran",
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )
        player2 = Player(
            name="Anthony Davis",
            jersey_number=3,
            team_id=sample_team.id,
            position="PF",
            height=82,
            weight=253,
            year="Veteran",
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )
        db_session.add_all([player1, player2])
        db_session.commit()
        db_session.refresh(player1)
        db_session.refresh(player2)
        return [player1, player2]

    @pytest.fixture
    def sample_game(self, db_session, sample_team, sample_team_2):
        """Create a sample game in the database."""
        game = Game(
            date=date(2025, 5, 1),
            playing_team_id=sample_team.id,
            opponent_team_id=sample_team_2.id,
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)
        return game

    @pytest.fixture
    def sample_game_stats(self, db_session, sample_game, sample_players):
        """Create sample game statistics in the database."""
        stats = []
        for player in sample_players:
            stat = PlayerGameStats(
                game_id=sample_game.id,
                player_id=player.id,
                fouls=2,
                total_ftm=5,
                total_fta=6,
                total_2pm=4,
                total_2pa=8,
                total_3pm=2,
                total_3pa=5,
            )
            db_session.add(stat)
            stats.append(stat)
        db_session.commit()
        for stat in stats:
            db_session.refresh(stat)
        return stats

    # Index and Page Tests

    @patch("app.web_ui.routers.pages.templates")
    def test_index_endpoint(self, mock_templates, client, sample_game):
        """Test the index endpoint."""
        # Set up template mock
        from fastapi.responses import HTMLResponse

        mock_templates.TemplateResponse.return_value = HTMLResponse(
            content="<html>Basketball Stats Dashboard</html>", status_code=200
        )

        # Make request
        response = client.get("/")

        # Assertions
        assert response.status_code == 200
        mock_templates.TemplateResponse.assert_called_once()

    def test_index_endpoint_error(self, client, monkeypatch):
        """Test the index endpoint with database error."""

        # Monkey-patch get_db_session to raise error
        def error_db_session():
            raise Exception("Database error")

        import app.web_ui.routers.pages as pages_module

        monkeypatch.setattr(pages_module, "get_db_session", error_db_session)

        # Make request
        response = client.get("/")

        # Assertions
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    # Game API Tests

    def test_list_games_endpoint(self, client, sample_game):
        """Test the list games endpoint."""
        # Make request
        response = client.get("/v1/games")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_game.id
        assert data[0]["home_team"] == "Lakers"
        assert data[0]["away_team"] == "Warriors"

    def test_list_games_with_team_filter(self, client, sample_game, sample_team):
        """Test the list games endpoint with team filter."""
        # Make request with team filter
        response = client.get(f"/v1/games?team_id={sample_team.id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_games_with_pagination(self, client):
        """Test the list games endpoint with pagination."""
        # Make request with pagination
        response = client.get("/v1/games?limit=10&offset=20")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data == []  # No games at offset 20

    def test_get_game_endpoint(self, client, sample_game):
        """Test the get game endpoint."""
        # Make request
        response = client.get(f"/v1/games/{sample_game.id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_game.id
        assert data["home_team"] == "Lakers"
        assert data["away_team"] == "Warriors"

    def test_get_game_not_found(self, client):
        """Test the get game endpoint when game not found."""
        # Make request
        response = client.get("/v1/games/999")

        # Assertions
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    @patch("app.web_ui.routers.games.ReportGenerator")
    def test_get_box_score_endpoint(self, mock_report_gen_class, client, sample_game, sample_team, sample_game_stats):
        """Test the get box score endpoint."""
        # Mock report generator
        mock_report_gen = MagicMock()
        mock_report_gen_class.return_value = mock_report_gen

        player_stats = [
            {
                "player_id": 1,
                "player_name": "LeBron James",
                "team_id": sample_team.id,
                "team_name": "Lakers",
                "points": 25,
                "rebounds": 7,
                "assists": 8,
                "fouls": 2,
                "ftm": 5,
                "fta": 6,
                "fg2m": 4,
                "fg2a": 8,
                "fg3m": 2,
                "fg3a": 5,
            },
            {
                "player_id": 2,
                "player_name": "Anthony Davis",
                "team_id": sample_team.id,
                "team_name": "Lakers",
                "points": 22,
                "rebounds": 10,
                "assists": 3,
                "fouls": 2,
                "ftm": 5,
                "fta": 6,
                "fg2m": 4,
                "fg2a": 8,
                "fg3m": 2,
                "fg3a": 5,
            },
        ]
        game_summary = {"playing_team": "Lakers", "opponent_team": "Warriors"}
        mock_report_gen.get_game_box_score_data.return_value = (player_stats, game_summary)

        # Make request
        response = client.get(f"/v1/games/{sample_game.id}/box-score")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == sample_game.id
        assert data["home_team"]["name"] == "Lakers"
        assert data["home_team"]["score"] == 47  # 25 + 22
        assert len(data["home_team"]["players"]) == 2

    @patch("app.web_ui.routers.games.ReportGenerator")
    def test_get_box_score_not_found(self, mock_report_gen_class, client):
        """Test the get box score endpoint when game not found."""
        # Mock report generator to return None
        mock_report_gen = MagicMock()
        mock_report_gen_class.return_value = mock_report_gen
        mock_report_gen.get_game_box_score_data.return_value = (None, None)

        # Make request
        response = client.get("/v1/games/999/box-score")

        # Assertions
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    # Team API Tests

    def test_list_teams_endpoint(self, client, sample_team):
        """Test the list teams endpoint."""
        # Make request
        response = client.get("/v1/teams")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_team.id
        assert data[0]["name"] == "Lakers"

    def test_list_teams_empty(self, client):
        """Test the list teams endpoint with no teams."""
        # When no teams exist, should return empty list
        response = client.get("/v1/teams")

        # The endpoint should work normally
        assert response.status_code == 200
        assert response.json() == []

    def test_get_team_endpoint(self, client, sample_team, sample_players):
        """Test the get team endpoint."""
        # Make request
        response = client.get(f"/v1/teams/{sample_team.id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_team.id
        assert data["name"] == "Lakers"
        assert len(data["roster"]) == 2
        # Players are ordered by jersey number
        assert data["roster"][0]["name"] == "Anthony Davis"
        assert data["roster"][0]["jersey_number"] == 3
        assert data["roster"][1]["name"] == "LeBron James"
        assert data["roster"][1]["jersey_number"] == 23

    def test_get_team_not_found(self, client):
        """Test the get team endpoint when team not found."""
        # Make request
        response = client.get("/v1/teams/999")

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    @patch("app.web_ui.routers.pages.templates")
    def test_games_page(self, mock_templates, client):
        """Test the games HTML page endpoint."""
        # Set up mock
        from fastapi.responses import HTMLResponse

        mock_templates.TemplateResponse.return_value = HTMLResponse(content="<html>Games Page</html>", status_code=200)

        # Make request
        response = client.get("/games")

        # Assertions
        assert response.status_code == 200
        mock_templates.TemplateResponse.assert_called_once()
        args = mock_templates.TemplateResponse.call_args[0]
        assert args[0] == "games/index.html"

    @patch("app.web_ui.routers.pages.templates")
    def test_game_detail_page(self, mock_templates, client, sample_game):
        """Test the game detail HTML page endpoint."""
        # Set up mock
        from fastapi.responses import HTMLResponse

        mock_templates.TemplateResponse.return_value = HTMLResponse(content="<html>Game Detail</html>", status_code=200)

        # Make request
        response = client.get(f"/games/{sample_game.id}")

        # Assertions
        assert response.status_code == 200
        mock_templates.TemplateResponse.assert_called_once()
        args = mock_templates.TemplateResponse.call_args[0]
        assert args[0] == "games/detail.html"

    def test_game_detail_page_not_found(self, client):
        """Test the game detail page when game not found."""
        # Make request
        response = client.get("/games/999")

        # Assertions
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    # Team CRUD API Tests

    def test_list_teams_with_counts(self, client, sample_team, sample_players):
        """Test listing teams with player counts."""
        # Make request
        response = client.get("/v1/teams/detail")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_team.id
        assert data[0]["name"] == "Lakers"
        assert data[0]["player_count"] == 2

    def test_create_team_success(self, client):
        """Test creating a new team successfully."""
        # Make request
        response = client.post("/v1/teams/new", json={"name": "New Team"})

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "New Team"
        assert data["player_count"] == 0

    def test_create_team_duplicate_name(self, client, sample_team):
        """Test creating a team with duplicate name."""
        # Make request
        response = client.post("/v1/teams/new", json={"name": "Lakers"})

        # Assertions
        assert response.status_code == 400
        assert "Team name already exists" in response.json()["detail"]

    def test_get_team_detail_success(self, client, sample_team, sample_players):
        """Test getting team detail with players."""
        # Make request
        response = client.get(f"/v1/teams/{sample_team.id}/detail")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_team.id
        assert data["name"] == "Lakers"
        assert len(data["players"]) == 2
        # Players are ordered by jersey number
        assert data["players"][0]["name"] == "Anthony Davis"
        assert data["players"][0]["jersey_number"] == 3
        assert data["players"][1]["name"] == "LeBron James"
        assert data["players"][1]["jersey_number"] == 23

    def test_get_team_detail_not_found(self, client):
        """Test getting team detail when team not found."""
        # Make request
        response = client.get("/v1/teams/999/detail")

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    def test_update_team_success(self, client, sample_team):
        """Test updating a team successfully."""
        # Make request
        response = client.put(f"/v1/teams/{sample_team.id}", json={"name": "Updated Lakers"})

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Lakers"
        assert data["player_count"] == 0

    def test_update_team_not_found(self, client):
        """Test updating a team that doesn't exist."""
        # Make request
        response = client.put("/v1/teams/999", json={"name": "New Name"})

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    def test_update_team_duplicate_name(self, client, sample_team, sample_team_2):
        """Test updating a team with a name that already exists."""
        # Make request
        response = client.put(f"/v1/teams/{sample_team.id}", json={"name": "Warriors"})

        # Assertions
        assert response.status_code == 400
        assert "Team name already exists" in response.json()["detail"]

    def test_delete_team_success(self, client, db_session):
        """Test deleting a team successfully."""
        # Create a team without any games
        team = Team(name="Deletable Team")
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        # Make request
        response = client.delete(f"/v1/teams/{team.id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Team deleted successfully"

    def test_delete_team_not_found(self, client):
        """Test deleting a team that doesn't exist."""
        # Make request
        response = client.delete("/v1/teams/999")

        # Assertions
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    def test_delete_team_with_games(self, client, sample_team, sample_game):
        """Test deleting a team that has existing games."""
        # Make request
        response = client.delete(f"/v1/teams/{sample_team.id}")

        # Assertions
        assert response.status_code == 400
        assert "Cannot delete team with existing games" in response.json()["detail"]

    # Player CRUD API Tests

    def test_list_players_all(self, client, sample_players):
        """Test listing all players."""
        # Make request
        response = client.get("/v1/players/list")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Players are ordered by jersey number, so Anthony Davis (#3) comes first
        assert data[0]["name"] == "Anthony Davis"
        assert data[0]["team_name"] == "Lakers"
        assert data[0]["jersey_number"] == 3
        assert data[1]["name"] == "LeBron James"
        assert data[1]["jersey_number"] == 23

    def test_list_players_by_team(self, client, sample_team, sample_players):
        """Test listing players filtered by team."""
        # Make request
        response = client.get(f"/v1/players/list?team_id={sample_team.id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Players are ordered by jersey number
        assert data[0]["name"] == "Anthony Davis"
        assert data[0]["team_name"] == "Lakers"
        assert data[1]["name"] == "LeBron James"

    def test_create_player_success(self, client, sample_team):
        """Test creating a new player successfully."""
        player_data = {
            "name": "New Player",
            "team_id": sample_team.id,
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
        assert data["team_id"] == sample_team.id
        assert data["jersey_number"] == 24
        assert data["position"] == "SF"

    def test_create_player_team_not_found(self, client):
        """Test creating a player with non-existent team."""
        player_data = {"name": "New Player", "team_id": 999, "jersey_number": 24}

        # Make request
        response = client.post("/v1/players/new", json=player_data)

        # Assertions
        assert response.status_code == 400
        assert "Team not found" in response.json()["detail"]

    def test_create_player_duplicate_jersey(self, client, sample_team, sample_players):
        """Test creating a player with duplicate jersey number."""
        player_data = {
            "name": "New Player",
            "team_id": sample_team.id,
            "jersey_number": 23,  # Same as existing player
        }

        # Make request
        response = client.post("/v1/players/new", json=player_data)

        # Assertions
        assert response.status_code == 400
        assert "Jersey number 23 already exists" in response.json()["detail"]

    def test_get_player_success(self, client, sample_players):
        """Test getting a player successfully."""
        # Make request
        response = client.get(f"/v1/players/{sample_players[0].id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_players[0].id
        assert data["name"] == "LeBron James"
        assert data["team_name"] == "Lakers"
        assert data["jersey_number"] == 23

    def test_get_player_not_found(self, client):
        """Test getting a player that doesn't exist."""
        # Make request
        response = client.get("/v1/players/999")

        # Assertions
        assert response.status_code == 404
        assert "Player not found" in response.json()["detail"]

    def test_update_player_success(self, client, sample_players):
        """Test updating a player successfully."""
        update_data = {"name": "Updated Name", "jersey_number": 24, "position": "PF"}

        # Make request
        response = client.put(f"/v1/players/{sample_players[0].id}", json=update_data)

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["jersey_number"] == 24
        assert data["position"] == "PF"

    def test_update_player_not_found(self, client):
        """Test updating a player that doesn't exist."""
        # Make request
        response = client.put("/v1/players/999", json={"name": "New Name"})

        # Assertions
        assert response.status_code == 404
        assert "Player not found" in response.json()["detail"]

    def test_delete_player_with_stats(self, client, sample_players, sample_game_stats):
        """Test deleting a player that has game stats (should deactivate)."""
        # Make request
        response = client.delete(f"/v1/players/{sample_players[0].id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "deactivated successfully" in data["message"]

    def test_delete_player_without_stats(self, client, db_session, sample_team):
        """Test deleting a player that has no game stats (should delete)."""
        # Create a player without stats
        player = Player(name="Deletable Player", jersey_number=99, team_id=sample_team.id, is_active=True)
        db_session.add(player)
        db_session.commit()
        db_session.refresh(player)

        # Make request
        response = client.delete(f"/v1/players/{player.id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

    def test_delete_player_not_found(self, client):
        """Test deleting a player that doesn't exist."""
        # Make request
        response = client.delete("/v1/players/999")

        # Assertions
        assert response.status_code == 404
        assert "Player not found" in response.json()["detail"]
