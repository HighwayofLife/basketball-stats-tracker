"""
Integration tests for the complete game entry workflow.
"""

import os

# Set JWT_SECRET_KEY for all tests in this module
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough-for-validation-purposes"

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import app.data_access.database_manager as db_manager
from app.data_access.models import (
    Game,
    GameEvent,
    GameState,
    Player,
    PlayerGameStats,
    PlayerQuarterStats,
    Team,
)
from app.services.game_state_service import GameStateService
from app.web_ui.api import app


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # Override authentication dependencies for testing
    from app.auth.dependencies import get_current_user, require_admin
    from app.auth.models import User, UserRole

    # Store original overrides
    original_overrides = app.dependency_overrides.copy()

    def mock_current_user():
        """Mock current user for testing."""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            role=UserRole.ADMIN,  # Use admin to bypass all auth checks
            is_active=True,
            provider="local",
        )
        return user

    def mock_admin_user():
        """Mock admin user for testing."""
        return mock_current_user()

    try:
        # Clear and set new overrides
        app.dependency_overrides.clear()
        app.dependency_overrides[get_current_user] = mock_current_user
        app.dependency_overrides[require_admin] = mock_admin_user

        with TestClient(app) as client:
            yield client
    finally:
        # Always restore original state
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@pytest.fixture
def mock_db_manager(test_db_file_url, test_db_file_engine, monkeypatch):
    """Mock the database manager to use the test session."""
    from sqlalchemy.orm import sessionmaker

    # Ensure database is created with proper schema
    from app.data_access.models import Base

    Base.metadata.create_all(test_db_file_engine)

    @contextmanager
    def get_db_session_mock():
        # Use the provided test engine to ensure schema consistency
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_file_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    # Create a mock of the database manager
    mock_manager = MagicMock()
    mock_manager.get_db_session = get_db_session_mock

    # Patch the database manager
    original_manager = db_manager.db_manager
    db_manager.db_manager = mock_manager

    # Patch get_db_session in all the places where it's used
    from app.data_access import db_session
    from app.web_ui.routers import admin, games, pages, players

    # Store original functions for cleanup
    original_get_db_session = db_session.get_db_session

    # Patch using direct assignment (more reliable than monkeypatch for this case)
    db_session.get_db_session = get_db_session_mock

    # Patch in router modules that import get_db_session directly
    monkeypatch.setattr(players, "get_db_session", get_db_session_mock)
    monkeypatch.setattr(games, "get_db_session", get_db_session_mock)
    monkeypatch.setattr(admin, "get_db_session", get_db_session_mock)
    monkeypatch.setattr(pages, "get_db_session", get_db_session_mock)

    # Override get_db dependency for FastAPI
    from app.dependencies import get_db
    from app.web_ui.api import app

    def mock_get_db():
        with get_db_session_mock() as session:
            yield session

    app.dependency_overrides[get_db] = mock_get_db

    yield mock_manager

    # Restore the original database manager and functions
    db_manager.db_manager = original_manager
    db_session.get_db_session = original_get_db_session
    # Clear dependency overrides for this app
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


class TestGameEntryWorkflow:
    """Integration tests for the complete game entry workflow."""

    def test_complete_team_player_game_workflow(self, test_db_file_engine, test_client, mock_db_manager):
        """Test the complete workflow from creating teams to entering game data."""
        from sqlalchemy.orm import Session

        # Create a session for database verification queries
        db_session = Session(bind=test_db_file_engine)

        # Step 1: Create teams
        team1_response = test_client.post("/v1/teams/new", json={"name": "Lakers"})
        assert team1_response.status_code == 200
        team1_data = team1_response.json()
        team1_id = team1_data["id"]

        team2_response = test_client.post("/v1/teams/new", json={"name": "Warriors"})
        assert team2_response.status_code == 200
        team2_data = team2_response.json()
        team2_id = team2_data["id"]

        # Verify teams were created in database
        team1_db = db_session.query(Team).filter(Team.name == "Lakers").first()
        team2_db = db_session.query(Team).filter(Team.name == "Warriors").first()
        assert team1_db is not None
        assert team2_db is not None

        # Step 2: Create players for each team
        lakers_players = [
            {"name": "LeBron James", "team_id": team1_id, "jersey_number": "23", "position": "SF"},
            {"name": "Anthony Davis", "team_id": team1_id, "jersey_number": "3", "position": "PF"},
            {"name": "Russell Westbrook", "team_id": team1_id, "jersey_number": "0", "position": "PG"},
            {"name": "Carmelo Anthony", "team_id": team1_id, "jersey_number": "7", "position": "SF"},
            {"name": "Dwight Howard", "team_id": team1_id, "jersey_number": "39", "position": "C"},
        ]

        warriors_players = [
            {"name": "Stephen Curry", "team_id": team2_id, "jersey_number": "30", "position": "PG"},
            {"name": "Klay Thompson", "team_id": team2_id, "jersey_number": "11", "position": "SG"},
            {"name": "Draymond Green", "team_id": team2_id, "jersey_number": "23", "position": "PF"},
            {"name": "Andrew Wiggins", "team_id": team2_id, "jersey_number": "22", "position": "SF"},
            {"name": "Kevon Looney", "team_id": team2_id, "jersey_number": "5", "position": "C"},
        ]

        lakers_player_ids = []
        for player_data in lakers_players:
            response = test_client.post("/v1/players/new", json=player_data)
            assert response.status_code == 200
            lakers_player_ids.append(response.json()["id"])

        warriors_player_ids = []
        for player_data in warriors_players:
            response = test_client.post("/v1/players/new", json=player_data)
            assert response.status_code == 200
            warriors_player_ids.append(response.json()["id"])

        # Verify players were created
        assert db_session.query(Player).filter(Player.team_id == team1_id).count() == 5
        assert db_session.query(Player).filter(Player.team_id == team2_id).count() == 5

        # Step 3: Create a game
        game_data = {
            "date": "2025-05-23",
            "home_team_id": team1_id,
            "away_team_id": team2_id,
            "location": "Crypto.com Arena",
            "scheduled_time": "19:30",
            "notes": "Integration test game",
        }

        game_response = test_client.post("/v1/games", json=game_data)
        assert game_response.status_code == 200
        game_data_response = game_response.json()
        game_id = game_data_response["id"]

        # Verify game was created
        game_db = db_session.query(Game).filter(Game.id == game_id).first()
        assert game_db is not None
        assert game_db.date == date(2025, 5, 23)
        assert game_db.playing_team_id == team1_id
        assert game_db.opponent_team_id == team2_id

        # Verify game state was created
        game_state = db_session.query(GameState).filter(GameState.game_id == game_id).first()
        assert game_state is not None
        assert game_state.current_quarter == 1
        assert game_state.is_live is False
        assert game_state.is_final is False

        # Step 4: Start the game with starting lineups
        start_data = {"home_starters": lakers_player_ids[:5], "away_starters": warriors_player_ids[:5]}

        start_response = test_client.post(f"/v1/games/{game_id}/start", json=start_data)
        assert start_response.status_code == 200
        start_response_data = start_response.json()
        assert start_response_data["state"] == "live"
        assert start_response_data["current_quarter"] == 1

        # Verify game state was updated
        db_session.expire_all()  # Refresh all objects from database
        game_state = db_session.query(GameState).filter(GameState.game_id == game_id).first()
        assert game_state.is_live is True

        # Step 5: Record various game events

        # Record a made 2-pointer by LeBron
        shot_data = {
            "player_id": lakers_player_ids[0],  # LeBron
            "shot_type": "2pt",
            "made": True,
            "quarter": 1,
        }
        shot_response = test_client.post(f"/v1/games/{game_id}/events/shot", json=shot_data)
        assert shot_response.status_code == 200

        # Record a missed 3-pointer by Curry
        shot_data = {
            "player_id": warriors_player_ids[0],  # Curry
            "shot_type": "3pt",
            "made": False,
            "quarter": 1,
        }
        shot_response = test_client.post(f"/v1/games/{game_id}/events/shot", json=shot_data)
        assert shot_response.status_code == 200

        # Record a made free throw by Anthony Davis
        shot_data = {
            "player_id": lakers_player_ids[1],  # AD
            "shot_type": "ft",
            "made": True,
            "quarter": 1,
        }
        shot_response = test_client.post(f"/v1/games/{game_id}/events/shot", json=shot_data)
        assert shot_response.status_code == 200

        # Record a foul by Draymond
        foul_data = {
            "player_id": warriors_player_ids[2],  # Draymond
            "foul_type": "personal",
            "quarter": 1,
        }
        foul_response = test_client.post(f"/v1/games/{game_id}/events/foul", json=foul_data)
        assert foul_response.status_code == 200

        # Step 6: Make a substitution
        sub_data = {
            "team_id": team1_id,
            "players_out": [lakers_player_ids[2]],  # Westbrook out
            "players_in": [lakers_player_ids[3]],  # Carmelo in
        }
        sub_response = test_client.post(f"/v1/games/{game_id}/players/substitute", json=sub_data)
        assert sub_response.status_code == 200

        # Step 7: End the quarter
        quarter_response = test_client.post(f"/v1/games/{game_id}/end-quarter")
        assert quarter_response.status_code == 200

        # Verify quarter advanced
        db_session.expire_all()  # Refresh all objects from database
        game_state = db_session.query(GameState).filter(GameState.game_id == game_id).first()
        assert game_state.current_quarter == 2

        # Step 8: Get live game state
        state_response = test_client.get(f"/v1/games/{game_id}/live")
        assert state_response.status_code == 200
        state_data = state_response.json()
        assert state_data["game_state"]["current_quarter"] == 2
        assert state_data["game_state"]["is_live"] is True

        # Step 9: Finalize the game
        final_response = test_client.post(f"/v1/games/{game_id}/finalize")
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data["state"] == "final"
        assert "home_score" in final_data
        assert "away_score" in final_data

        # Verify game state was finalized
        db_session.expire_all()  # Refresh all objects from database
        game_state = db_session.query(GameState).filter(GameState.game_id == game_id).first()
        assert game_state.is_live is False
        assert game_state.is_final is True

        # Step 10: Verify all data was recorded correctly

        # Check game events
        events = db_session.query(GameEvent).filter(GameEvent.game_id == game_id).count()
        assert events >= 6  # 3 shots + 1 foul + 1 sub + start + end quarter + finalize

        # Check player stats
        lebron_stats = (
            db_session.query(PlayerGameStats)
            .filter(PlayerGameStats.game_id == game_id, PlayerGameStats.player_id == lakers_player_ids[0])
            .first()
        )
        assert lebron_stats is not None
        assert lebron_stats.total_2pm == 1
        assert lebron_stats.total_2pa == 1

        ad_stats = (
            db_session.query(PlayerGameStats)
            .filter(PlayerGameStats.game_id == game_id, PlayerGameStats.player_id == lakers_player_ids[1])
            .first()
        )
        assert ad_stats is not None
        assert ad_stats.total_ftm == 1
        assert ad_stats.total_fta == 1

        curry_stats = (
            db_session.query(PlayerGameStats)
            .filter(PlayerGameStats.game_id == game_id, PlayerGameStats.player_id == warriors_player_ids[0])
            .first()
        )
        assert curry_stats is not None
        assert curry_stats.total_3pm == 0
        assert curry_stats.total_3pa == 1

        draymond_stats = (
            db_session.query(PlayerGameStats)
            .filter(PlayerGameStats.game_id == game_id, PlayerGameStats.player_id == warriors_player_ids[2])
            .first()
        )
        assert draymond_stats is not None
        assert draymond_stats.fouls == 1

        # Check quarter stats
        lebron_q1_stats = (
            db_session.query(PlayerQuarterStats)
            .join(PlayerGameStats)
            .filter(
                PlayerGameStats.game_id == game_id,
                PlayerGameStats.player_id == lakers_player_ids[0],
                PlayerQuarterStats.quarter_number == 1,
            )
            .first()
        )
        assert lebron_q1_stats is not None
        assert lebron_q1_stats.fg2m == 1
        assert lebron_q1_stats.fg2a == 1

    def test_team_management_workflow(self, test_db_file_session, test_client, mock_db_manager):
        """Test the team management workflow including CRUD operations."""
        db_session = test_db_file_session  # Use file-based session for database queries

        # Create a team
        team_response = test_client.post("/v1/teams/new", json={"name": "Test Team"})
        assert team_response.status_code == 200
        team_id = team_response.json()["id"]

        # Get team details
        detail_response = test_client.get(f"/v1/teams/{team_id}/detail")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["name"] == "Test Team"
        assert len(detail_data["players"]) == 0

        # Add players to the team
        player_data = {
            "name": "Test Player",
            "team_id": team_id,
            "jersey_number": "42",
            "position": "PG",
            "height": 75,
            "weight": 180,
            "year": "Sophomore",
        }

        player_response = test_client.post("/v1/players/new", json=player_data)
        assert player_response.status_code == 200
        player_id = player_response.json()["id"]

        # Get team details again to verify player was added
        detail_response = test_client.get(f"/v1/teams/{team_id}/detail")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert len(detail_data["players"]) == 1
        assert detail_data["players"][0]["name"] == "Test Player"

        # Update the team name
        update_response = test_client.put(f"/v1/teams/{team_id}", json={"name": "Updated Team"})
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Team"

        # Update the player
        player_update_data = {"name": "Updated Player", "jersey_number": "24", "position": "SG"}
        player_update_response = test_client.put(f"/v1/players/{player_id}", json=player_update_data)
        assert player_update_response.status_code == 200
        updated_player = player_update_response.json()
        assert updated_player["name"] == "Updated Player"
        assert updated_player["jersey_number"] == "24"
        assert updated_player["position"] == "SG"

        # List all players
        players_response = test_client.get("/v1/players/list")
        assert players_response.status_code == 200
        players_data = players_response.json()
        assert len(players_data) == 1
        assert players_data[0]["name"] == "Updated Player"

        # Delete the player (should deactivate since no stats)
        delete_player_response = test_client.delete(f"/v1/players/{player_id}")
        assert delete_player_response.status_code == 200
        assert "deleted successfully" in delete_player_response.json()["message"]

        # Verify player was deleted
        player_check = db_session.query(Player).filter(Player.id == player_id).first()
        assert player_check is None

        # Delete the team (should work since no games)
        delete_team_response = test_client.delete(f"/v1/teams/{team_id}")
        assert delete_team_response.status_code == 200
        assert "deleted successfully" in delete_team_response.json()["message"]

        # Verify team was deleted
        team_check = db_session.query(Team).filter(Team.id == team_id).first()
        assert team_check is None

    def test_game_state_service_integration(self, test_db_file_session):
        """Test the GameStateService integration with the database."""
        db_session = test_db_file_session  # Use file-based session for database queries

        # Create teams and players directly in the database
        team1 = Team(name="Home Team")
        team2 = Team(name="Away Team")
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

    def test_error_handling_workflow(self, test_db_file_session, test_client, mock_db_manager):
        """Test error handling in various workflow scenarios."""
        db_session = test_db_file_session  # Use file-based session for database queries

        # Try to create player for non-existent team
        player_data = {"name": "Test Player", "team_id": 999, "jersey_number": "1"}
        response = test_client.post("/v1/players/new", json=player_data)
        assert response.status_code == 400
        assert "Team not found" in response.json()["detail"]

        # Create a team and player
        team_response = test_client.post("/v1/teams/new", json={"name": "Test Team"})
        team_id = team_response.json()["id"]

        player_response = test_client.post(
            "/v1/players/new", json={"name": "Test Player", "team_id": team_id, "jersey_number": "1"}
        )
        player_id = player_response.json()["id"]

        # Try to create another player with same jersey number
        duplicate_response = test_client.post(
            "/v1/players/new", json={"name": "Duplicate Player", "team_id": team_id, "jersey_number": "1"}
        )
        assert duplicate_response.status_code == 400
        assert "already exists" in duplicate_response.json()["detail"]

        # Create a game
        game_response = test_client.post(
            "/v1/games",
            json={
                "date": "2025-05-23",
                "home_team_id": team_id,
                "away_team_id": team_id,  # Same team as opponent
            },
        )
        game_id = game_response.json()["id"]

        # Try to record shot before starting game
        shot_response = test_client.post(
            f"/v1/games/{game_id}/events/shot", json={"player_id": player_id, "shot_type": "2pt", "made": True}
        )
        assert shot_response.status_code == 400
        assert "not in progress" in shot_response.json()["detail"]

        # Try to delete team with a game
        delete_response = test_client.delete(f"/v1/teams/{team_id}")
        assert delete_response.status_code == 400
        assert "existing games" in delete_response.json()["detail"]
