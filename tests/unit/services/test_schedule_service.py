"""Unit tests for ScheduleService."""

from datetime import date, time
from unittest.mock import MagicMock, patch

import pytest

from app.data_access.models import ScheduledGame, ScheduledGameStatus
from app.services.schedule_service import ScheduleService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def schedule_service():
    """Create a ScheduleService instance."""
    return ScheduleService()


@pytest.fixture
def mock_crud_scheduled_game():
    """Mock the crud_scheduled_game module."""
    with patch("app.services.schedule_service.crud_scheduled_game") as mock_crud:
        yield mock_crud


class TestScheduleService:
    """Test cases for ScheduleService."""

    def test_create_scheduled_game(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test creating a scheduled game."""
        # Arrange
        home_team_id = 1
        away_team_id = 2
        scheduled_date = date(2025, 6, 15)
        scheduled_time = time(19, 30)
        location = "Test Arena"
        notes = "Test game"

        mock_crud_scheduled_game.find_matching_game.return_value = None

        expected_game = ScheduledGame(
            id=1,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            location=location,
            notes=notes,
            status=ScheduledGameStatus.SCHEDULED,
        )

        mock_crud_scheduled_game.create.return_value = expected_game

        # Act
        result = schedule_service.create_scheduled_game(
            db=mock_db_session,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            location=location,
            notes=notes,
        )

        # Assert
        assert result == expected_game
        mock_crud_scheduled_game.find_matching_game.assert_called_once_with(
            mock_db_session, scheduled_date, home_team_id, away_team_id
        )
        mock_crud_scheduled_game.create.assert_called_once()

    def test_create_scheduled_game_same_teams(self, schedule_service, mock_db_session):
        """Test creating a scheduled game with same home and away team."""
        # Act & Assert
        with pytest.raises(ValueError, match="Home team and away team cannot be the same"):
            schedule_service.create_scheduled_game(
                db=mock_db_session, home_team_id=1, away_team_id=1, scheduled_date=date(2025, 6, 15)
            )

    def test_create_scheduled_game_already_exists(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test creating a scheduled game that already exists."""
        # Arrange
        existing_game = ScheduledGame(id=1, scheduled_date=date(2025, 6, 15))
        mock_crud_scheduled_game.find_matching_game.return_value = existing_game

        # Act & Assert
        with pytest.raises(ValueError, match="A scheduled game already exists between these teams"):
            schedule_service.create_scheduled_game(
                db=mock_db_session, home_team_id=1, away_team_id=2, scheduled_date=date(2025, 6, 15)
            )

    def test_get_scheduled_game(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test getting a specific scheduled game."""
        # Arrange
        game_id = 1
        expected_game = ScheduledGame(
            id=game_id, scheduled_date=date(2025, 6, 15), status=ScheduledGameStatus.SCHEDULED
        )

        mock_crud_scheduled_game.get_by_id.return_value = expected_game

        # Act
        result = schedule_service.get_scheduled_game(mock_db_session, game_id)

        # Assert
        assert result == expected_game
        mock_crud_scheduled_game.get_by_id.assert_called_once_with(mock_db_session, game_id)

    def test_get_all_scheduled_games(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test getting all scheduled games."""
        # Arrange
        games = [
            ScheduledGame(id=1, scheduled_date=date(2025, 6, 15)),
            ScheduledGame(id=2, scheduled_date=date(2025, 6, 20)),
        ]

        mock_crud_scheduled_game.get_all.return_value = games

        # Act
        result = schedule_service.get_all_scheduled_games(mock_db_session, skip=0, limit=100)

        # Assert
        assert result == games
        mock_crud_scheduled_game.get_all.assert_called_once_with(mock_db_session, skip=0, limit=100)

    def test_get_upcoming_games(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test getting upcoming games."""
        # Arrange
        upcoming_games = [
            ScheduledGame(id=1, scheduled_date=date(2025, 6, 15), status=ScheduledGameStatus.SCHEDULED),
            ScheduledGame(id=2, scheduled_date=date(2025, 6, 20), status=ScheduledGameStatus.SCHEDULED),
        ]

        mock_crud_scheduled_game.get_upcoming.return_value = upcoming_games

        # Act
        result = schedule_service.get_upcoming_games(mock_db_session, limit=30)

        # Assert
        assert result == upcoming_games
        mock_crud_scheduled_game.get_upcoming.assert_called_once_with(mock_db_session, limit=30)

    def test_get_next_games(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test getting the next N games."""
        # Arrange
        next_games = [
            ScheduledGame(id=1, scheduled_date=date(2025, 6, 15)),
            ScheduledGame(id=2, scheduled_date=date(2025, 6, 16)),
            ScheduledGame(id=3, scheduled_date=date(2025, 6, 17)),
        ]

        mock_crud_scheduled_game.get_upcoming.return_value = next_games

        # Act
        result = schedule_service.get_next_games(mock_db_session, count=3)

        # Assert
        assert result == next_games
        mock_crud_scheduled_game.get_upcoming.assert_called_once_with(mock_db_session, limit=3)

    def test_get_games_by_status(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test getting games filtered by status."""
        # Arrange
        status = ScheduledGameStatus.POSTPONED

        postponed_games = [ScheduledGame(id=1, scheduled_date=date(2025, 6, 15), status=ScheduledGameStatus.POSTPONED)]

        mock_crud_scheduled_game.get_by_status.return_value = postponed_games

        # Act
        result = schedule_service.get_games_by_status(mock_db_session, status)

        # Assert
        assert result == postponed_games
        mock_crud_scheduled_game.get_by_status.assert_called_once_with(mock_db_session, status)

    def test_update_scheduled_game(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test updating a scheduled game."""
        # Arrange
        game_id = 1
        new_date = date(2025, 6, 20)
        new_time = time(20, 0)
        new_location = "New Arena"

        updated_game = ScheduledGame(
            id=game_id,
            scheduled_date=new_date,
            scheduled_time=new_time,
            location=new_location,
            status=ScheduledGameStatus.SCHEDULED,
        )

        mock_crud_scheduled_game.update.return_value = updated_game

        # Act
        result = schedule_service.update_scheduled_game(
            mock_db_session,
            scheduled_game_id=game_id,
            scheduled_date=new_date,
            scheduled_time=new_time,
            location=new_location,
        )

        # Assert
        assert result == updated_game
        mock_crud_scheduled_game.update.assert_called_once_with(
            mock_db_session, game_id, scheduled_date=new_date, scheduled_time=new_time, location=new_location
        )

    def test_cancel_scheduled_game(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test canceling a scheduled game."""
        # Arrange
        game_id = 1

        cancelled_game = ScheduledGame(id=game_id, status=ScheduledGameStatus.CANCELLED, notes="Weather conditions")

        mock_crud_scheduled_game.cancel.return_value = cancelled_game

        # Act
        result = schedule_service.cancel_scheduled_game(mock_db_session, game_id)

        # Assert
        assert result == cancelled_game
        mock_crud_scheduled_game.cancel.assert_called_once_with(mock_db_session, game_id)

    def test_link_game_to_schedule(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test linking a completed game to its scheduled entry."""
        # Arrange
        scheduled_game_id = 1
        game_id = 100

        updated_game = ScheduledGame(id=scheduled_game_id, status=ScheduledGameStatus.COMPLETED, game_id=game_id)

        mock_crud_scheduled_game.mark_completed.return_value = updated_game

        # Act
        result = schedule_service.link_game_to_schedule(mock_db_session, scheduled_game_id, game_id)

        # Assert
        assert result == updated_game
        mock_crud_scheduled_game.mark_completed.assert_called_once_with(mock_db_session, scheduled_game_id, game_id)

    def test_find_matching_scheduled_game(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test finding a matching scheduled game."""
        # Arrange
        game_date = date(2025, 6, 15)
        team1_name = "Lakers"
        team2_name = "Warriors"

        expected_game = ScheduledGame(id=1, scheduled_date=game_date, status=ScheduledGameStatus.SCHEDULED)

        mock_crud_scheduled_game.find_matching_game.return_value = expected_game

        # Act
        result = schedule_service.find_matching_scheduled_game(mock_db_session, game_date, team1_name, team2_name)

        # Assert
        assert result == expected_game
        mock_crud_scheduled_game.find_matching_game.assert_called_once_with(
            mock_db_session, game_date, team1_name, team2_name
        )

    def test_delete_scheduled_game(self, schedule_service, mock_db_session, mock_crud_scheduled_game):
        """Test deleting a scheduled game."""
        # Arrange
        game_id = 1
        mock_crud_scheduled_game.delete.return_value = True

        # Act
        result = schedule_service.delete_scheduled_game(mock_db_session, game_id)

        # Assert
        assert result is True
        mock_crud_scheduled_game.delete.assert_called_once_with(mock_db_session, game_id)
