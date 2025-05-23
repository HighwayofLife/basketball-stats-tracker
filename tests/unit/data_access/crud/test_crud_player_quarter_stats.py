"""
Unit tests for crud_player_quarter_stats module.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.data_access.crud import crud_player_quarter_stats
from app.data_access.models import PlayerQuarterStats


class TestCrudPlayerQuarterStats:
    """Test cases for crud_player_quarter_stats module."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def sample_quarter_stats(self):
        """Create a sample player quarter stats object."""
        stats = MagicMock(spec=PlayerQuarterStats)
        stats.id = 1
        stats.player_game_stat_id = 1
        stats.quarter_number = 1
        stats.ftm = 2
        stats.fta = 3
        stats.fg2m = 3
        stats.fg2a = 5
        stats.fg3m = 1
        stats.fg3a = 2
        return stats

    def test_create_player_quarter_stats(self, mock_db_session):
        """Test creating a new player quarter stats record."""
        # Arrange
        player_game_stat_id = 1
        quarter_number = 1
        stats = {"ftm": 2, "fta": 3, "fg2m": 3, "fg2a": 5, "fg3m": 1, "fg3a": 2}

        # Mock the database operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.side_effect = lambda qstats: setattr(qstats, "id", 1)

        # Act
        result = crud_player_quarter_stats.create_player_quarter_stats(
            mock_db_session, player_game_stat_id, quarter_number, stats
        )

        # Assert
        assert result.id == 1
        assert result.player_game_stat_id == player_game_stat_id
        assert result.quarter_number == quarter_number
        # Verify stats were set
        for key, value in stats.items():
            assert hasattr(result, key)
            assert getattr(result, key) == value

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    def test_create_player_quarter_stats_empty_stats(self, mock_db_session):
        """Test creating player quarter stats with empty stats dictionary."""
        # Arrange
        player_game_stat_id = 1
        quarter_number = 1
        stats = {}  # Empty stats

        # Mock the database operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.side_effect = lambda qstats: setattr(qstats, "id", 1)

        # Act
        result = crud_player_quarter_stats.create_player_quarter_stats(
            mock_db_session, player_game_stat_id, quarter_number, stats
        )

        # Assert
        assert result.id == 1
        assert result.player_game_stat_id == player_game_stat_id
        assert result.quarter_number == quarter_number
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    def test_get_player_quarter_stats(self, mock_db_session):
        """Test getting all quarter stats for a player game stats record."""
        # Arrange
        player_game_stat_id = 1

        # Create mock quarter stats for all 4 quarters
        quarter_stats_list = []
        for q in range(1, 5):
            stats = MagicMock(spec=PlayerQuarterStats)
            stats.id = q
            stats.player_game_stat_id = player_game_stat_id
            stats.quarter_number = q
            stats.ftm = q
            stats.fta = q + 1
            quarter_stats_list.append(stats)

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order_by = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.all.return_value = quarter_stats_list
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_quarter_stats.get_player_quarter_stats(mock_db_session, player_game_stat_id)

        # Assert
        assert result == quarter_stats_list
        assert len(result) == 4
        # Verify quarters are in order
        for i, stats in enumerate(result):
            assert stats.quarter_number == i + 1

        mock_db_session.query.assert_called_once_with(PlayerQuarterStats)
        mock_query.filter.assert_called_once()
        mock_filter.order_by.assert_called_once()
        mock_order_by.all.assert_called_once()

    def test_get_player_quarter_stats_no_stats(self, mock_db_session):
        """Test getting quarter stats when no stats exist."""
        # Arrange
        player_game_stat_id = 999

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order_by = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_quarter_stats.get_player_quarter_stats(mock_db_session, player_game_stat_id)

        # Assert
        assert result == []
        mock_db_session.query.assert_called_once_with(PlayerQuarterStats)
        mock_query.filter.assert_called_once()
        mock_filter.order_by.assert_called_once()
        mock_order_by.all.assert_called_once()

    def test_get_quarter_stats_by_quarter(self, mock_db_session, sample_quarter_stats):
        """Test getting a specific quarter's stats."""
        # Arrange
        player_game_stat_id = 1
        quarter_number = 1

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_quarter_stats
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_quarter_stats.get_quarter_stats_by_quarter(
            mock_db_session, player_game_stat_id, quarter_number
        )

        # Assert
        assert result == sample_quarter_stats
        assert result.quarter_number == quarter_number
        mock_db_session.query.assert_called_once_with(PlayerQuarterStats)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_quarter_stats_by_quarter_not_found(self, mock_db_session):
        """Test getting quarter stats when not found."""
        # Arrange
        player_game_stat_id = 999
        quarter_number = 1

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_quarter_stats.get_quarter_stats_by_quarter(
            mock_db_session, player_game_stat_id, quarter_number
        )

        # Assert
        assert result is None
        mock_db_session.query.assert_called_once_with(PlayerQuarterStats)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_quarter_stats_partial_quarters(self, mock_db_session):
        """Test getting quarter stats when only some quarters have data."""
        # Arrange
        player_game_stat_id = 1

        # Create mock quarter stats for only quarters 1 and 3
        quarter_stats_list = []
        for q in [1, 3]:
            stats = MagicMock(spec=PlayerQuarterStats)
            stats.id = q
            stats.player_game_stat_id = player_game_stat_id
            stats.quarter_number = q
            quarter_stats_list.append(stats)

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order_by = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order_by
        mock_order_by.all.return_value = quarter_stats_list
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_player_quarter_stats.get_player_quarter_stats(mock_db_session, player_game_stat_id)

        # Assert
        assert len(result) == 2
        assert result[0].quarter_number == 1
        assert result[1].quarter_number == 3
        mock_db_session.query.assert_called_once_with(PlayerQuarterStats)
        mock_query.filter.assert_called_once()
        mock_filter.order_by.assert_called_once()
        mock_order_by.all.assert_called_once()
