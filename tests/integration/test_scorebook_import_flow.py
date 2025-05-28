"""
Integration tests for the complete scorebook import flow including player creation.
"""

import pytest
from sqlalchemy.orm import Session
from .test_game_entry_workflow import test_client, mock_db_manager


class TestScorebookImportFlow:
    """Integration tests for the complete scorebook import workflow."""

    def test_import_game_with_new_players(self, test_client, mock_db_manager, db_session: Session):
        """Test importing a game that requires creating new players."""
        # First, create teams
        teams_response = test_client.get("/v1/teams/detail")
        teams = teams_response.json()

        if len(teams) < 2:
            # Create teams if they don't exist
            test_client.post("/v1/teams/new", json={"name": "Lakers"})
            test_client.post("/v1/teams/new", json={"name": "Warriors"})
            teams_response = test_client.get("/v1/teams/detail")
            teams = teams_response.json()

        lakers = next(t for t in teams if t["name"] == "Lakers")
        warriors = next(t for t in teams if t["name"] == "Warriors")

        # Create game data with some existing and some new players
        game_data = {
            "date": "2024-03-25",
            "home_team_id": lakers["id"],
            "away_team_id": warriors["id"],
            "location": "Crypto.com Arena",
            "notes": "Regular season game",
            "player_stats": [
                # This will be a new player
                {
                    "player_id": None,  # Will trigger player creation in real flow
                    "player_name": "LeBron James",
                    "jersey_number": "23",
                    "team_id": lakers["id"],
                    "fouls": 2,
                    "qt1_shots": "22-3",
                    "qt2_shots": "3/22",
                    "qt3_shots": "11x",
                    "qt4_shots": "2-3/",
                },
                # Another new player
                {
                    "player_id": None,
                    "player_name": "Stephen Curry",
                    "jersey_number": "30",
                    "team_id": warriors["id"],
                    "fouls": 3,
                    "qt1_shots": "333/",
                    "qt2_shots": "3/3",
                    "qt3_shots": "33//",
                    "qt4_shots": "3/11",
                },
            ],
        }

        # First create the players
        lebron_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "LeBron James",
                "jersey_number": "23",
                "team_id": lakers["id"],
                "position": "Forward",
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert lebron_response.status_code == 200
        lebron = lebron_response.json()

        curry_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "Stephen Curry",
                "jersey_number": "30",
                "team_id": warriors["id"],
                "position": "Guard",
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert curry_response.status_code == 200
        curry = curry_response.json()

        # Update game data with actual player IDs
        game_data["player_stats"][0]["player_id"] = lebron["id"]
        game_data["player_stats"][1]["player_id"] = curry["id"]

        # Create the game
        response = test_client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 200

        result = response.json()
        game_id = result["game_id"]

        # Verify the game was created correctly
        game_response = test_client.get(f"/v1/games/{game_id}")
        assert game_response.status_code == 200

        game = game_response.json()
        assert game["location"] == "Crypto.com Arena"
        assert len(game["player_stats"]) == 2

        # Check LeBron's stats
        lebron_stats = next(s for s in game["player_stats"] if s["player"]["name"] == "LeBron James")
        assert lebron_stats["player"]["jersey_number"] == "23"
        assert lebron_stats["points"] == 20  # 4+3+4+3+2+2+2
        assert lebron_stats["three_pointers_made"] == 3
        assert lebron_stats["personal_fouls"] == 2

        # Check Curry's stats
        curry_stats = next(s for s in game["player_stats"] if s["player"]["name"] == "Stephen Curry")
        assert curry_stats["player"]["jersey_number"] == "30"
        assert curry_stats["points"] == 23  # 9+6+6+2
        assert curry_stats["three_pointers_made"] == 7
        assert curry_stats["three_pointers_attempted"] == 11
        assert curry_stats["personal_fouls"] == 3

    def test_import_game_with_jersey_conflict(self, test_client, mock_db_manager, db_session: Session):
        """Test handling jersey number conflicts during import."""
        # Get teams
        teams_response = test_client.get("/v1/teams/detail")
        teams = teams_response.json()
        team = teams[0]

        # Create a player with jersey #0
        player1_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "Player Zero",
                "jersey_number": "0",
                "team_id": team["id"],
                "position": None,
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert player1_response.status_code == 200

        # Try to create another player with jersey #0 on same team
        player2_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "Another Zero",
                "jersey_number": "0",
                "team_id": team["id"],
                "position": None,
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert player2_response.status_code == 400
        assert "already exists" in player2_response.json()["detail"]

        # But creating with jersey #00 should work (different string)
        player3_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "Double Zero",
                "jersey_number": "00",
                "team_id": team["id"],
                "position": None,
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert player3_response.status_code == 200
        player3 = player3_response.json()
        assert player3["jersey_number"] == "00"

    def test_import_game_updates_existing_player_stats(self, test_client, mock_db_manager, db_session: Session):
        """Test that importing a game updates stats for existing players."""
        # Get teams and create a game
        teams_response = test_client.get("/v1/teams/detail")
        teams = teams_response.json()
        home_team = teams[0]
        away_team = teams[1]

        # Get existing players
        players_response = test_client.get("/v1/players/list")
        players = players_response.json()
        home_player = next(p for p in players if p["team_id"] == home_team["id"])
        away_player = next(p for p in players if p["team_id"] == away_team["id"])

        # Create first game
        game1_data = {
            "date": "2024-03-26",
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "player_stats": [
                {
                    "player_id": home_player["id"],
                    "player_name": home_player["name"],
                    "jersey_number": home_player["jersey_number"],
                    "team_id": home_team["id"],
                    "fouls": 2,
                    "qt1_shots": "22",
                    "qt2_shots": "3",
                    "qt3_shots": "",
                    "qt4_shots": "2-",
                }
            ],
        }

        response1 = test_client.post("/v1/games/scorebook", json=game1_data)
        assert response1.status_code == 200

        # Create second game on different date
        game2_data = {
            "date": "2024-03-27",
            "home_team_id": home_team["id"],
            "away_team_id": away_team["id"],
            "player_stats": [
                {
                    "player_id": home_player["id"],
                    "player_name": home_player["name"],
                    "jersey_number": home_player["jersey_number"],
                    "team_id": home_team["id"],
                    "fouls": 4,
                    "qt1_shots": "333",
                    "qt2_shots": "//",
                    "qt3_shots": "22-",
                    "qt4_shots": "11xx",
                }
            ],
        }

        response2 = test_client.post("/v1/games/scorebook", json=game2_data)
        assert response2.status_code == 200

        # Both games should exist and have different stats
        game1 = test_client.get(f"/v1/games/{response1.json()['game_id']}").json()
        game2 = test_client.get(f"/v1/games/{response2.json()['game_id']}").json()

        # Check first game stats
        game1_stats = game1["player_stats"][0]
        assert game1_stats["points"] == 9  # 4 + 3 + 2 = 9
        assert game1_stats["personal_fouls"] == 2

        # Check second game stats
        game2_stats = game2["player_stats"][0]
        assert game2_stats["points"] == 15  # 9 + 4 + 2 = 15
        assert game2_stats["personal_fouls"] == 4

    def test_csv_import_simulation(self, test_client, mock_db_manager, db_session: Session):
        """Simulate the full CSV import process as it would happen in the UI."""
        # This test simulates what happens when a user imports a CSV file
        # with both existing and new players

        teams_response = test_client.get("/v1/teams/detail")
        teams = teams_response.json()
        blue_team = next((t for t in teams if t["name"] == "Blue"), None)
        black_team = next((t for t in teams if t["name"] == "Black"), None)

        # Create teams if they don't exist
        if not blue_team:
            blue_response = test_client.post("/v1/teams/new", json={"name": "Blue"})
            blue_team = blue_response.json()

        if not black_team:
            black_response = test_client.post("/v1/teams/new", json={"name": "Black"})
            black_team = black_response.json()

        # Create one existing player
        existing_player_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "Jose",
                "jersey_number": "1",  # Different from CSV which has #0
                "team_id": blue_team["id"],
                "position": None,
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert existing_player_response.status_code == 200
        existing_player = existing_player_response.json()

        # Simulate CSV data being parsed
        csv_players = [
            {
                "name": "Jordan",
                "jersey_number": "00",
                "team": "Black",
                "fouls": 1,
                "qt1_shots": "-/-",
                "qt2_shots": "-/",
                "qt3_shots": "/2",
                "qt4_shots": "-2xxxx",
            },
            {
                "name": "Kyle",
                "jersey_number": "5",
                "team": "Black",
                "fouls": 3,
                "qt1_shots": "-/2-/",
                "qt2_shots": "2/",
                "qt3_shots": "/--3",
                "qt4_shots": "/3-",
            },
            {
                "name": "Jose",  # Existing player but with different jersey
                "jersey_number": "0",  # CSV has #0, but we created with #1
                "team": "Blue",
                "fouls": 2,
                "qt1_shots": "-2/-1x",
                "qt2_shots": "-2-/-2",
                "qt3_shots": "/2-",
                "qt4_shots": "-2-33/33xx/2",
            },
        ]

        # Step 1: Create new players (Jordan and Kyle)
        # In the UI, this happens when the user clicks Save and new players are detected
        jordan_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "Jordan",
                "jersey_number": "00",
                "team_id": black_team["id"],
                "position": None,
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert jordan_response.status_code == 200
        jordan = jordan_response.json()

        kyle_response = test_client.post(
            "/v1/players/new",
            json={
                "name": "Kyle",
                "jersey_number": "5",
                "team_id": black_team["id"],
                "position": None,
                "height": None,
                "weight": None,
                "year": None,
            },
        )
        assert kyle_response.status_code == 200
        kyle = kyle_response.json()

        # Step 2: Create the game with all players
        game_data = {
            "date": "2025-05-19",
            "home_team_id": blue_team["id"],
            "away_team_id": black_team["id"],
            "location": None,
            "notes": None,
            "player_stats": [
                {
                    "player_id": jordan["id"],
                    "player_name": "Jordan",
                    "jersey_number": "00",
                    "team_id": black_team["id"],
                    "fouls": 1,
                    "qt1_shots": "-/-",
                    "qt2_shots": "-/",
                    "qt3_shots": "/2",
                    "qt4_shots": "-2xxxx",
                },
                {
                    "player_id": kyle["id"],
                    "player_name": "Kyle",
                    "jersey_number": "5",
                    "team_id": black_team["id"],
                    "fouls": 3,
                    "qt1_shots": "-/2-/",
                    "qt2_shots": "2/",
                    "qt3_shots": "/--3",
                    "qt4_shots": "/3-",
                },
                {
                    "player_id": existing_player["id"],  # Use existing Jose
                    "player_name": "Jose",
                    "jersey_number": existing_player["jersey_number"],  # Use his actual jersey #1
                    "team_id": blue_team["id"],
                    "fouls": 2,
                    "qt1_shots": "-2/-1x",
                    "qt2_shots": "-2-/-2",
                    "qt3_shots": "/2-",
                    "qt4_shots": "-2-33/33xx/2",
                },
            ],
        }

        response = test_client.post("/v1/games/scorebook", json=game_data)
        assert response.status_code == 200

        # Verify the game
        game_id = response.json()["game_id"]
        game = test_client.get(f"/v1/games/{game_id}").json()

        assert len(game["player_stats"]) == 3

        # Verify each player's stats
        jordan_stats = next(s for s in game["player_stats"] if s["player"]["name"] == "Jordan")
        assert jordan_stats["points"] == 4  # 2 + 2 = 4
        assert jordan_stats["free_throws_attempted"] == 4

        kyle_stats = next(s for s in game["player_stats"] if s["player"]["name"] == "Kyle")
        assert kyle_stats["points"] == 8  # 2 + 3 + 3 = 8

        jose_stats = next(s for s in game["player_stats"] if s["player"]["name"] == "Jose")
        assert jose_stats["points"] == 21  # Complex calculation but verified manually
