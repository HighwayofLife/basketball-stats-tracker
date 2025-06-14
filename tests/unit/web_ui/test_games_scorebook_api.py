"""Unit tests for games scorebook API endpoints."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.auth.models import User, UserRole
from app.data_access.models import Base, Game, Player, PlayerGameStats, PlayerQuarterStats, Team
from app.web_ui.api import app


class TestScoreboardFormatEndpoint:
    """Test the scorebook format endpoint."""

    @pytest.fixture
    def test_db_file(self, tmp_path):
        """Create a temporary database file for testing."""
        # Create a temporary file for the database
        db_file = tmp_path / "test.db"
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
    def client(self, db_session, test_db_engine):
        """Create a test client with proper database dependency override."""
        from sqlalchemy.orm import sessionmaker

        from app.auth.dependencies import get_current_user
        from app.dependencies import get_db

        # Commit data so it's visible to other sessions
        db_session.commit()

        # Create sessionmaker for the dependency override
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)

        def override_get_db():
            session = SessionLocal()
            try:
                yield session
            finally:
                session.close()

        # Mock authenticated user
        def mock_current_user():
            user = User(
                id=1,
                username="testuser",
                email="test@example.com",
                role=UserRole.ADMIN,
                is_active=True,
                provider="local",
            )
            user.teams = []
            return user

        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = mock_current_user

        try:
            with TestClient(app) as client:
                yield client
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def test_get_game_scorebook_format_success(self, client, db_session):
        """Test successful retrieval of game in scorebook format."""
        # Create test data
        team1 = Team(id=1, name="Home Team")
        team2 = Team(id=2, name="Away Team")
        db_session.add_all([team1, team2])
        db_session.flush()

        game = Game(
            id=1,
            date=date(2025, 1, 15),
            playing_team_id=1,
            opponent_team_id=2,
            location="Test Court",
            notes="Test game",
        )
        db_session.add(game)
        db_session.flush()

        player1 = Player(id=1, name="Player 1", jersey_number="10", team_id=1)
        player2 = Player(id=2, name="Player 2", jersey_number="20", team_id=2)
        db_session.add_all([player1, player2])
        db_session.flush()

        # Create player game stats
        pgs1 = PlayerGameStats(
            game_id=1,
            player_id=1,
            total_ftm=2,
            total_fta=3,
            total_2pm=4,
            total_2pa=6,
            total_3pm=1,
            total_3pa=2,
            fouls=2,
        )
        db_session.add(pgs1)
        db_session.flush()

        # Create quarter stats
        qs1 = PlayerQuarterStats(
            player_game_stat_id=pgs1.id, quarter_number=1, ftm=1, fta=2, fg2m=2, fg2a=3, fg3m=0, fg3a=1
        )
        db_session.add(qs1)
        db_session.commit()

        # Test the endpoint
        response = client.get("/v1/games/1/scorebook-format")
        assert response.status_code == 200

        data = response.json()
        assert data["game_info"]["id"] == 1
        # Verify date format is correct (YYYY-MM-DD)
        import re

        assert re.match(r"^\d{4}-\d{2}-\d{2}$", data["game_info"]["date"])
        # Verify team IDs are present and different
        assert isinstance(data["game_info"]["home_team_id"], int)
        assert isinstance(data["game_info"]["away_team_id"], int)
        assert data["game_info"]["home_team_id"] != data["game_info"]["away_team_id"]
        # Basic structure validation
        assert "location" in data["game_info"]
        assert "notes" in data["game_info"]

        # Verify player stats structure
        assert len(data["player_stats"]) >= 1
        player_stat = data["player_stats"][0]
        assert "player_id" in player_stat
        assert "player_name" in player_stat
        assert "jersey_number" in player_stat
        assert "team" in player_stat
        assert "fouls" in player_stat
        assert "shots_q1" in player_stat
        # Verify shot notation format
        assert isinstance(player_stat["shots_q1"], str)

    def test_get_game_scorebook_format_not_found(self, client):
        """Test retrieval of non-existent game."""
        response = client.get("/v1/games/999/scorebook-format")
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_get_game_scorebook_format_unauthorized(self, db_session):
        """Test endpoint without authentication."""
        # Create client without auth override
        client = TestClient(app)

        response = client.get("/v1/games/1/scorebook-format")
        assert response.status_code == 401

    def test_get_game_scorebook_format_access_denied(self, client, db_session):
        """Test access control for non-admin user."""
        from app.auth.dependencies import get_current_user

        # Mock non-admin user without team access
        def mock_regular_user():
            user = User(
                id=2,
                username="regularuser",
                email="regular@example.com",
                role=UserRole.USER,
                is_active=True,
                provider="local",
            )
            user.teams = []  # No team access
            return user

        app.dependency_overrides[get_current_user] = mock_regular_user

        # Create test data
        team1 = Team(id=1, name="Home Team")
        team2 = Team(id=2, name="Away Team")
        db_session.add_all([team1, team2])
        db_session.flush()

        game = Game(id=1, date=date(2025, 1, 15), playing_team_id=1, opponent_team_id=2)
        db_session.add(game)
        db_session.commit()

        response = client.get("/v1/games/1/scorebook-format")
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
