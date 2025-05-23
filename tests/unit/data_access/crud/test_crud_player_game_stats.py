"""
Unit tests for crud_player_game_stats module.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.data_access.crud import crud_player_game_stats
from app.data_access.models import PlayerGameStats


class TestCrudPlayerGameStats:
    """Test cases for crud_player_game_stats module."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def sample_player_game_stats(self):
        """Create a sample player game stats object."""
        stats = MagicMock(spec=PlayerGameStats)
        stats.id = 1
        stats.game_id = 1
        stats.player_id = 1
        stats.fouls = 3
        stats.total_ftm = 5
        stats.total_fta = 6
        stats.total_2pm = 4
        stats.total_2pa = 8
        stats.total_3pm = 2
        stats.total_3pa = 5
        return stats

    def test_create_player_game_stats(self, mock_db_session):
        """Test creating a new player game stats record."""
        # Arrange
        game_id = 1
        player_id = 1
        fouls = 3

        # Mock the database operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.side_effect = lambda stats: setattr(stats, "id", 1)

        # Act
        result = crud_player_game_stats.create_player_game_stats(mock_db_session, game_id, player_id, fouls)

        # Assert
        assert result.id == 1
        assert result.game_id == game_id
        assert result.player_id == player_id
        assert result.fouls == fouls
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    def test_update_player_game_stats_totals(self, mock_db_session, sample_player_game_stats):
        """Test updating player game stats totals."""
        # Arrange
        player_game_stat_id = 1
        totals = {"total_ftm": 7, "total_fta": 8, "total_2pm": 5, "total_2pa": 10, "total_3pm": 3, "total_3pa": 6}

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_player_game_stats
        mock_db_session.query.return_value = mock_query
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        result = crud_player_game_stats.update_player_game_stats_totals(mock_db_session, player_game_stat_id, totals)

        # Assert
        assert result == sample_player_game_stats
        mock_db_session.query.assert_called_once_with(PlayerGameStats)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(sample_player_game_stats)

        # Verify the stats were updated
        for key, _value in totals.items():
            assert hasattr(sample_player_game_stats, key)

    def test_update_player_game_stats_totals_not_found(self, mock_db_session):
        """Test updating player game stats totals when record not found."""
        # Arrange
        player_game_stat_id = 999
        totals = {"total_ftm": 7}

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            crud_player_game_stats.update_player_game_stats_totals(mock_db_session, player_game_stat_id, totals)

        assert f"PlayerGameStats with ID {player_game_stat_id} not found" in str(excinfo.value)
        mock_db_session.query.assert_called_once_with(PlayerGameStats)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_player_game_stats_by_game(self, mock_db_session):
        """Test getting all player game stats for a specific game."""
        # Arrange
        game_id = 1

        stats1 = MagicMock(spec=PlayerGameStats)
        stats1.id = 1
        stats1.game_id = game_id
        stats1.player_id = 1

        stats2 = MagicMock(spec=PlayerGameStats)
        stats2.id = 2
        stats2.game_id = game_id
        stats2.player_id = 2

        expected_stats = [stats1, stats2]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = expected_stats
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_game_stats.get_player_game_stats_by_game(mock_db_session, game_id)

        # Assert
        assert result == expected_stats
        assert len(result) == 2
        mock_db_session.query.assert_called_once_with(PlayerGameStats)
        mock_query.filter.assert_called_once()
        mock_filter.all.assert_called_once()

    def test_get_player_game_stats_by_game_no_stats(self, mock_db_session):
        """Test getting player game stats when no stats exist for the game."""
        # Arrange
        game_id = 999

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_game_stats.get_player_game_stats_by_game(mock_db_session, game_id)

        # Assert
        assert result == []
        mock_db_session.query.assert_called_once_with(PlayerGameStats)
        mock_query.filter.assert_called_once()
        mock_filter.all.assert_called_once()

    def test_get_player_game_stats(self, mock_db_session, sample_player_game_stats):
        """Test getting a specific player's game stats."""
        # Arrange
        game_id = 1
        player_id = 1

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_player_game_stats
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_game_stats.get_player_game_stats(mock_db_session, game_id, player_id)

        # Assert
        assert result == sample_player_game_stats
        mock_db_session.query.assert_called_once_with(PlayerGameStats)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_player_game_stats_not_found(self, mock_db_session):
        """Test getting player game stats when not found."""
        # Arrange
        game_id = 999
        player_id = 999

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_game_stats.get_player_game_stats(mock_db_session, game_id, player_id)

        # Assert
        assert result is None
        mock_db_session.query.assert_called_once_with(PlayerGameStats)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()
