"""Unit tests for substitute and unknown player handling."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.import_services.import_processor import ImportProcessor
from app.services.player_service import PlayerService
from app.data_access.models import Player, Team
# We'll use a mock for SUBSTITUTE_PLAYER_NAMES in tests


class TestSubstitutePlayerHandling:
    """Test cases for substitute player functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def import_processor(self, mock_db):
        """Create an ImportProcessor instance with mocked dependencies."""
        with patch("app.services.import_services.import_processor.GameService"):
            with patch("app.services.import_services.import_processor.PlayerService"):
                with patch("app.services.import_services.import_processor.StatsEntryService"):
                    processor = ImportProcessor(mock_db)
                    return processor

    def test_unknown_player_detection(self, import_processor, mock_db):
        """Test that 'unknown' player names are handled correctly."""
        # Setup
        team = Team(id=1, name="Blue Team")
        mock_db.query.return_value.filter.return_value.first.return_value = team

        player_stats = Mock()
        player_stats.team_name = "Blue Team"
        player_stats.jersey_number = "99"
        player_stats.player_name = "Unknown"
        # Mock quarter data
        player_stats.quarter_1 = ""
        player_stats.quarter_2 = ""
        player_stats.quarter_3 = ""
        player_stats.quarter_4 = ""
        player_stats.overtime = ""

        # Mock player service to return a player
        mock_player = Player(id=1, name="Unknown #99 (Blue Team)", jersey_number="99")
        import_processor.player_service.get_or_create_player.return_value = mock_player

        # Mock stats service
        import_processor.stats_service.add_player_quarter_stats.return_value = True

        # Act
        result = import_processor._process_player_game_stats(Mock(), player_stats)

        # Assert
        assert result is True
        import_processor.player_service.get_or_create_player.assert_called_once_with(
            team_id=1, jersey_number="99", player_name="Unknown #99 (Blue Team)"
        )

    def test_unidentified_player_handling(self, import_processor, mock_db):
        """Test that 'unidentified' player names are handled correctly."""
        # Setup
        team = Team(id=1, name="Red Team")
        mock_db.query.return_value.filter.return_value.first.return_value = team

        player_stats = Mock()
        player_stats.team_name = "Red Team"
        player_stats.jersey_number = "00"
        player_stats.player_name = "Unidentified"
        # Mock quarter data
        for q in ["quarter_1", "quarter_2", "quarter_3", "quarter_4", "overtime"]:
            setattr(player_stats, q, "")

        # Mock player service
        mock_player = Player(id=2, name="Unknown #00 (Red Team)", jersey_number="00")
        import_processor.player_service.get_or_create_player.return_value = mock_player

        # Mock stats service
        import_processor.stats_service.add_player_quarter_stats.return_value = True

        # Act
        result = import_processor._process_player_game_stats(Mock(), player_stats)

        # Assert
        assert result is True
        import_processor.player_service.get_or_create_player.assert_called_once_with(
            team_id=1, jersey_number="00", player_name="Unknown #00 (Red Team)"
        )

    def test_substitute_player_identification(self, import_processor):
        """Test the _is_substitute_player method."""
        # Test with empty configuration
        assert import_processor._is_substitute_player("John Doe", "1") is False

        # Test with None name
        assert import_processor._is_substitute_player(None, "1") is False

        # Test with configured substitute name
        with patch("app.services.import_services.import_processor.SUBSTITUTE_PLAYER_NAMES", ["john doe"]):
            assert import_processor._is_substitute_player("John Doe", "1") is True
            assert import_processor._is_substitute_player("JOHN DOE", "1") is True

    def test_substitute_player_creation(self, import_processor, mock_db):
        """Test that substitute players are created correctly."""
        # Setup
        team = Team(id=1, name="Green Team")
        mock_db.query.return_value.filter.return_value.first.return_value = team

        player_stats = Mock()
        player_stats.team_name = "Green Team"
        player_stats.jersey_number = "0"
        player_stats.player_name = "Sub Player"
        # Mock quarter data
        for q in ["quarter_1", "quarter_2", "quarter_3", "quarter_4", "overtime"]:
            setattr(player_stats, q, "")

        # Mock substitute detection
        import_processor._is_substitute_player = Mock(return_value=True)

        # Mock player service
        mock_player = Player(id=3, name="Sub Player", jersey_number="0", is_substitute=True)
        import_processor.player_service.get_or_create_substitute_player.return_value = mock_player

        # Mock stats service
        import_processor.stats_service.add_player_quarter_stats.return_value = True

        # Act
        result = import_processor._process_player_game_stats(Mock(), player_stats)

        # Assert
        assert result is True
        import_processor.player_service.get_or_create_substitute_player.assert_called_once_with(
            jersey_number="0", player_name="Sub Player"
        )

    def test_regular_player_handling(self, import_processor, mock_db):
        """Test that regular players are handled normally."""
        # Setup
        team = Team(id=1, name="Blue Team")
        mock_db.query.return_value.filter.return_value.first.return_value = team

        player_stats = Mock()
        player_stats.team_name = "Blue Team"
        player_stats.jersey_number = "23"
        player_stats.player_name = "Michael Jordan"
        # Mock quarter data
        for q in ["quarter_1", "quarter_2", "quarter_3", "quarter_4", "overtime"]:
            setattr(player_stats, q, "")

        # Mock player service
        mock_player = Player(id=4, name="Michael Jordan", jersey_number="23")
        import_processor.player_service.get_or_create_player.return_value = mock_player

        # Mock stats service
        import_processor.stats_service.add_player_quarter_stats.return_value = True

        # Act
        result = import_processor._process_player_game_stats(Mock(), player_stats)

        # Assert
        assert result is True
        import_processor.player_service.get_or_create_player.assert_called_once_with(
            team_id=1, jersey_number="23", player_name="Michael Jordan"
        )


class TestPlayerServiceSubstitutes:
    """Test cases for PlayerService substitute functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock(spec=Session)
        db.query = Mock()
        db.add = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def player_service(self, mock_db):
        """Create a PlayerService instance."""
        return PlayerService(mock_db)

    def test_get_or_create_substitute_player_new(self, player_service, mock_db):
        """Test creating a new substitute player."""
        # Mock no existing guest team
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        # Mock guest team creation
        with patch("app.services.player_service.get_team_by_name", return_value=None):
            # Act
            result = player_service.get_or_create_substitute_player("00", "John Sub")

            # Assert that guest team was created
            assert mock_db.add.called
            assert mock_db.commit.called

    def test_get_or_create_substitute_player_existing(self, player_service, mock_db):
        """Test retrieving an existing substitute player."""
        # Mock existing guest team
        guest_team = Team(id=99, name="Guest Players")

        # Mock existing substitute player
        existing_player = Player(id=10, team_id=99, name="John Sub", jersey_number="00", is_substitute=True)

        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            guest_team,  # First call for team
            existing_player,  # Second call for player
        ]

        with patch("app.services.player_service.get_team_by_name", return_value=guest_team):
            # Act
            result = player_service.get_or_create_substitute_player("00", "John Sub")

            # Assert
            assert result == existing_player
            assert not mock_db.add.called  # Should not create new player

    def test_substitute_player_default_name(self, player_service, mock_db):
        """Test that substitute players get default names when not provided."""
        # Mock guest team
        guest_team = Team(id=99, name="Guest Players")
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            guest_team,  # First call for team
            None,  # No existing player
        ]

        with patch("app.services.player_service.get_team_by_name", return_value=guest_team):
            # Act with empty name
            result = player_service.get_or_create_substitute_player("1", "")

            # Assert default name was used
            added_player = mock_db.add.call_args[0][0]
            assert added_player.name == "Sub #1"

            # Act with "unknown" name
            mock_db.reset_mock()
            mock_db.query.return_value.filter_by.return_value.first.side_effect = [None]
            result = player_service.get_or_create_substitute_player("2", "Unknown")

            # Assert default name was used
            added_player = mock_db.add.call_args[0][0]
            assert added_player.name == "Sub #2"
