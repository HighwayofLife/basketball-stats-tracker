"""
Integration tests for the CSV import flow.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

import app.data_access.database_manager as db_manager
from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team
from app.services.csv_import_service import import_game_stats_from_csv


@pytest.fixture
def setup_import_test(db_session, sample_game_csv_file, test_shot_mapping):
    """Set up the test environment for CSV import testing."""
    return {"db_session": db_session, "csv_file_path": sample_game_csv_file, "shot_mapping": test_shot_mapping}


@pytest.fixture
def mock_db_manager(db_session):
    """Mock the database manager to use the test session."""

    @contextmanager
    def get_db_session_mock():
        try:
            yield db_session
        finally:
            pass

    # Create a mock of the database manager
    mock_manager = MagicMock()
    mock_manager.get_db_session = get_db_session_mock

    # Patch the database manager
    original_manager = db_manager.db_manager
    db_manager.db_manager = mock_manager

    yield mock_manager

    # Restore the original database manager
    db_manager.db_manager = original_manager


class TestCSVImport:
    """Integration tests for the CSV import functionality."""

    def test_import_game_stats_from_csv(self, setup_import_test, mock_db_manager):
        """Test importing game stats from CSV file."""
        # Create valid CSV content
        valid_csv_content = """GAME_INFO_KEY,VALUE
Playing Team,Team A
Opponent Team,Team B
Date,2025-05-01
PLAYER_STATS_HEADER,Team Name,Player Jersey,Player Name,Fouls,QT1 Shots,QT2 Shots,QT3 Shots,QT4 Shots
PLAYER_DATA,Team A,10,Player One,2,22-1x,3/2,11,
PLAYER_DATA,Team A,23,Player Two,1,1,2-2,3/,22
PLAYER_DATA,Team B,5,Player Alpha,3,3-,1,/3,
PLAYER_DATA,Team B,15,Player Beta,4,//-,2-,11x,3
"""
        # Mock the _check_file_exists function to return a Path object
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        # Run import with mocked database manager and file content
        with (
            patch("app.services.csv_import_service._check_file_exists", return_value=mock_path),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = valid_csv_content
            result = import_game_stats_from_csv(
                "valid_path.csv"  # This path doesn't matter due to mocking
            )

        # Assertions for successful import
        assert result is True

        # Check that teams are created
        db_session = setup_import_test["db_session"]
        teams = db_session.query(Team).all()
        assert len(teams) == 2
        team_names = [team.name for team in teams]
        assert "Team A" in team_names
        assert "Team B" in team_names

        # Check that players are created
        players = db_session.query(Player).all()
        assert len(players) == 4
        player_names = [player.name for player in players]
        assert "Player One" in player_names
        assert "Player Two" in player_names
        assert "Player Alpha" in player_names
        assert "Player Beta" in player_names

        # Check that the game is created
        game = db_session.query(Game).first()
        assert game is not None
        assert game.date == "2025-05-01"

        # Check that player game stats are created
        player_game_stats = db_session.query(PlayerGameStats).all()
        assert len(player_game_stats) == 4

        # Check that player quarter stats are created
        player_quarter_stats = db_session.query(PlayerQuarterStats).all()
        assert len(player_quarter_stats) > 0  # Should have multiple quarter entries

    def test_import_game_stats_from_invalid_csv(self, setup_import_test, mock_db_manager):
        """Test importing game stats from an invalid CSV file."""
        # Create invalid CSV file - missing required headers
        invalid_csv_content = """GAME_INFO_KEY,VALUE
Playing Team,Team A
Date,2025-05-01
PLAYER_STATS_HEADER,Team Name,Player Jersey,Player Name,Fouls,QT1 Shots,QT2 Shots,QT3 Shots,QT4 Shots
PLAYER_DATA,Team A,10,Player One,2,22-1x,3/2,11,
"""
        # Mock the _check_file_exists function to return a Path object
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with (
            patch("app.services.csv_import_service._check_file_exists", return_value=mock_path),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = invalid_csv_content
            result = import_game_stats_from_csv(
                "invalid_path.csv"  # This path doesn't matter due to mocking
            )

            # Assertions for failed import
            assert result is False

            # Since the import failed, we need to check that no data was created
            # Check that no data is imported
            db_session = setup_import_test["db_session"]
            teams_count = db_session.query(Team).count()
            assert teams_count == 0

            players_count = db_session.query(Player).count()
            assert players_count == 0

            games_count = db_session.query(Game).count()
            assert games_count == 0
