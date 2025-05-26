"""
Tests for the scorebook API endpoint.
"""

import pytest

from app.web_ui.schemas import PlayerStatsInput


class TestScorebookAPI:
    """Tests for the scorebook game creation API."""

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
        assert result["message"] == "Game created successfully"

        # Verify game was created
        game_response = client.get(f"/v1/games/{result['game_id']}")
        assert game_response.status_code == 200

        game = game_response.json()
        assert game["home_team"]["id"] == home_team.id
        assert game["away_team"]["id"] == away_team.id
        assert game["game_date"] == "2024-03-15"
        assert game["location"] == "Home Arena"
        assert game["notes"] == "Test game"

        # Verify player stats
        assert len(game["player_stats"]) == 2

        # Check first player stats
        player1_stats = next(s for s in game["player_stats"] if s["player"]["id"] == sample_players[0].id)
        assert player1_stats["points"] == 9  # 2 + 2 + 3 + 1 + 1 = 9
        assert player1_stats["field_goals_made"] == 3
        assert player1_stats["field_goals_attempted"] == 4
        assert player1_stats["three_pointers_made"] == 1
        assert player1_stats["three_pointers_attempted"] == 2
        assert player1_stats["free_throws_made"] == 2
        assert player1_stats["free_throws_attempted"] == 2
        assert player1_stats["personal_fouls"] == 2

        # Check quarter stats exist
        assert len(player1_stats["quarter_stats"]) == 4

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

        # Verify game stats
        game_response = client.get(f"/v1/games/{game_id}")
        game = game_response.json()

        player_stats = game["player_stats"][0]
        assert player_stats["points"] == 2
        assert player_stats["field_goals_made"] == 1
        assert player_stats["field_goals_attempted"] == 1

    def test_create_game_duplicate_prevention(self, client, sample_teams, sample_players):
        """Test that duplicate games are prevented."""
        home_team = sample_teams[0]
        away_team = sample_teams[1]

        game_data = {
            "date": "2024-03-17",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "player_stats": [
                {
                    "player_id": sample_players[0].id,
                    "player_name": sample_players[0].name,
                    "jersey_number": sample_players[0].jersey_number,
                    "team_id": home_team.id,
                    "fouls": 1,
                    "qt1_shots": "2",
                    "qt2_shots": "",
                    "qt3_shots": "",
                    "qt4_shots": "",
                }
            ],
        }

        # Create first game
        response1 = client.post("/v1/games/scorebook", json=game_data)
        assert response1.status_code == 200

        # Try to create duplicate
        response2 = client.post("/v1/games/scorebook", json=game_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"].lower()

    def test_create_game_invalid_teams(self, client):
        """Test creating a game with invalid team IDs."""
        game_data = {"date": "2024-03-18", "home_team_id": 9999, "away_team_id": 9998, "player_stats": []}

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_game_same_teams(self, client, sample_teams):
        """Test creating a game with same home and away teams."""
        team = sample_teams[0]

        game_data = {"date": "2024-03-19", "home_team_id": team.id, "away_team_id": team.id, "player_stats": []}

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()

    def test_create_game_no_player_stats(self, client, sample_teams):
        """Test creating a game without player stats."""
        home_team = sample_teams[0]
        away_team = sample_teams[1]

        game_data = {
            "date": "2024-03-20",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "player_stats": [],
        }

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 400
        assert "at least one player" in response.json()["detail"].lower()

    def test_create_game_invalid_player_team(self, client, sample_teams, sample_players):
        """Test creating a game with player on wrong team."""
        home_team = sample_teams[0]
        away_team = sample_teams[1]

        # Use a player from home team but assign to a third team
        game_data = {
            "date": "2024-03-21",
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "player_stats": [
                {
                    "player_id": sample_players[0].id,  # This player is on home_team
                    "player_name": sample_players[0].name,
                    "jersey_number": sample_players[0].jersey_number,
                    "team_id": 9999,  # Invalid team ID
                    "fouls": 0,
                    "qt1_shots": "2",
                    "qt2_shots": "",
                    "qt3_shots": "",
                    "qt4_shots": "",
                }
            ],
        }

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 400
        assert "not in this game" in response.json()["detail"].lower()

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
                    "qt4_shots": "231x-/",  # Mixed: 1 made 2pt, 1 made 3pt, 1 made FT, 1 missed FT, 1 missed 2pt, 1 missed 3pt
                }
            ],
        }

        response = client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 200

        # Verify stats calculation
        result = response.json()
        game_response = client.get(f"/v1/games/{result['game_id']}")
        game = game_response.json()

        player_stats = game["player_stats"][0]
        assert player_stats["points"] == 18  # 2 + 4 + 6 + 6 = 18
        assert player_stats["field_goals_made"] == 5  # 2 + 2 + 1 = 5
        assert player_stats["field_goals_attempted"] == 10  # 4 + 4 + 2 = 10
        assert player_stats["three_pointers_made"] == 3  # 2 + 1 = 3
        assert player_stats["three_pointers_attempted"] == 5  # 2 + 2 + 1 = 5
        assert player_stats["free_throws_made"] == 3  # 2 + 1 = 3
        assert player_stats["free_throws_attempted"] == 5  # 4 + 1 = 5
        assert player_stats["personal_fouls"] == 5

    def test_schema_validation_jersey_number_as_string(self):
        """Test that jersey numbers are properly handled as strings in schemas."""
        # Test PlayerStatsInput
        stats_input = PlayerStatsInput(
            player_id=1,
            player_name="Test Player",
            jersey_number="00",  # String with leading zero
            team_id=1,
            fouls=2,
            qt1_shots="22",
            qt2_shots="",
            qt3_shots="",
            qt4_shots="",
        )
        assert stats_input.jersey_number == "00"

        # Test with single digit
        stats_input2 = PlayerStatsInput(
            player_id=2,
            player_name="Test Player 2",
            jersey_number="5",
            team_id=1,
            fouls=0,
            qt1_shots="",
            qt2_shots="",
            qt3_shots="",
            qt4_shots="",
        )
        assert stats_input2.jersey_number == "5"

        # Test validation with empty jersey number should fail
        with pytest.raises(ValueError):
            PlayerStatsInput(
                player_id=3,
                player_name="Test Player 3",
                jersey_number="",  # Empty string should fail
                team_id=1,
                fouls=0,
                qt1_shots="",
                qt2_shots="",
                qt3_shots="",
                qt4_shots="",
            )
