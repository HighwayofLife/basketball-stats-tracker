"""
Unit tests for crud_game module.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.data_access.crud import crud_game
from app.data_access.models import Game


class TestCrudGame:
    """Test cases for crud_game module."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def sample_game(self):
        """Create a sample game object."""
        game = MagicMock(spec=Game)
        game.id = 1
        game.date = datetime.strptime("2025-05-01", "%Y-%m-%d").date()
        game.playing_team_id = 1
        game.opponent_team_id = 2
        return game

    def test_create_game(self, mock_db_session):
        """Test creating a new game."""
        # Arrange
        date_str = "2025-05-01"
        playing_team_id = 1
        opponent_team_id = 2

        # Mock the database operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.side_effect = lambda game: setattr(game, "id", 1)

        # Act
        result = crud_game.create_game(mock_db_session, date_str, playing_team_id, opponent_team_id)

        # Assert
        assert result.id == 1
        assert result.date == datetime.strptime(date_str, "%Y-%m-%d").date()
        assert result.playing_team_id == playing_team_id
        assert result.opponent_team_id == opponent_team_id
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    def test_create_game_invalid_date_format(self, mock_db_session):
        """Test creating a game with invalid date format."""
        # Arrange
        invalid_date_str = "2025/05/01"  # Wrong format
        playing_team_id = 1
        opponent_team_id = 2

        # Act & Assert
        with pytest.raises(ValueError):
            crud_game.create_game(mock_db_session, invalid_date_str, playing_team_id, opponent_team_id)

    def test_get_game_by_id_found(self, mock_db_session, sample_game):
        """Test getting a game by ID when it exists."""
        # Arrange
        game_id = 1
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_game
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_game.get_game_by_id(mock_db_session, game_id)

        # Assert
        assert result == sample_game
        mock_db_session.query.assert_called_once_with(Game)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_game_by_id_not_found(self, mock_db_session):
        """Test getting a game by ID when it doesn't exist."""
        # Arrange
        game_id = 999
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_game.get_game_by_id(mock_db_session, game_id)

        # Assert
        assert result is None
        mock_db_session.query.assert_called_once_with(Game)
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()

    def test_get_games_by_team(self, mock_db_session):
        """Test getting games by team ID."""
        # Arrange
        team_id = 1
        game1 = MagicMock(spec=Game)
        game1.id = 1
        game1.playing_team_id = 1
        game1.opponent_team_id = 2

        game2 = MagicMock(spec=Game)
        game2.id = 2
        game2.playing_team_id = 3
        game2.opponent_team_id = 1

        expected_games = [game1, game2]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = expected_games
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_game.get_games_by_team(mock_db_session, team_id)

        # Assert
        assert result == expected_games
        assert len(result) == 2
        mock_db_session.query.assert_called_once_with(Game)
        mock_query.filter.assert_called_once()
        mock_filter.all.assert_called_once()

    def test_get_games_by_team_no_games(self, mock_db_session):
        """Test getting games by team ID when no games exist."""
        # Arrange
        team_id = 999
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_game.get_games_by_team(mock_db_session, team_id)

        # Assert
        assert result == []
        mock_db_session.query.assert_called_once_with(Game)
        mock_query.filter.assert_called_once()
        mock_filter.all.assert_called_once()

    def test_get_games_by_date_range(self, mock_db_session):
        """Test getting games within a date range."""
        # Arrange
        start_date = "2025-05-01"
        end_date = "2025-05-31"

        game1 = MagicMock(spec=Game)
        game1.id = 1
        game1.date = datetime.strptime("2025-05-10", "%Y-%m-%d").date()

        game2 = MagicMock(spec=Game)
        game2.id = 2
        game2.date = datetime.strptime("2025-05-20", "%Y-%m-%d").date()

        expected_games = [game1, game2]

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = expected_games
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_game.get_games_by_date_range(mock_db_session, start_date, end_date)

        # Assert
        assert result == expected_games
        assert len(result) == 2
        mock_db_session.query.assert_called_once_with(Game)
        mock_query.filter.assert_called_once()
        mock_filter.all.assert_called_once()

    def test_get_games_by_date_range_no_games(self, mock_db_session):
        """Test getting games within a date range when no games exist."""
        # Arrange
        start_date = "2025-05-01"
        end_date = "2025-05-31"

        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Act
        result = crud_game.get_games_by_date_range(mock_db_session, start_date, end_date)

        # Assert
        assert result == []
        mock_db_session.query.assert_called_once_with(Game)
        mock_query.filter.assert_called_once()
        mock_filter.all.assert_called_once()

    def test_get_games_by_date_range_invalid_date_format(self, mock_db_session):
        """Test getting games with invalid date format."""
        # Arrange
        invalid_start_date = "05/01/2025"  # Wrong format
        end_date = "2025-05-31"

        # Act & Assert
        with pytest.raises(ValueError):
            crud_game.get_games_by_date_range(mock_db_session, invalid_start_date, end_date)
