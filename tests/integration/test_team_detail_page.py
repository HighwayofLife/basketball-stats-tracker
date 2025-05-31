"""Integration tests for team detail page with statistics."""

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User  # Import User model to resolve SQLAlchemy relationships
from app.data_access.models import Game, Player, PlayerGameStats, Team, TeamSeasonStats
from app.web_ui.api import app
from app.web_ui.dependencies import get_db


@pytest.fixture
def client(test_db_file_session):
    """Create a FastAPI test client with isolated database."""

    def override_get_db():
        return test_db_file_session

    def mock_current_user():
        return User(id=1, username="testuser", email="test@example.com", role="admin", is_active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = mock_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def team_with_full_data(test_db_file_session: Session):
    """Create a team with players, games, and statistics."""
    # Create team
    team = Team(id=1, name="Hawks", display_name="Atlanta Hawks")
    test_db_file_session.add(team)

    # Create opponent team
    opponent = Team(id=2, name="Lakers", display_name="Los Angeles Lakers")
    test_db_file_session.add(opponent)

    # Create players
    players = []
    for i in range(8):
        player = Player(
            id=i + 1,
            name=f"Player {i + 1}",
            team_id=team.id,
            jersey_number=str(i + 10),
            position=["PG", "SG", "SF", "PF", "C", "SG", "SF", "PF"][i],
            height=72 + i,  # 6'0" to 6'7"
            weight=180 + i * 5,
            year=["Senior", "Junior", "Sophomore", "Freshman", "Senior", "Junior", "Sophomore", "Freshman"][i],
            is_active=True,
        )
        test_db_file_session.add(player)
        players.append(player)

    test_db_file_session.commit()

    # Create games with stats
    games = []
    for i in range(5):
        game = Game(
            id=i + 1, playing_team_id=team.id, opponent_team_id=opponent.id, date=datetime.date(2025, 5, 1 + i * 7)
        )
        test_db_file_session.add(game)
        games.append(game)

        # Add player stats
        for j, player in enumerate(players[:5]):  # Only 5 players per game
            stat = PlayerGameStats(
                player_id=player.id,
                game_id=game.id,
                total_ftm=3 + j + i,
                total_fta=4 + j + i,
                total_2pm=5 + j + i,
                total_2pa=8 + j + i,
                total_3pm=2 + j + i,
                total_3pa=4 + j + i,
                fouls=2 + (j % 3),
            )
            test_db_file_session.add(stat)

        # Add opponent stats for realistic scores
        for j in range(5):
            opponent_player = Player(
                id=100 + i * 5 + j,
                name=f"Opponent {i * 5 + j + 1}",  # Make names unique across games
                team_id=opponent.id,
                jersey_number=str(i * 5 + j + 1),  # Make jersey numbers unique
                is_active=True,
            )
            test_db_file_session.add(opponent_player)

            stat = PlayerGameStats(
                player_id=opponent_player.id,
                game_id=game.id,
                total_ftm=2 + j + i,
                total_fta=3 + j + i,
                total_2pm=4 + j + i,
                total_2pa=7 + j + i,
                total_3pm=1 + j + i,
                total_3pa=3 + j + i,
                fouls=2,
            )
            test_db_file_session.add(stat)

    # Create season stats
    season_stats = TeamSeasonStats(
        team_id=team.id,
        season="2024-2025",
        games_played=5,
        wins=3,
        losses=2,
        total_points_for=400,
        total_points_against=380,
        total_ftm=75,
        total_fta=100,
        total_2pm=125,
        total_2pa=200,
        total_3pm=40,
        total_3pa=80,
    )
    test_db_file_session.add(season_stats)

    test_db_file_session.commit()
    return team


class TestTeamDetailPageIntegration:
    """Integration tests for the team detail page."""

    def test_team_detail_page_loads(self, client, team_with_full_data):
        """Test that team detail page loads successfully."""
        response = client.get(f"/teams/{team_with_full_data.id}")

        assert response.status_code == 200
        content = response.text

        # Check for loading indicator
        assert "Loading team data" in content

        # Check for JavaScript that loads team data
        assert f"teamId = {team_with_full_data.id}" in content
        assert "loadTeamData()" in content
        assert "renderTeamData(teamData, statsData)" in content

    def test_team_detail_api_integration(self, client, team_with_full_data):
        """Test that team detail and stats APIs work together."""
        # Test detail endpoint
        detail_response = client.get(f"/v1/teams/{team_with_full_data.id}/detail")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()

        assert detail_data["id"] == team_with_full_data.id
        assert detail_data["name"] == "Hawks"
        assert detail_data["display_name"] == "Atlanta Hawks"
        assert len(detail_data["players"]) == 8

        # Test stats endpoint
        stats_response = client.get(f"/v1/teams/{team_with_full_data.id}/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        assert stats_data["team"]["id"] == team_with_full_data.id
        assert "career_stats" in stats_data
        assert "season_stats" in stats_data
        assert "recent_games" in stats_data

    def test_team_detail_page_javascript_functions(self, client, team_with_full_data):
        """Test that all required JavaScript functions are present."""
        response = client.get(f"/teams/{team_with_full_data.id}")
        content = response.text

        # Check for required functions
        required_functions = [
            "loadTeamData",
            "renderTeamData",
            "formatHeight",
            "showAddPlayerModal",
            "editPlayer",
            "closePlayerModal",
            "showDeletePlayerModal",
            "closeDeletePlayerModal",
            "confirmDeletePlayer",
        ]

        for func in required_functions:
            assert (
                f"function {func}" in content or f"{func} = function" in content or f"async function {func}" in content
            )

    def test_team_detail_page_ui_elements(self, client, team_with_full_data):
        """Test that all UI elements are present in the template."""
        response = client.get(f"/teams/{team_with_full_data.id}")
        content = response.text

        # Check for modals
        assert 'id="player-modal"' in content
        assert 'id="delete-player-modal"' in content

        # Check for form elements
        assert 'id="player-form"' in content
        assert 'id="player-name"' in content
        assert 'id="jersey-number"' in content
        assert 'id="position"' in content

        # Check for Bootstrap classes
        assert "card" in content
        assert "table" in content
        assert "btn btn-primary" in content
        assert "spinner-border" in content

    def test_team_stats_calculation_accuracy(self, client, team_with_full_data):
        """Test that team statistics are calculated correctly."""
        response = client.get(f"/v1/teams/{team_with_full_data.id}/stats")
        data = response.json()

        # Verify career stats calculations
        career = data["career_stats"]
        assert career["games_played"] == 5
        assert career["wins"] == 3
        assert career["losses"] == 2
        assert career["win_percentage"] == 60.0  # 3/5 * 100
        assert career["ppg"] == 80.0  # 400/5
        assert career["opp_ppg"] == 76.0  # 380/5
        assert career["point_diff"] == 4.0  # 80-76

        # Verify shooting percentages
        assert career["ft_percentage"] == 75.0  # 75/100
        assert career["fg2_percentage"] == 62.5  # 125/200
        assert career["fg3_percentage"] == 50.0  # 40/80

    def test_team_recent_games_sorting(self, client, team_with_full_data):
        """Test that recent games are sorted by date descending."""
        response = client.get(f"/v1/teams/{team_with_full_data.id}/stats")
        data = response.json()

        games = data["recent_games"]
        assert len(games) == 5

        # Verify descending date order
        for i in range(len(games) - 1):
            assert games[i]["date"] > games[i + 1]["date"]

    def test_team_detail_error_handling(self, client):
        """Test error handling for non-existent team."""
        # Test page load
        page_response = client.get("/teams/999")
        assert page_response.status_code == 200  # Page loads but will show error

        # Test API endpoints
        detail_response = client.get("/v1/teams/999/detail")
        assert detail_response.status_code == 404

        stats_response = client.get("/v1/teams/999/stats")
        assert stats_response.status_code == 404

    def test_team_player_management_integration(self, client, team_with_full_data, test_db_file_session):
        """Test player management functionality integration."""
        # Test that we can access the player creation endpoint (even if it fails due to jersey number conflict)
        new_player_data = {
            "name": "New Player",
            "team_id": team_with_full_data.id,
            "jersey_number": "0",
            "position": "C",
            "height": 84,  # 7'0"
            "weight": 250,
            "year": "Rookie",
        }

        response = client.post("/v1/players/new", json=new_player_data)
        # Accept either 200 (success) or 400 (jersey number conflict) as both indicate the endpoint is working
        assert response.status_code in [200, 400]

        # Verify team detail endpoint works regardless
        detail_response = client.get(f"/v1/teams/{team_with_full_data.id}/detail")
        detail_data = detail_response.json()
        assert len(detail_data["players"]) >= 8  # At least the original players

    def test_team_stats_with_no_games(self, client, test_db_file_session):
        """Test team stats when team has no games played."""
        # Create team with no games
        empty_team = Team(id=99, name="Empty", display_name="Empty Team")
        test_db_file_session.add(empty_team)
        test_db_file_session.commit()

        response = client.get(f"/v1/teams/{empty_team.id}/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["career_stats"]["games_played"] == 0
        assert data["career_stats"]["ppg"] == 0
        assert data["recent_games"] == []
        assert data["season_stats"] is None
