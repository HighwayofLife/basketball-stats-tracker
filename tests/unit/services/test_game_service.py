"""
Test module for the GameService.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.data_access.models import Game, Team
from app.services.game_service import GameService


class TestGameService:
    """Tests for the GameService."""

    def test_init(self, db_session):
        """Test initializing the game service."""
        service = GameService(db_session)
        assert service._db_session == db_session

    def test_get_or_create_team_existing(self, db_session):
        """Test getting an existing team."""
        # Mock the db session and CRUD function
        mock_get_team = MagicMock(return_value=Team(id=1, name="Existing Team"))

        with patch("app.services.game_service.get_team_by_name", mock_get_team):
            service = GameService(db_session)
            team = service.get_or_create_team("Existing Team")

            assert team.id == 1
            assert team.name == "Existing Team"
            mock_get_team.assert_called_once_with(db_session, "Existing Team")

    def test_get_or_create_team_new(self, db_session):
        """Test creating a new team."""
        # Mock the db session and CRUD functions
        mock_get_team = MagicMock(return_value=None)
        mock_create_team = MagicMock(return_value=Team(id=2, name="New Team"))

        with (
            patch("app.services.game_service.get_team_by_name", mock_get_team),
            patch("app.services.game_service.create_team", mock_create_team),
        ):
            service = GameService(db_session)
            team = service.get_or_create_team("New Team")

            assert team.id == 2
            assert team.name == "New Team"
            mock_get_team.assert_called_once_with(db_session, "New Team")
            mock_create_team.assert_called_once_with(db_session, "New Team")

    def test_list_all_teams(self, db_session):
        """Test listing all teams."""
        # Mock the db session and CRUD function
        mock_teams = [Team(id=1, name="Team A"), Team(id=2, name="Team B"), Team(id=3, name="Team C")]
        mock_get_all_teams = MagicMock(return_value=mock_teams)

        with patch("app.services.game_service.get_all_teams", mock_get_all_teams):
            service = GameService(db_session)
            teams = service.list_all_teams()

            assert len(teams) == 3
            assert teams[0].id == 1
            assert teams[1].id == 2
            assert teams[2].id == 3
            mock_get_all_teams.assert_called_once_with(db_session)

    def test_add_game_new_teams(self, db_session):
        """Test adding a game with teams that need to be created."""
        # Mock the CRUD functions
        mock_get_team = MagicMock(return_value=None)
        mock_create_team_a = MagicMock(return_value=Team(id=1, name="Team A"))
        mock_create_team_b = MagicMock(return_value=Team(id=2, name="Team B"))

        # Convert string date to date object for test
        test_date = datetime.strptime("2025-05-01", "%Y-%m-%d").date()
        mock_create_game = MagicMock(return_value=Game(id=1, date=test_date, playing_team_id=1, opponent_team_id=2))

        with (
            patch("app.services.game_service.get_team_by_name", mock_get_team),
            patch(
                "app.services.game_service.create_team",
                side_effect=[mock_create_team_a.return_value, mock_create_team_b.return_value],
            ),
            patch("app.services.game_service.create_game", mock_create_game),
        ):
            service = GameService(db_session)
            game = service.add_game("2025-05-01", "Team A", "Team B")

            assert game.id == 1
            assert game.date == test_date
            assert game.playing_team_id == 1
            assert game.opponent_team_id == 2
            mock_create_game.assert_called_once_with(db_session, "2025-05-01", 1, 2)
            assert game.opponent_team_id == 2
            mock_create_game.assert_called_once_with(db_session, "2025-05-01", 1, 2)

    def test_add_game_existing_teams(self, db_session):
        """Test adding a game with existing teams."""
        # Mock the CRUD functions
        mock_get_team_a = MagicMock(return_value=Team(id=1, name="Team A"))
        mock_get_team_b = MagicMock(return_value=Team(id=2, name="Team B"))

        # Convert string date to date object for test
        test_date = datetime.strptime("2025-05-01", "%Y-%m-%d").date()
        mock_create_game = MagicMock(return_value=Game(id=1, date=test_date, playing_team_id=1, opponent_team_id=2))

        def mock_get_team_side_effect(db_session, team_name):
            if team_name == "Team A":
                return mock_get_team_a.return_value
            elif team_name == "Team B":
                return mock_get_team_b.return_value
            return None

        with (
            patch("app.services.game_service.get_team_by_name", side_effect=mock_get_team_side_effect),
            patch("app.services.game_service.create_game", mock_create_game),
        ):
            service = GameService(db_session)
            game = service.add_game("2025-05-01", "Team A", "Team B")

            assert game.id == 1
            assert game.date == test_date
            assert game.playing_team_id == 1
            assert game.opponent_team_id == 2
            mock_create_game.assert_called_once_with(db_session, "2025-05-01", 1, 2)
