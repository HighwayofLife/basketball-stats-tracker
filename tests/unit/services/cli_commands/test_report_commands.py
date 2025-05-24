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
    @patch("app.services.cli_commands.report_commands.get_game_by_id")
    def test_generate_report_game_not_found(self, mock_get_game, mock_get_session, capsys):
        """Test report generation when game is not found."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_game.return_value = None

        # Execute
        ReportCommands.generate_report(game_id=999)

        # Verify
        captured = capsys.readouterr()
        assert "Error: Game ID 999 not found." in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.get_game_by_id")
    def test_generate_report_show_options(self, mock_get_game, mock_get_session, mock_game, capsys):
        """Test showing report options for a game."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_game.return_value = mock_game

        with patch("app.services.cli_commands.report_commands.get_player_game_stats_by_game") as mock_get_stats:
            mock_get_stats.return_value = []

            # Execute
            ReportCommands.generate_report(game_id=1, show_options=True)

        # Verify
        captured = capsys.readouterr()
        assert "Available reports for Game 1" in captured.out
        assert "box-score" in captured.out
        assert "player-performance" in captured.out
        assert "team-efficiency" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.get_game_by_id")
    @patch("app.services.cli_commands.report_commands.ReportGenerator")
    def test_generate_box_score_report(self, mock_report_gen_class, mock_get_game, mock_get_session, mock_game, capsys):
        """Test box score report generation."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_game.return_value = mock_game

        mock_report_gen = MagicMock()
        mock_report_gen.get_game_box_score_data.return_value = (
            [{"name": "John Doe", "points": 20}],
            {"team_points": 100},
        )
        mock_report_gen_class.return_value = mock_report_gen

        # Execute
        ReportCommands.generate_report(game_id=1, report_type="box-score")

        # Verify
        captured = capsys.readouterr()
        assert "Box Score Report" in captured.out
        assert "Lakers vs Warriors" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.get_game_by_id")
    def test_generate_player_performance_no_player_id(self, mock_get_game, mock_get_session, mock_game, capsys):
        """Test player performance report without player ID."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_game.return_value = mock_game

        # Execute
        ReportCommands.generate_report(game_id=1, report_type="player-performance")

        # Verify
        captured = capsys.readouterr()
        assert "Error: Player ID is required" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.SeasonStatsService")
    def test_generate_season_standings_report(self, mock_service_class, mock_get_session, capsys):
        """Test season standings report generation."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_service = MagicMock()
        mock_service.get_team_standings.return_value = [{"team_name": "Lakers", "wins": 10, "losses": 5}]
        mock_service_class.return_value = mock_service

        # Execute
        ReportCommands.generate_season_report(report_type="standings")

        # Verify
        captured = capsys.readouterr()
        assert "Team Standings" in captured.out

    @patch("app.services.cli_commands.report_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.report_commands.SeasonStatsService")
    def test_generate_season_report_csv_output(self, mock_service_class, mock_get_session):
        """Test season report with CSV output."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_service = MagicMock()
        mock_service.get_team_standings.return_value = [{"team_name": "Lakers", "wins": 10, "losses": 5}]
        mock_service_class.return_value = mock_service

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
    @patch("app.services.cli_commands.report_commands.get_player_by_id")
    def test_generate_player_season_report_no_player(self, mock_get_player, mock_get_session, capsys):
        """Test player season report when player not found."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_player.return_value = None

        # Execute
        ReportCommands.generate_season_report(report_type="player-season", player_id=999)

        # Verify
        captured = capsys.readouterr()
        assert "Error: Player with ID 999 not found." in captured.out
