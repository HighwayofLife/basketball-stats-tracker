"""Unit tests for report-related CLI command handlers."""

from datetime import date
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.services.cli_commands.report_commands import ReportCommands


class TestReportCommands:
    """Test report-related CLI commands."""

    @pytest.fixture
    def mock_game(self):
        """Create a mock game object."""
        game = MagicMock()
        game.id = 1
        game.date = date(2024, 12, 1)
        game.playing_team_id = 1
        game.opponent_team_id = 2
        game.playing_team.name = "Lakers"
        game.opponent_team.name = "Warriors"
        return game

    @pytest.fixture
    def mock_player(self):
        """Create a mock player object."""
        player = MagicMock()
        player.id = 1
        player.name = "John Doe"
        player.team.name = "Lakers"
        return player

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.ReportService")
    def test_generate_report_game_not_found(self, mock_report_service_class, mock_get_session, capsys):
        """Test report generation when game is not found."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_report_service = MagicMock()
        mock_report_service_class.return_value = mock_report_service
        mock_report_service.generate_game_report.return_value = (
            False,
            {"suggestions": [{"id": 1, "date": "2024-12-01", "info": "Lakers vs Warriors", "status": "Played"}]},
            "Game ID 999 not found",
        )

        # Execute
        ReportCommands.generate_report(game_id=999)

        # Verify
        captured = capsys.readouterr()
        assert "Error: Game ID 999 not found" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.ReportService")
    def test_generate_report_show_options(self, mock_report_service_class, mock_get_session, mock_game, capsys):
        """Test showing report options for a game."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_report_service = MagicMock()
        mock_report_service_class.return_value = mock_report_service
        mock_report_service.get_game_or_suggestions.return_value = (mock_game, None)
        mock_report_service.get_report_options.return_value = {
            "game": {"id": 1, "playing_team": "Lakers", "opponent_team": "Warriors", "date": "2024-12-01"},
            "available_reports": [
                {"type": "box-score", "description": "Traditional box score"},
                {"type": "player-performance", "description": "Player performance", "requires": "player"},
                {"type": "team-efficiency", "description": "Team efficiency", "requires": "team"},
            ],
            "teams": [{"id": 1, "name": "Lakers"}, {"id": 2, "name": "Warriors"}],
            "players": {},
            "has_stats": False,
        }

        # Execute
        ReportCommands.generate_report(game_id=1, show_options=True)

        # Verify
        captured = capsys.readouterr()
        assert "Available reports for Game 1" in captured.out
        assert "box-score" in captured.out
        assert "player-performance" in captured.out
        assert "team-efficiency" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.ReportService")
    def test_generate_box_score_report(self, mock_report_service_class, mock_get_session, mock_game, capsys):
        """Test box score report generation."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_report_service = MagicMock()
        mock_report_service_class.return_value = mock_report_service
        mock_report_service.generate_game_report.return_value = (
            True,
            {
                "player_stats": [{"name": "John Doe", "points": 20}],
                "game_summary": {"team_points": 100},
                "_game": mock_game,
                "_report_type": "box-score",
            },
            None,
        )

        # Execute
        ReportCommands.generate_report(game_id=1, report_type="box-score")

        # Verify
        captured = capsys.readouterr()
        assert "Box Score Report" in captured.out
        assert "Lakers vs Warriors" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.ReportService")
    def test_generate_player_performance_no_player_id(
        self, mock_report_service_class, mock_get_session, mock_game, capsys
    ):
        """Test player performance report without player ID."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_report_service = MagicMock()
        mock_report_service_class.return_value = mock_report_service
        mock_report_service.generate_game_report.return_value = (
            False,
            None,
            "Player ID is required for player-performance report",
        )

        # Execute
        ReportCommands.generate_report(game_id=1, report_type="player-performance")

        # Verify
        captured = capsys.readouterr()
        assert "Error: Player ID is required" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.ReportService")
    def test_generate_season_standings_report(self, mock_report_service_class, mock_get_session, capsys):
        """Test season standings report generation."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_report_service = MagicMock()
        mock_report_service_class.return_value = mock_report_service
        mock_report_service.generate_season_report.return_value = (
            True,
            {"standings": [{"team": "Lakers", "wins": 10, "losses": 5}], "_report_type": "standings"},
            None,
        )

        # Execute
        ReportCommands.generate_season_report(report_type="standings")

        # Verify
        captured = capsys.readouterr()
        assert "Team Standings" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.ReportService")
    def test_generate_season_report_csv_output(self, mock_report_service_class, mock_get_session):
        """Test season report with CSV output."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_report_service = MagicMock()
        mock_report_service_class.return_value = mock_report_service
        mock_report_service.generate_season_report.return_value = (
            True,
            {"standings": [{"team": "Lakers", "wins": 10, "losses": 5}], "_report_type": "standings"},
            None,
        )

        # Mock file operations
        m = mock_open()
        with patch("builtins.open", m):
            # Execute
            ReportCommands.generate_season_report(
                report_type="standings", output_format="csv", output_file="standings.csv"
            )

        # Verify file was written
        m.assert_called_once_with("standings.csv", "w", newline="", encoding="utf-8")

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.ReportService")
    def test_generate_player_season_report_no_player(self, mock_report_service_class, mock_get_session, capsys):
        """Test player season report when player not found."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_report_service = MagicMock()
        mock_report_service_class.return_value = mock_report_service
        mock_report_service.generate_season_report.return_value = (
            False,
            None,
            "Player ID is required for player-season report",
        )

        # Execute
        ReportCommands.generate_season_report(report_type="player-season", player_id=999)

        # Verify
        captured = capsys.readouterr()
        assert "Error: Player ID is required for player-season report" in captured.out
