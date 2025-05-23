"""
Test module for the PlayerService.
"""

from unittest.mock import MagicMock, patch

from app.data_access.models import Player
from app.services.player_service import PlayerService


class TestPlayerService:
    """Tests for the PlayerService."""

    def test_init(self, db_session):
        """Test initializing the player service."""
        service = PlayerService(db_session)
        assert service._db_session == db_session

    def test_get_or_create_player_existing(self, db_session):
        """Test getting an existing player by team and jersey."""
        # Mock the db session and CRUD function
        mock_get_player = MagicMock(return_value=Player(id=1, name="Existing Player", jersey_number=23, team_id=1))

        with patch("app.services.player_service.get_player_by_team_and_jersey", mock_get_player):
            service = PlayerService(db_session)
            player = service.get_or_create_player(1, 23, "Existing Player")

            assert player.id == 1
            assert player.name == "Existing Player"
            assert player.jersey_number == 23
            assert player.team_id == 1
            mock_get_player.assert_called_once_with(db_session, 1, 23)

    def test_get_or_create_player_new(self, db_session):
        """Test creating a new player."""
        # Mock the db session and CRUD functions
        mock_get_player = MagicMock(return_value=None)
        mock_create_player = MagicMock(return_value=Player(id=2, name="New Player", jersey_number=10, team_id=1))

        with (
            patch("app.services.player_service.get_player_by_team_and_jersey", mock_get_player),
            patch("app.services.player_service.create_player", mock_create_player),
        ):
            service = PlayerService(db_session)
            player = service.get_or_create_player(1, 10, "New Player")

            assert player.id == 2
            assert player.name == "New Player"
            assert player.jersey_number == 10
            assert player.team_id == 1
            mock_get_player.assert_called_once_with(db_session, 1, 10)
            mock_create_player.assert_called_once_with(db_session, "New Player", 10, 1)

    def test_get_or_create_player_existing_different_name(self, db_session):
        """Test getting an existing player by team and jersey when name is different."""
        # Mock the db session and CRUD function with a player with a different name
        mock_existing_player = Player(id=1, name="Original Name", jersey_number=23, team_id=1)
        mock_get_player = MagicMock(return_value=mock_existing_player)

        with patch("app.services.player_service.get_player_by_team_and_jersey", mock_get_player):
            service = PlayerService(db_session)
            player = service.get_or_create_player(1, 23, "New Name")

            # Should return the existing player but update the name
            assert player.id == 1
            assert player.name == "New Name"  # Name should be updated
            assert player.jersey_number == 23
            assert player.team_id == 1
            mock_get_player.assert_called_once_with(db_session, 1, 23)

    def test_get_player_details(self, db_session):
        """Test getting player details by ID."""
        # Mock the db session and CRUD function
        mock_player = Player(id=1, name="Test Player", jersey_number=23, team_id=1)
        mock_get_player = MagicMock(return_value=mock_player)

        with patch("app.services.player_service.get_player_by_id", mock_get_player):
            service = PlayerService(db_session)
            player = service.get_player_details(1)

            assert player is not None
            assert player.id == 1
            assert player.name == "Test Player"
            mock_get_player.assert_called_once_with(db_session, 1)

    def test_get_player_details_not_found(self, db_session):
        """Test getting player details by ID when player doesn't exist."""
        # Mock the db session and CRUD function to return None
        mock_get_player = MagicMock(return_value=None)

        with patch("app.services.player_service.get_player_by_id", mock_get_player):
            service = PlayerService(db_session)
            player = service.get_player_details(999)  # Non-existent ID

            assert player is None
            mock_get_player.assert_called_once_with(db_session, 999)

    def test_get_team_roster(self, db_session):
        """Test getting team roster by team ID."""
        # Mock the db session and CRUD function
        mock_players = [
            Player(id=1, name="Player 1", jersey_number=1, team_id=1),
            Player(id=2, name="Player 2", jersey_number=2, team_id=1),
            Player(id=3, name="Player 3", jersey_number=3, team_id=1),
        ]
        mock_get_players = MagicMock(return_value=mock_players)

        with patch("app.services.player_service.get_players_by_team", mock_get_players):
            service = PlayerService(db_session)
            players = service.get_team_roster(1)

            assert len(players) == 3
            assert players[0].name == "Player 1"
            assert players[1].name == "Player 2"
            assert players[2].name == "Player 3"
            mock_get_players.assert_called_once_with(db_session, 1)

    def test_get_team_roster_empty(self, db_session):
        """Test getting team roster when there are no players."""
        # Mock the db session and CRUD function to return empty list
        mock_get_players = MagicMock(return_value=[])

        with patch("app.services.player_service.get_players_by_team", mock_get_players):
            service = PlayerService(db_session)
            players = service.get_team_roster(1)

            assert isinstance(players, list)
            assert len(players) == 0
            mock_get_players.assert_called_once_with(db_session, 1)
