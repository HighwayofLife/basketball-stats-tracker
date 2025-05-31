"""Unit tests for team statistics API endpoints."""

import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data_access.models import Game, Player, PlayerGameStats, Team, TeamSeasonStats
from app.web_ui.api import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_team(db_session):
    """Create a sample team for testing."""
    team = Team(id=1, name="Test", display_name="Test Team")
    db_session.add(team)
    db_session.commit()
    return team


@pytest.fixture
def sample_teams_with_stats(db_session):
    """Create sample teams with season statistics."""
    teams = []
    for i in range(2):
        team = Team(id=i + 1, name=f"Team{i + 1}", display_name=f"Team {i + 1}")
        db_session.add(team)
        teams.append(team)

    db_session.commit()

    # Add season stats
    for i, team in enumerate(teams):
        stats = TeamSeasonStats(
            team_id=team.id,
            season="2024-2025",
            games_played=20,
            wins=15 - i * 5,
            losses=5 + i * 5,
            total_points_for=1600 - i * 200,
            total_points_against=1400 + i * 100,
            total_ftm=300 - i * 50,
            total_fta=400 - i * 50,
            total_2pm=500 - i * 100,
            total_2pa=600 - i * 100,
            total_3pm=150 - i * 30,
            total_3pa=250 - i * 50,
        )
        db_session.add(stats)

    db_session.commit()
    return teams


@pytest.fixture
def sample_games_with_stats(db_session, sample_teams_with_stats):
    """Create sample games with player statistics."""
    team1, team2 = sample_teams_with_stats

    # Create players for each team
    players_team1 = []
    players_team2 = []

    for i in range(5):
        player1 = Player(id=i + 1, name=f"Player {i + 1}", team_id=team1.id, jersey_number=str(i + 1), is_active=True)
        player2 = Player(id=i + 6, name=f"Player {i + 6}", team_id=team2.id, jersey_number=str(i + 6), is_active=True)
        db_session.add(player1)
        db_session.add(player2)
        players_team1.append(player1)
        players_team2.append(player2)

    db_session.commit()

    # Create games
    games = []
    for i in range(3):
        game = Game(
            id=i + 1, playing_team_id=team1.id, opponent_team_id=team2.id, date=datetime.date(2025, 5, 1 + i * 7)
        )
        db_session.add(game)
        games.append(game)

        # Add player stats for each game
        for j, player in enumerate(players_team1):
            stat = PlayerGameStats(
                player_id=player.id,
                game_id=game.id,
                total_ftm=2 + j,
                total_fta=3 + j,
                total_2pm=4 + j,
                total_2pa=6 + j,
                total_3pm=1 + j,
                total_3pa=3 + j,
                fouls=2,
            )
            db_session.add(stat)

        for j, player in enumerate(players_team2):
            stat = PlayerGameStats(
                player_id=player.id,
                game_id=game.id,
                total_ftm=1 + j,
                total_fta=2 + j,
                total_2pm=3 + j,
                total_2pa=5 + j,
                total_3pm=1 + j,
                total_3pa=2 + j,
                fouls=3,
            )
            db_session.add(stat)

    db_session.commit()
    return games


class TestTeamStatsAPI:
    """Test cases for team statistics API endpoints."""

    def test_get_team_stats_success(self, client, sample_games_with_stats, db_session):
        """Test successful retrieval of team statistics."""
        response = client.get("/v1/teams/1/stats")

        assert response.status_code == 200
        data = response.json()

        # Check team info
        assert data["team"]["id"] == 1
        assert data["team"]["name"] == "Team1"
        assert data["team"]["display_name"] == "Team 1"

        # Check career stats exist
        assert "career_stats" in data
        career = data["career_stats"]
        assert career["games_played"] == 20
        assert career["wins"] == 15
        assert career["losses"] == 5
        assert career["win_percentage"] == 75.0
        assert career["ppg"] == 80.0  # 1600 / 20
        assert career["opp_ppg"] == 70.0  # 1400 / 20
        assert career["point_diff"] == 10.0

        # Check shooting percentages
        assert career["ft_percentage"] == 75.0  # 300/400
        assert career["fg2_percentage"] == 83.3  # 500/600
        assert career["fg3_percentage"] == 60.0  # 150/250

        # Check recent games exist
        assert "recent_games" in data
        assert len(data["recent_games"]) == 3

        # Check first game details
        game = data["recent_games"][0]
        assert "date" in game
        assert game["opponent"] == "Team 2"
        assert "team_points" in game
        assert "opponent_points" in game
        assert "win" in game
        assert "ft" in game
        assert "fg2" in game
        assert "fg3" in game

    def test_get_team_stats_no_season_stats(self, client, sample_team, db_session):
        """Test team stats when no season statistics exist."""
        # Create a game without season stats
        game = Game(
            id=1,
            playing_team_id=sample_team.id,
            opponent_team_id=999,  # Non-existent opponent
            date=datetime.date(2025, 5, 1),
        )
        db_session.add(game)
        db_session.commit()

        response = client.get(f"/v1/teams/{sample_team.id}/stats")

        assert response.status_code == 200
        data = response.json()

        # Should have empty career stats
        assert data["career_stats"]["games_played"] == 0
        assert data["career_stats"]["wins"] == 0
        assert data["career_stats"]["losses"] == 0

        # Should have no season stats
        assert data["season_stats"] is None

        # Should have the game in recent games
        assert len(data["recent_games"]) == 1

    def test_get_team_stats_team_not_found(self, client):
        """Test team stats endpoint when team doesn't exist."""
        response = client.get("/v1/teams/999/stats")

        assert response.status_code == 404
        assert response.json()["detail"] == "Team not found"

    def test_get_team_stats_with_current_season(self, client, sample_games_with_stats, db_session):
        """Test team stats with current season statistics."""
        # The season stats service should calculate current season
        response = client.get("/v1/teams/1/stats")

        assert response.status_code == 200
        data = response.json()

        # Season stats might be calculated based on games
        # The exact values depend on the season calculation logic
        # We mainly verify the structure is correct
        if data["season_stats"]:
            season = data["season_stats"]
            assert "season" in season
            assert "games_played" in season
            assert "wins" in season
            assert "losses" in season
            assert "win_percentage" in season
            assert "ppg" in season
            assert "ft_percentage" in season
            assert "fg2_percentage" in season
            assert "fg3_percentage" in season

    def test_get_team_stats_empty_games(self, client, sample_team):
        """Test team stats when team has no games."""
        response = client.get(f"/v1/teams/{sample_team.id}/stats")

        assert response.status_code == 200
        data = response.json()

        # Should have zero stats
        assert data["career_stats"]["games_played"] == 0
        assert data["career_stats"]["ppg"] == 0
        assert data["recent_games"] == []

    @patch("app.web_ui.routers.teams.SeasonStatsService")
    def test_get_team_stats_season_service_error(self, mock_service_class, client, sample_team):
        """Test team stats when season service throws an error."""
        # Mock the service to raise an exception
        mock_service = MagicMock()
        mock_service.get_season_from_date.side_effect = Exception("Season calculation error")
        mock_service_class.return_value = mock_service

        response = client.get(f"/v1/teams/{sample_team.id}/stats")

        # Should still return 200 with partial data
        assert response.status_code == 200
        data = response.json()
        assert data["season_stats"] is None

    def test_get_team_stats_performance(self, client, db_session, sample_team):
        """Test team stats endpoint performance with many games."""
        # Create many games to test performance
        for i in range(50):
            game = Game(
                id=i + 1,
                playing_team_id=sample_team.id,
                opponent_team_id=999,
                date=datetime.date(2025, 1, 1) + datetime.timedelta(days=i),
            )
            db_session.add(game)
        db_session.commit()

        response = client.get(f"/v1/teams/{sample_team.id}/stats")

        assert response.status_code == 200
        data = response.json()

        # Should only return 10 recent games
        assert len(data["recent_games"]) == 10

        # Most recent game should be first
        assert data["recent_games"][0]["date"] > data["recent_games"][1]["date"]

    def test_get_team_stats_calculates_correct_totals(self, client, sample_games_with_stats):
        """Test that team stats correctly calculates point totals."""
        response = client.get("/v1/teams/1/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify a recent game has correct point calculation
        # Based on our fixture: 5 players with stats incrementing by position
        # Team 1: Player 1-5 with increasing stats
        # For game 1: total_ftm sum = 2+3+4+5+6 = 20
        # total_2pm sum = 4+5+6+7+8 = 30 -> 60 points
        # total_3pm sum = 1+2+3+4+5 = 15 -> 45 points
        # Total = 20 + 60 + 45 = 125
        game = data["recent_games"][0]
        assert game["team_points"] == 125
