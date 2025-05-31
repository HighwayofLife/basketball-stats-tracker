"""
Tests for the scorebook API endpoint.
"""

from contextlib import contextmanager

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.data_access.models import Base, Player, Team
from app.web_ui import app
from app.web_ui.dependencies import get_db


class TestScorebookAPI:
    """Tests for the scorebook game creation API."""

    @pytest.fixture(scope="class")
    def test_db_file(self, tmp_path_factory):
        """Create a temporary database file for testing."""
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
        db_session.commit()

        @contextmanager
        def test_get_db_session():
            new_session = Session(bind=test_db_engine)
            try:
                yield new_session
            finally:
                new_session.close()

        # Monkey-patch the get_db_session function
        import app.data_access.db_session as db_session_module
        import app.web_ui.routers.games as games_module

        monkeypatch.setattr(db_session_module, "get_db_session", test_get_db_session)
        monkeypatch.setattr(games_module, "get_db_session", test_get_db_session)

        def override_get_db():
            new_session = Session(bind=test_db_engine)
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
                role=UserRole.ADMIN,  # Use admin to bypass all auth checks
                is_active=True,
                provider="local"
            )
            return user
            
        def mock_admin_user():
            """Mock admin user for testing."""
            return mock_current_user()
            
        app.dependency_overrides[get_current_user] = mock_current_user
        app.dependency_overrides[require_admin] = mock_admin_user

        yield TestClient(app)
        app.dependency_overrides.clear()

    @pytest.fixture
    def sample_teams(self, db_session):
        """Create sample teams in the database."""
        team1 = Team(name="Lakers", display_name="Lakers")
        team2 = Team(name="Warriors", display_name="Warriors")
        db_session.add_all([team1, team2])
        db_session.commit()
        db_session.refresh(team1)
        db_session.refresh(team2)
        return [team1, team2]

    @pytest.fixture
    def sample_players(self, db_session, sample_teams):
        """Create sample players in the database."""
        players = [
            Player(name="LeBron James", jersey_number="23", team_id=sample_teams[0].id, is_active=True),
            Player(name="Anthony Davis", jersey_number="3", team_id=sample_teams[0].id, is_active=True),
            Player(name="Stephen Curry", jersey_number="30", team_id=sample_teams[1].id, is_active=True),
            Player(name="Klay Thompson", jersey_number="11", team_id=sample_teams[1].id, is_active=True),
        ]
        db_session.add_all(players)
        db_session.commit()
        for player in players:
            db_session.refresh(player)
        return players

    def test_create_game_from_scorebook(self, client, sample_teams, sample_players):
        """Test creating a game with scorebook data."""
        home_team = sample_teams[0]
        away_team = sample_teams[1]

        # Create game data
        game_data = {
            "date": "2024-03-15",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "location": "Home Arena",
            "notes": "Test game",
            "player_stats": [
                {
                    "player_id": sample_players[0].id,
                    "player_name": sample_players[0].name,
                    "jersey_number": sample_players[0].jersey_number,
                    "team_id": home_team.id,
                    "fouls": 2,
                    "qt1_shots": "22-",
                    "qt2_shots": "3/",
                    "qt3_shots": "11",
                    "qt4_shots": "-",
                },
                {
                    "player_id": sample_players[2].id,
                    "player_name": sample_players[2].name,
                    "jersey_number": sample_players[2].jersey_number,
                    "team_id": away_team.id,
                    "fouls": 3,
                    "qt1_shots": "2",
                    "qt2_shots": "33/",
                    "qt3_shots": "",
                    "qt4_shots": "22-1x",
                },
            ],
        }

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 200

        result = response.json()
        assert "game_id" in result
        assert result["message"] == "Game created successfully from scorebook"

        # Verify game was created
        game_response = client.get(f"/v1/games/{result['game_id']}")
        assert game_response.status_code == 200

        game = game_response.json()
        assert game["home_team_id"] == home_team.id
        assert game["away_team_id"] == away_team.id

    def test_create_game_with_empty_quarters(self, client, sample_teams, sample_players):
        """Test creating a game where some players have empty quarters."""
        home_team = sample_teams[0]
        away_team = sample_teams[1]

        game_data = {
            "date": "2024-03-16",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "player_stats": [
                {
                    "player_id": sample_players[0].id,
                    "player_name": sample_players[0].name,
                    "jersey_number": sample_players[0].jersey_number,
                    "team_id": home_team.id,
                    "fouls": 0,
                    "qt1_shots": "",
                    "qt2_shots": "",
                    "qt3_shots": "2",
                    "qt4_shots": "",
                }
            ],
        }

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 200

        result = response.json()
        game_id = result["game_id"]

        # Verify game was created
        game_response = client.get(f"/v1/games/{game_id}")
        assert game_response.status_code == 200

    def test_create_game_invalid_teams(self, client):
        """Test creating a game with invalid team IDs."""
        game_data = {"date": "2024-03-18", "home_team_id": 9999, "away_team_id": 9998, "player_stats": []}

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_create_game_same_teams(self, client, sample_teams):
        """Test creating a game with same home and away teams."""
        team = sample_teams[0]

        game_data = {"date": "2024-03-19", "home_team_id": team.id, "away_team_id": team.id, "player_stats": []}

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()

    def test_create_game_missing_required_fields(self, client):
        """Test creating a game without required fields."""
        # Missing home_team_id
        game_data = {"date": "2024-03-20", "away_team_id": 1, "player_stats": []}

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 400
        assert "Missing required field" in response.json()["detail"]

    def test_create_game_with_all_shot_types(self, client, sample_teams, sample_players):
        """Test creating a game with all shot notation types."""
        home_team = sample_teams[0]
        away_team = sample_teams[1]

        game_data = {
            "date": "2024-03-22",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "player_stats": [
                {
                    "player_id": sample_players[0].id,
                    "player_name": sample_players[0].name,
                    "jersey_number": sample_players[0].jersey_number,
                    "team_id": home_team.id,
                    "fouls": 5,
                    "qt1_shots": "11xx",  # 2 made FT, 2 missed FT
                    "qt2_shots": "22--",  # 2 made 2pt, 2 missed 2pt
                    "qt3_shots": "33//",  # 2 made 3pt, 2 missed 3pt
                    "qt4_shots": "231x-/",  # Mixed shots
                }
            ],
        }

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 200

        result = response.json()
        assert "game_id" in result
