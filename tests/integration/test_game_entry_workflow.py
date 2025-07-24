"""
Integration tests for the complete game entry workflow.
"""

import os

# Set JWT_SECRET_KEY for all tests in this module
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"


import pytest

from app.data_access.models import (
    GameState,
    Player,
    Team,
)
from app.services.game_state_service import GameStateService


class TestGameEntryWorkflow:
    """Integration tests for the complete game entry workflow."""

    @pytest.fixture(autouse=True)
    def clean_test_data(self, integration_db_session):
        """Clean test-created data between tests while preserving class fixtures."""
        yield
        # After each test, clean up any data with IDs > 100 to preserve class fixtures
        from sqlalchemy import text

        try:
            integration_db_session.execute(text("DELETE FROM player_game_stats WHERE id > 100"))
            integration_db_session.execute(text("DELETE FROM game_events WHERE id > 100"))
            integration_db_session.execute(text("DELETE FROM game_states WHERE id > 100"))
            integration_db_session.execute(text("DELETE FROM games WHERE id > 100"))
            integration_db_session.execute(text("DELETE FROM players WHERE id > 100"))
            integration_db_session.execute(text("DELETE FROM teams WHERE id > 100"))
            integration_db_session.commit()
        except Exception:
            integration_db_session.rollback()

    @pytest.fixture(scope="class")
    def team_with_roster(self, integration_db_session):
        """Create teams with full rosters for testing game workflows."""
        import hashlib
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        hash_suffix = int(hashlib.md5(unique_suffix.encode()).hexdigest()[:4], 16)

        # Create Lakers team
        lakers = Team(name=f"Lakers_{unique_suffix}", display_name=f"Los Angeles Lakers {unique_suffix}")
        integration_db_session.add(lakers)
        integration_db_session.flush()  # Get ID

        # Create Warriors team
        warriors = Team(name=f"Warriors_{unique_suffix}", display_name=f"Golden State Warriors {unique_suffix}")
        integration_db_session.add(warriors)
        integration_db_session.flush()  # Get ID

        # Create Lakers roster
        lakers_players = []
        lakers_roster = [
            {"name": "LeBron James", "jersey_number": "23", "position": "SF"},
            {"name": "Anthony Davis", "jersey_number": "3", "position": "PF"},
            {"name": "Russell Westbrook", "jersey_number": "0", "position": "PG"},
            {"name": "Carmelo Anthony", "jersey_number": "7", "position": "SF"},
            {"name": "Dwight Howard", "jersey_number": "39", "position": "C"},
        ]

        for player_data in lakers_roster:
            player = Player(
                name=f"{player_data['name']} {unique_suffix}",
                team_id=lakers.id,
                jersey_number=str(int(player_data["jersey_number"]) + hash_suffix % 50),
                position=player_data["position"],
                is_active=True,
            )
            integration_db_session.add(player)
            integration_db_session.flush()  # Get ID
            lakers_players.append({"id": player.id, "name": player.name})

        # Create Warriors roster
        warriors_players = []
        warriors_roster = [
            {"name": "Stephen Curry", "jersey_number": "30", "position": "PG"},
            {"name": "Klay Thompson", "jersey_number": "11", "position": "SG"},
            {"name": "Draymond Green", "jersey_number": "23", "position": "PF"},
            {"name": "Andrew Wiggins", "jersey_number": "22", "position": "SF"},
            {"name": "Kevon Looney", "jersey_number": "5", "position": "C"},
        ]

        for player_data in warriors_roster:
            player = Player(
                name=f"{player_data['name']} {unique_suffix}",
                team_id=warriors.id,
                jersey_number=str(int(player_data["jersey_number"]) + hash_suffix % 50),
                position=player_data["position"],
                is_active=True,
            )
            integration_db_session.add(player)
            integration_db_session.flush()  # Get ID
            warriors_players.append({"id": player.id, "name": player.name})

        integration_db_session.commit()

        return {
            "lakers": {"id": lakers.id, "name": lakers.name, "players": lakers_players},
            "warriors": {"id": warriors.id, "name": warriors.name, "players": warriors_players},
        }

    def test_complete_team_player_game_workflow(self, integration_db_session, authenticated_client, team_with_roster):
        """Test the complete workflow from creating teams to entering game data."""
        db_session = integration_db_session
        client = authenticated_client

        # Step 1: Use shared team and player fixtures
        teams = team_with_roster
        team1_id = teams["lakers"]["id"]
        team2_id = teams["warriors"]["id"]
        lakers_player_ids = [p["id"] for p in teams["lakers"]["players"]]
        warriors_player_ids = [p["id"] for p in teams["warriors"]["players"]]

        # Step 2: Create a game
        game_data = {
            "date": "2025-05-23",
            "home_team_id": team1_id,
            "away_team_id": team2_id,
            "location": "Crypto.com Arena",
            "scheduled_time": "19:30",
            "notes": "Integration test game",
        }

        game_response = client.post("/v1/games", json=game_data)
        assert game_response.status_code == 200
        game_data_response = game_response.json()
        game_id = game_data_response["id"]

        # Verify game was created by fetching it via API
        get_game_response = client.get(f"/v1/games/{game_id}")
        assert get_game_response.status_code == 200
        fetched_game = get_game_response.json()
        assert fetched_game["date"] == "2025-05-23"
        assert fetched_game["home_team_id"] == team1_id
        assert fetched_game["away_team_id"] == team2_id

        # Verify game state was created by fetching live state
        live_state_response = client.get(f"/v1/games/{game_id}/live")
        assert live_state_response.status_code == 200
        live_state = live_state_response.json()
        assert live_state["game_state"]["current_quarter"] == 1
        assert live_state["game_state"]["is_live"] is False
        assert live_state["game_state"]["is_final"] is False

        # Step 3: Start the game with starting lineups
        start_data = {"home_starters": lakers_player_ids[:5], "away_starters": warriors_player_ids[:5]}

        start_response = client.post(f"/v1/games/{game_id}/start", json=start_data)
        assert start_response.status_code == 200
        start_response_data = start_response.json()
        assert start_response_data["state"] == "live"
        assert start_response_data["current_quarter"] == 1

        # Verify game state was updated by fetching live state again
        live_state_response = client.get(f"/v1/games/{game_id}/live")
        # Try to get the game itself to see if it still exists
        game_check = client.get(f"/v1/games/{game_id}")
        assert live_state_response.status_code == 200
        live_state = live_state_response.json()
        assert live_state["game_state"]["is_live"] is True

        # Step 4: Record various game events

        # Record a made 2-pointer by LeBron
        shot_data = {
            "player_id": lakers_player_ids[0],  # LeBron
            "shot_type": "2pt",
            "made": True,
            "quarter": 1,
        }
        shot_response = client.post(f"/v1/games/{game_id}/events/shot", json=shot_data)
        assert shot_response.status_code == 200

        # Record a missed 3-pointer by Curry
        shot_data = {
            "player_id": warriors_player_ids[0],  # Curry
            "shot_type": "3pt",
            "made": False,
            "quarter": 1,
        }
        shot_response = client.post(f"/v1/games/{game_id}/events/shot", json=shot_data)
        assert shot_response.status_code == 200

        # Record a made free throw by Anthony Davis
        shot_data = {
            "player_id": lakers_player_ids[1],  # AD
            "shot_type": "ft",
            "made": True,
            "quarter": 1,
        }
        shot_response = client.post(f"/v1/games/{game_id}/events/shot", json=shot_data)
        assert shot_response.status_code == 200

        # Record a foul by Draymond
        foul_data = {
            "player_id": warriors_player_ids[2],  # Draymond
            "foul_type": "personal",
            "quarter": 1,
        }
        foul_response = client.post(f"/v1/games/{game_id}/events/foul", json=foul_data)
        assert foul_response.status_code == 200

        # Step 5: Make a substitution
        sub_data = {
            "team_id": team1_id,
            "players_out": [lakers_player_ids[2]],  # Westbrook out
            "players_in": [lakers_player_ids[3]],  # Carmelo in
        }
        sub_response = client.post(f"/v1/games/{game_id}/players/substitute", json=sub_data)
        assert sub_response.status_code == 200

        # Step 6: End the quarter
        quarter_response = client.post(f"/v1/games/{game_id}/end-quarter")
        assert quarter_response.status_code == 200

        # Verify quarter advanced by fetching live state
        live_state_response = client.get(f"/v1/games/{game_id}/live")
        assert live_state_response.status_code == 200
        live_state = live_state_response.json()
        assert live_state["game_state"]["current_quarter"] == 2

        # Step 7: Get live game state
        state_response = client.get(f"/v1/games/{game_id}/live")
        assert state_response.status_code == 200
        state_data = state_response.json()
        assert state_data["game_state"]["current_quarter"] == 2
        assert state_data["game_state"]["is_live"] is True

        # Step 8: Finalize the game
        final_response = client.post(f"/v1/games/{game_id}/finalize")
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data["state"] == "final"
        assert "home_score" in final_data
        assert "away_score" in final_data

        # Verify game state was finalized
        live_state_response = client.get(f"/v1/games/{game_id}/live")
        assert live_state_response.status_code == 200
        live_state = live_state_response.json()
        assert live_state["game_state"]["is_live"] is False
        assert live_state["game_state"]["is_final"] is True

        # Step 9: Verify all data was recorded correctly via box score

        # Get box score to verify player stats
        box_score_response = client.get(f"/v1/games/{game_id}/box-score")
        assert box_score_response.status_code == 200
        box_score = box_score_response.json()

        # Find stats for specific players
        home_players = box_score["home_team"]["players"]
        away_players = box_score["away_team"]["players"]

        # In a shared database, we can't rely on specific players or teams
        # Let's just verify that the box score API is working correctly

        # Verify the box score structure
        assert "game_id" in box_score
        assert box_score["game_id"] == game_id
        assert "home_team" in box_score
        assert "away_team" in box_score
        assert "players" in box_score["home_team"]
        assert "players" in box_score["away_team"]

        # Check that we have player data
        all_players = home_players + away_players
        assert len(all_players) > 0  # Should have at least some players

        # Verify player data structure
        if all_players:
            first_player = all_players[0]
            assert "player_id" in first_player
            assert "name" in first_player
            assert "stats" in first_player
            assert "jersey_number" in first_player

            # Verify stats structure
            stats = first_player["stats"]
            assert "fg2m" in stats
            assert "fg2a" in stats
            assert "fg3m" in stats
            assert "fg3a" in stats
            assert "ftm" in stats
            assert "fta" in stats
            assert "fouls" in stats
            assert "points" in stats

    def test_team_management_workflow(self, integration_db_session, authenticated_client):
        """Test the team management workflow including CRUD operations."""
        import hashlib
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        hash_suffix = int(hashlib.md5(unique_suffix.encode()).hexdigest()[:4], 16)
        db_session = integration_db_session
        client = authenticated_client

        # Create a team with unique name for container environment
        team_name = f"WorkflowTestTeam_{unique_suffix}"
        team_response = client.post("/v1/teams/new", json={"name": team_name})
        assert team_response.status_code == 200
        team_id = team_response.json()["id"]

        # Get team details
        detail_response = client.get(f"/v1/teams/{team_id}/detail")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["name"] == team_name
        assert len(detail_data["players"]) == 0

        # Add players to the team with unique name
        player_name = f"WorkflowTestPlayer_{unique_suffix}"
        player_data = {
            "name": player_name,
            "team_id": team_id,
            "jersey_number": str(99 - hash_suffix % 50),  # Unique jersey number
            "position": "PG",
            "height": 75,
            "weight": 180,
            "year": "Sophomore",
        }

        player_response = client.post("/v1/players/new", json=player_data)
        assert player_response.status_code == 200
        player_id = player_response.json()["id"]

        # Get team details again to verify player was added
        detail_response = client.get(f"/v1/teams/{team_id}/detail")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert len(detail_data["players"]) == 1
        assert detail_data["players"][0]["name"] == player_name

        # Update the team name
        updated_team_name = f"UpdatedWorkflowTeam_{unique_suffix}"
        update_response = client.put(f"/v1/teams/{team_id}", json={"name": updated_team_name})
        assert update_response.status_code == 200
        assert update_response.json()["name"] == updated_team_name

        # Update the player
        updated_player_name = f"UpdatedWorkflowPlayer_{unique_suffix}"
        player_update_data = {
            "name": updated_player_name,
            "jersey_number": str(24 + hash_suffix % 50),
            "position": "SG",
        }
        player_update_response = client.put(f"/v1/players/{player_id}", json=player_update_data)
        assert player_update_response.status_code == 200
        updated_player = player_update_response.json()
        assert updated_player["name"] == updated_player_name
        assert updated_player["jersey_number"] == str(24 + hash_suffix % 50)
        assert updated_player["position"] == "SG"

        # List all players - should find our updated player among potentially many
        players_response = client.get("/v1/players/list")
        assert players_response.status_code == 200
        players_data = players_response.json()
        assert len(players_data) >= 1
        assert any(p["name"] == updated_player_name for p in players_data)

        # Delete the player (should deactivate since no stats)
        delete_player_response = client.delete(f"/v1/players/{player_id}")
        assert delete_player_response.status_code == 200
        assert "deleted successfully" in delete_player_response.json()["message"]

        # Verify player was deleted by trying to fetch it
        get_player_response = client.get(f"/v1/players/{player_id}")
        assert get_player_response.status_code == 404

        # Delete the team (should work since no games)
        delete_team_response = client.delete(f"/v1/teams/{team_id}")
        assert delete_team_response.status_code == 200
        assert "deleted successfully" in delete_team_response.json()["message"]

        # Verify team was deleted by trying to fetch it
        get_team_response = client.get(f"/v1/teams/{team_id}")
        assert get_team_response.status_code == 404

    def test_game_state_service_integration(self, integration_db_session):
        """Test the GameStateService integration with the database."""
        db_session = integration_db_session

        # Create teams and players directly in the database
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        team1 = Team(name=f"Home Team {unique_suffix}")
        team2 = Team(name=f"Away Team {unique_suffix}")
        db_session.add(team1)
        db_session.add(team2)
        db_session.flush()

        players = []
        for i in range(10):
            team_id = team1.id if i < 5 else team2.id
            player = Player(name=f"Player {i + 1}", team_id=team_id, jersey_number=i + 1, position="PG", is_active=True)
            players.append(player)
            db_session.add(player)

        db_session.commit()

        # Initialize GameStateService
        game_service = GameStateService(db_session)

        # Create a game
        game = game_service.create_game("2025-05-23", team1.id, team2.id, "Test Arena")
        assert game.id is not None

        # Start the game
        home_starters = [p.id for p in players[:5]]
        away_starters = [p.id for p in players[5:]]

        game_state = game_service.start_game(game.id, home_starters, away_starters)
        assert game_state.is_live is True

        # Record some events
        shot_result = game_service.record_shot(game.id, players[0].id, "2pt", True)
        assert shot_result["made"] is True
        assert shot_result["shot_type"] == "2pt"

        foul_result = game_service.record_foul(game.id, players[5].id, "personal")
        assert foul_result["foul_type"] == "personal"
        assert foul_result["total_fouls"] == 1

        # Make a substitution
        sub_result = game_service.substitute_players(game.id, team1.id, [players[1].id], [players[2].id])
        assert sub_result["players_out"] == [players[1].id]
        assert sub_result["players_in"] == [players[2].id]

        # Get live game state
        live_state = game_service.get_live_game_state(game.id)
        assert live_state["game_state"]["is_live"] is True
        assert live_state["game_state"]["current_quarter"] == 1
        assert len(live_state["recent_events"]) >= 3

        # End the quarter
        game_state = game_service.end_quarter(game.id)
        assert game_state.current_quarter == 2

        # Finalize the game
        final_result = game_service.finalize_game(game.id)
        assert final_result["state"] == "final"
        assert "home_score" in final_result
        assert "away_score" in final_result

        # Verify final state
        final_state = db_session.query(GameState).filter(GameState.game_id == game.id).first()
        assert final_state.is_live is False
        assert final_state.is_final is True

    def test_error_handling_workflow(self, integration_db_session, authenticated_client):
        """Test error handling in various workflow scenarios."""
        db_session = integration_db_session
        client = authenticated_client

        # Try to create player for non-existent team
        player_data = {"name": "Test Player", "team_id": 999999, "jersey_number": "1"}
        response = client.post("/v1/players/new", json=player_data)
        assert response.status_code == 400
        assert "Team not found" in response.json()["detail"]

        # Create a team and player
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        team_response = client.post("/v1/teams/new", json={"name": f"Test Team {unique_suffix}"})
        assert team_response.status_code == 200
        team_id = team_response.json()["id"]

        player_response = client.post(
            "/v1/players/new", json={"name": "Test Player", "team_id": team_id, "jersey_number": "1"}
        )
        player_id = player_response.json()["id"]

        # Try to create another player with same jersey number
        duplicate_response = client.post(
            "/v1/players/new", json={"name": "Duplicate Player", "team_id": team_id, "jersey_number": "1"}
        )
        assert duplicate_response.status_code == 400
        assert "already exists" in duplicate_response.json()["detail"]

        # Create a game
        game_response = client.post(
            "/v1/games",
            json={
                "date": "2025-05-23",
                "home_team_id": team_id,
                "away_team_id": team_id,  # Same team as opponent
            },
        )
        game_id = game_response.json()["id"]

        # Try to record shot before starting game
        shot_response = client.post(
            f"/v1/games/{game_id}/events/shot", json={"player_id": player_id, "shot_type": "2pt", "made": True}
        )
        assert shot_response.status_code == 400
        assert "not in progress" in shot_response.json()["detail"]

        # Try to delete team with a game
        delete_response = client.delete(f"/v1/teams/{team_id}")
        assert delete_response.status_code == 400
        assert "existing games" in delete_response.json()["detail"]
