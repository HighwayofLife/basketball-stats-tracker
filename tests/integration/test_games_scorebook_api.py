"""Integration tests for games scorebook API endpoints."""

from datetime import date

from app.auth.models import User, UserRole
from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team


class TestScoreboardFormatEndpoint:
    """Test the scorebook format endpoint."""

    def test_get_game_scorebook_format_success(self, authenticated_client, integration_db_session):
        """Test successful retrieval of game in scorebook format."""
        # Create test data with unique names
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        team1 = Team(name=f"ScorbookHomeTeam_{unique_suffix}", display_name=f"Scorebook Home Team {unique_suffix}")
        team2 = Team(name=f"ScorbookAwayTeam_{unique_suffix}", display_name=f"Scorebook Away Team {unique_suffix}")
        integration_db_session.add_all([team1, team2])
        integration_db_session.flush()

        game = Game(
            date=date(2025, 1, 15),
            playing_team_id=team1.id,
            opponent_team_id=team2.id,
            location="Test Court",
            notes="Test game",
        )
        integration_db_session.add(game)
        integration_db_session.flush()

        player1 = Player(name="Scorebook Player 1", jersey_number="10", team_id=team1.id, is_active=True)
        player2 = Player(name="Scorebook Player 2", jersey_number="20", team_id=team2.id, is_active=True)
        integration_db_session.add_all([player1, player2])
        integration_db_session.flush()

        # Create player game stats
        pgs1 = PlayerGameStats(
            game_id=game.id,
            player_id=player1.id,
            total_ftm=2,
            total_fta=3,
            total_2pm=4,
            total_2pa=6,
            total_3pm=1,
            total_3pa=2,
            fouls=2,
        )
        integration_db_session.add(pgs1)
        integration_db_session.flush()

        # Create quarter stats
        qs1 = PlayerQuarterStats(
            player_game_stat_id=pgs1.id, quarter_number=1, ftm=1, fta=2, fg2m=2, fg2a=3, fg3m=0, fg3a=1
        )
        integration_db_session.add(qs1)
        integration_db_session.commit()

        # Test the endpoint
        response = authenticated_client.get(f"/v1/games/{game.id}/scorebook-format")
        assert response.status_code == 200

        data = response.json()
        assert data["game_info"]["id"] == game.id
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

    def test_get_game_scorebook_format_not_found(self, authenticated_client):
        """Test retrieval of non-existent game."""
        response = authenticated_client.get("/v1/games/999999/scorebook-format")
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_get_game_scorebook_format_unauthorized(self, unauthenticated_client):
        """Test endpoint without authentication."""
        response = unauthenticated_client.get("/v1/games/1/scorebook-format")
        assert response.status_code == 401

    def test_get_game_scorebook_format_access_denied(self, unauthenticated_client, integration_db_session):
        """Test access control for non-admin user."""
        from fastapi.testclient import TestClient

        from app.auth.dependencies import get_current_user
        from app.web_ui.api import app

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

        with TestClient(app) as test_client:
            # Create test data
            import uuid

            unique_suffix = str(uuid.uuid4())[:8]
            team1 = Team(
                name=f"ScoreAccess Home Team {unique_suffix}", display_name=f"Score Access Home Team {unique_suffix}"
            )
            team2 = Team(
                name=f"ScoreAccess Away Team {unique_suffix}", display_name=f"Score Access Away Team {unique_suffix}"
            )
            integration_db_session.add_all([team1, team2])
            integration_db_session.flush()

            game = Game(date=date(2025, 1, 15), playing_team_id=team1.id, opponent_team_id=team2.id)
            integration_db_session.add(game)
            integration_db_session.commit()

            response = test_client.get(f"/v1/games/{game.id}/scorebook-format")
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]

        # Clear the override
        app.dependency_overrides.clear()
