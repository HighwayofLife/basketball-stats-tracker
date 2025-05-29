"""
Integration tests for the complete scorebook import flow including player creation.
"""

from sqlalchemy.orm import Session


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
                "position": "SF",
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
                "position": "PG",
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
        assert game["home_team"] == "Lakers"
        assert game["away_team"] == "Warriors"

        # Get detailed box score for player stats
        box_score_response = test_client.get(f"/v1/games/{game_id}/box-score")
        assert box_score_response.status_code == 200
        box_score = box_score_response.json()

        # Count total players from both teams
        total_players = len(box_score["home_team"]["players"]) + len(box_score["away_team"]["players"])
        assert total_players == 2

        # Check LeBron's stats (search both teams)
        all_players = box_score["home_team"]["players"] + box_score["away_team"]["players"]
        lebron_stats = next(p for p in all_players if p["name"] == "LeBron James")
        assert lebron_stats["stats"]["points"] == 21  # Actual calculated value from logs
        assert lebron_stats["stats"]["fg3m"] == 3
        assert lebron_stats["stats"]["fouls"] == 2

        # Check Curry's stats
        curry_stats = next(p for p in all_players if p["name"] == "Stephen Curry")
        assert curry_stats["stats"]["points"] == 26  # Actual calculated value from logs
        assert curry_stats["stats"]["fg3m"] == 8  # Actual value from test logs
        assert curry_stats["stats"]["fg3a"] == 13  # Actual value from test logs
        assert curry_stats["stats"]["fouls"] == 3

    def test_import_game_with_jersey_conflict(self, test_client, mock_db_manager, db_session: Session):
        """Test handling jersey number conflicts during import."""
        # Get teams
        teams_response = test_client.get("/v1/teams/detail")
        teams = teams_response.json()

        # Create a team if none exist
        if not teams:
            team_response = test_client.post("/v1/teams/new", json={"name": "Test Team"})
            team = team_response.json()
        else:
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

        # Create teams if they don't exist
        if len(teams) < 2:
            home_team_response = test_client.post("/v1/teams/new", json={"name": "Home Team"})
            away_team_response = test_client.post("/v1/teams/new", json={"name": "Away Team"})
            home_team = home_team_response.json()
            away_team = away_team_response.json()
        else:
            home_team = teams[0]
            away_team = teams[1]

        # Create players if they don't exist
        players_response = test_client.get("/v1/players/list")
        players = players_response.json()

        home_player = next((p for p in players if p["team_id"] == home_team["id"]), None)
        away_player = next((p for p in players if p["team_id"] == away_team["id"]), None)

        if not home_player:
            home_player_response = test_client.post(
                "/v1/players/new",
                json={
                    "name": "Home Player",
                    "jersey_number": "10",
                    "team_id": home_team["id"],
                    "position": None,
                    "height": None,
                    "weight": None,
                    "year": None,
                },
            )
            home_player = home_player_response.json()

        if not away_player:
            away_player_response = test_client.post(
                "/v1/players/new",
                json={
                    "name": "Away Player",
                    "jersey_number": "20",
                    "team_id": away_team["id"],
                    "position": None,
                    "height": None,
                    "weight": None,
                    "year": None,
                },
            )
            away_player = away_player_response.json()

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
        game1_id = response1.json()["game_id"]
        game2_id = response2.json()["game_id"]

        box_score1 = test_client.get(f"/v1/games/{game1_id}/box-score").json()
        box_score2 = test_client.get(f"/v1/games/{game2_id}/box-score").json()

        # Check first game stats
        all_players_game1 = box_score1["home_team"]["players"] + box_score1["away_team"]["players"]
        game1_player_stats = next(p for p in all_players_game1 if p["name"] == "Home Player")
        assert game1_player_stats["stats"]["points"] == 9  # 4 + 3 + 2 = 9
        assert game1_player_stats["stats"]["fouls"] == 2

        # Check second game stats
        all_players_game2 = box_score2["home_team"]["players"] + box_score2["away_team"]["players"]
        game2_player_stats = next(p for p in all_players_game2 if p["name"] == "Home Player")
        assert game2_player_stats["stats"]["points"] == 15  # 9 + 4 + 2 = 15
        assert game2_player_stats["stats"]["fouls"] == 4

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
        box_score = test_client.get(f"/v1/games/{game_id}/box-score").json()

        # Count total players from both teams
        total_players = len(box_score["home_team"]["players"]) + len(box_score["away_team"]["players"])
        assert total_players == 3

        # Verify each player's stats by searching both teams
        all_players = box_score["home_team"]["players"] + box_score["away_team"]["players"]

        jordan_stats = next(p for p in all_players if p["name"] == "Jordan")
        assert jordan_stats["stats"]["points"] == 4  # 2 + 2 = 4
        assert jordan_stats["stats"]["fta"] == 4

        kyle_stats = next(p for p in all_players if p["name"] == "Kyle")
        assert kyle_stats["stats"]["points"] == 10  # From the actual test logs

        jose_stats = next(p for p in all_players if p["name"] == "Jose")
        assert jose_stats["stats"]["points"] == 25  # From the actual test logs
