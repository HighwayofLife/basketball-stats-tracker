"""
Integration tests for the scorebook API workflows.
"""

import pytest

from app.data_access.models import Player, Team


@pytest.mark.integration
class TestScorebookAPI:
    """Tests for the scorebook game creation API."""

    @pytest.fixture(scope="class")
    def sample_teams(self, integration_db_session):
        """Create sample teams in the database."""
        import time
        import uuid

        unique_suffix = f"{int(time.time())}_{str(uuid.uuid4())[:8]}"

        team1 = Team(name=f"ScorebookLakers_{unique_suffix}", display_name=f"Scorebook Lakers {unique_suffix}")
        team2 = Team(name=f"ScorebookWarriors_{unique_suffix}", display_name=f"Scorebook Warriors {unique_suffix}")
        integration_db_session.add_all([team1, team2])
        integration_db_session.commit()
        integration_db_session.refresh(team1)
        integration_db_session.refresh(team2)
        return [team1, team2]

    @pytest.fixture(scope="class")
    def sample_players(self, integration_db_session, sample_teams):
        """Create sample players in the database."""
        import hashlib
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        hash_suffix = int(hashlib.md5(unique_suffix.encode()).hexdigest()[:4], 16)

        lakers, warriors = sample_teams

        players = [
            Player(
                name=f"Scorebook LeBron {unique_suffix}",
                team_id=lakers.id,
                jersey_number=str(23 + hash_suffix % 50),
                position="SF",
                is_active=True,
            ),
            Player(
                name=f"Scorebook Anthony {unique_suffix}",
                team_id=lakers.id,
                jersey_number=str(3 + hash_suffix % 50),
                position="PF",
                is_active=True,
            ),
            Player(
                name=f"Scorebook Stephen {unique_suffix}",
                team_id=warriors.id,
                jersey_number=str(30 + hash_suffix % 50),
                position="PG",
                is_active=True,
            ),
            Player(
                name=f"Scorebook Klay {unique_suffix}",
                team_id=warriors.id,
                jersey_number=str(11 + hash_suffix % 50),
                position="SG",
                is_active=True,
            ),
        ]

        integration_db_session.add_all(players)
        integration_db_session.commit()
        for player in players:
            integration_db_session.refresh(player)
        return players

    def test_create_scorebook_game_success(self, authenticated_client, sample_teams, sample_players):
        """Test creating a scorebook game with valid data."""
        lakers, warriors = sample_teams
        lebron, anthony, curry, klay = sample_players

        import time

        unique_date_suffix = int(time.time()) % 10000  # Use timestamp for unique date
        game_date = f"2024-{(unique_date_suffix % 12) + 1:02d}-{(unique_date_suffix % 28) + 1:02d}"

        game_data = {
            "date": game_date,
            "home_team_id": lakers.id,
            "away_team_id": warriors.id,
            "location": "Test Arena",
            "player_stats": [
                {
                    "player_id": lebron.id,
                    "fouls": 2,
                    "qt1_shots": "22-1x",
                    "qt2_shots": "",
                    "qt3_shots": "",
                    "qt4_shots": "",
                },
                {
                    "player_id": curry.id,
                    "fouls": 1,
                    "qt1_shots": "33-",
                    "qt2_shots": "",
                    "qt3_shots": "",
                    "qt4_shots": "",
                },
            ],
        }

        response = authenticated_client.post("/v1/games/scorebook", json=game_data)

        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert isinstance(data["game_id"], int)
        assert "message" in data
        assert "home_team" in data
        assert "away_team" in data

    def test_update_scorebook_game_missing_fields(self, authenticated_client):
        """Test updating a scorebook game with missing required fields."""
        import time

        unique_date_suffix = int(time.time()) % 10000
        game_date = f"2024-{(unique_date_suffix % 12) + 1:02d}-{(unique_date_suffix % 28) + 1:02d}"

        game_data = {
            "date": game_date,
            # Missing home_team_id, away_team_id, and player_stats
        }

        response = authenticated_client.post("/v1/games/scorebook", json=game_data)

        assert response.status_code in [400, 422]  # Validation error

    def test_update_scorebook_game_invalid_teams(self, authenticated_client):
        """Test updating a scorebook game with non-existent teams."""
        import time

        unique_date_suffix = int(time.time()) % 10000
        game_date = f"2024-{(unique_date_suffix % 12) + 1:02d}-{(unique_date_suffix % 28) + 1:02d}"

        game_data = {
            "date": game_date,
            "home_team_id": 99999,  # Non-existent team
            "away_team_id": 88888,  # Non-existent team
            "location": "Test Arena",
            "player_stats": [],
        }

        response = authenticated_client.post("/v1/games/scorebook", json=game_data)

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_import_scorebook_game_with_comprehensive_stats(self, authenticated_client, sample_players, sample_teams):
        """Test importing a scorebook game with comprehensive player statistics."""
        lakers, warriors = sample_teams
        lebron, anthony, curry, klay = sample_players

        import time

        # Create a unique date based on team IDs and timestamp to avoid conflicts
        unique_date_suffix = (int(time.time()) + lakers.id + warriors.id) % 10000
        game_date = f"2024-{(unique_date_suffix % 12) + 1:02d}-{(unique_date_suffix % 28) + 1:02d}"

        game_data = {
            "date": game_date,
            "home_team_id": lakers.id,
            "away_team_id": warriors.id,
            "location": "Crypto.com Arena",
            "player_stats": [
                {
                    "player_id": lebron.id,
                    "fouls": 3,
                    "qt1_shots": "22-1x",
                    "qt2_shots": "33-",
                    "qt3_shots": "22-",
                    "qt4_shots": "1x",
                },
                {
                    "player_id": anthony.id,
                    "fouls": 2,
                    "qt1_shots": "22-",
                    "qt2_shots": "",
                    "qt3_shots": "22-1x",
                    "qt4_shots": "",
                },
                {
                    "player_id": curry.id,
                    "fouls": 1,
                    "qt1_shots": "333-",
                    "qt2_shots": "22-",
                    "qt3_shots": "",
                    "qt4_shots": "33-",
                },
                {
                    "player_id": klay.id,
                    "fouls": 0,
                    "qt1_shots": "33-",
                    "qt2_shots": "22-",
                    "qt3_shots": "",
                    "qt4_shots": "",
                },
            ],
        }

        response = authenticated_client.post("/v1/games/scorebook", json=game_data)

        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert "home_score" in data
        assert "away_score" in data
