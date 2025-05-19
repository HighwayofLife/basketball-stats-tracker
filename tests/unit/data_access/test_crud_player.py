"""
Test module for player CRUD operations.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.data_access.crud.crud_player import (
    create_player,
    get_player_by_id,
    get_player_by_team_and_jersey,
    get_players_by_team,
)
from app.data_access.crud.crud_team import create_team
from app.data_access.models import Player


class TestPlayerCrud:
    """Tests for Player CRUD operations."""

    @pytest.fixture
    def test_teams(self, db_session):
        """Create test teams for player tests."""
        team_a = create_team(db_session, "Team A")
        team_b = create_team(db_session, "Team B")
        return {"team_a": team_a, "team_b": team_b}

    def test_create_player(self, db_session, test_teams):
        """Test creating a player."""
        player = create_player(db_session, "Test Player", 23, test_teams["team_a"].id)

        assert isinstance(player, Player)
        assert player.id is not None
        assert player.name == "Test Player"
        assert player.jersey_number == 23
        assert player.team_id == test_teams["team_a"].id

    def test_create_player_duplicate_jersey_same_team(self, db_session, test_teams):
        """Test that creating a player with the same jersey number in the same team raises an IntegrityError."""
        # Create the first player
        player1 = create_player(db_session, "Player 1", 23, test_teams["team_a"].id)
        assert player1.jersey_number == 23

        # Try to create a second player with the same jersey number in the same team
        with pytest.raises(IntegrityError):
            create_player(db_session, "Player 2", 23, test_teams["team_a"].id)

    def test_create_player_duplicate_jersey_different_team(self, db_session, test_teams):
        """Test creating players with the same jersey number in different teams."""
        # Create a player in Team A
        player1 = create_player(db_session, "Player 1", 23, test_teams["team_a"].id)
        assert player1.jersey_number == 23

        # Create a player with the same jersey number in Team B
        player2 = create_player(db_session, "Player 2", 23, test_teams["team_b"].id)
        assert player2.jersey_number == 23
        # No exception should be raised

    def test_create_player_duplicate_name_same_team(self, db_session, test_teams):
        """Test that creating a player with the same name in the same team raises an IntegrityError."""
        # Create the first player
        player1 = create_player(db_session, "John Smith", 23, test_teams["team_a"].id)
        assert player1.name == "John Smith"

        # Try to create a second player with the same name in the same team
        with pytest.raises(IntegrityError):
            create_player(db_session, "John Smith", 24, test_teams["team_a"].id)

    def test_create_player_duplicate_name_different_team(self, db_session, test_teams):
        """Test creating players with the same name in different teams."""
        # Create a player in Team A
        player1 = create_player(db_session, "John Smith", 23, test_teams["team_a"].id)
        assert player1.name == "John Smith"

        # Create a player with the same name in Team B
        player2 = create_player(db_session, "John Smith", 23, test_teams["team_b"].id)
        assert player2.name == "John Smith"
        # No exception should be raised

    def test_get_player_by_team_and_jersey(self, db_session, test_teams):
        """Test getting a player by team and jersey number."""
        original_player = create_player(db_session, "Jersey Player", 42, test_teams["team_a"].id)

        # Get the player by team and jersey
        retrieved_player = get_player_by_team_and_jersey(db_session, test_teams["team_a"].id, 42)

        assert retrieved_player is not None
        assert retrieved_player.id == original_player.id
        assert retrieved_player.name == "Jersey Player"
        assert retrieved_player.jersey_number == 42
        assert retrieved_player.team_id == test_teams["team_a"].id

    def test_get_player_by_team_and_jersey_not_found(self, db_session, test_teams):
        """Test getting a player by team and jersey number that doesn't exist."""
        retrieved_player = get_player_by_team_and_jersey(db_session, test_teams["team_a"].id, 99)
        assert retrieved_player is None

    def test_get_player_by_id(self, db_session, test_teams):
        """Test getting a player by ID."""
        original_player = create_player(db_session, "ID Player", 1, test_teams["team_a"].id)

        # Get the player by ID
        retrieved_player = get_player_by_id(db_session, original_player.id)

        assert retrieved_player is not None
        assert retrieved_player.id == original_player.id
        assert retrieved_player.name == "ID Player"
        assert retrieved_player.jersey_number == 1
        assert retrieved_player.team_id == test_teams["team_a"].id

    def test_get_player_by_id_not_found(self, db_session):
        """Test getting a player by ID that doesn't exist."""
        retrieved_player = get_player_by_id(db_session, 9999)  # Assuming ID 9999 doesn't exist
        assert retrieved_player is None

    def test_get_players_by_team_empty(self, db_session, test_teams):
        """Test getting players by team when there are none."""
        players = get_players_by_team(db_session, test_teams["team_b"].id)
        assert isinstance(players, list)
        assert len(players) == 0

    def test_get_players_by_team(self, db_session, test_teams):
        """Test getting players by team."""
        # Create some players in Team A
        player1 = create_player(db_session, "Player 1", 1, test_teams["team_a"].id)
        player2 = create_player(db_session, "Player 2", 2, test_teams["team_a"].id)
        player3 = create_player(db_session, "Player 3", 3, test_teams["team_a"].id)

        # Create a player in Team B (should not be retrieved)
        create_player(db_session, "Player B", 4, test_teams["team_b"].id)

        # Get players by Team A
        players = get_players_by_team(db_session, test_teams["team_a"].id)

        assert isinstance(players, list)
        assert len(players) == 3
        assert any(p.id == player1.id for p in players)
        assert any(p.id == player2.id for p in players)
        assert any(p.id == player3.id for p in players)
        # No player from Team B should be present
        assert not any(p.team_id == test_teams["team_b"].id for p in players)
