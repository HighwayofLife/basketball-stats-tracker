"""Unit tests for statistics-related CLI command handlers."""

from unittest.mock import MagicMock, patch

from app.services.cli_commands.stats_commands import StatsCommands


class TestStatsCommands:
    """Test statistics-related CLI commands."""

    @patch("app.services.cli_commands.stats_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.stats_commands.SeasonStatsService")
    def test_update_season_stats_no_season(self, mock_service_class, mock_get_session, capsys):
        """Test season stats update without specifying season."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Execute
        StatsCommands.update_season_stats()

        # Verify
        mock_service_class.assert_called_once_with(mock_session)
        mock_service.update_all_season_stats.assert_called_once_with(None)

        captured = capsys.readouterr()
        assert "Updating season statistics for current season..." in captured.out
        assert "Season statistics updated successfully!" in captured.out

    @patch("app.services.cli_commands.stats_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.stats_commands.SeasonStatsService")
    def test_update_season_stats_with_season(self, mock_service_class, mock_get_session, capsys):
        """Test season stats update with specific season."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Execute
        StatsCommands.update_season_stats("2024-2025")

        # Verify
        mock_service_class.assert_called_once_with(mock_session)
        mock_service.update_all_season_stats.assert_called_once_with("2024-2025")

        captured = capsys.readouterr()
        assert "Updating season statistics for 2024-2025..." in captured.out
        assert "Season statistics updated successfully!" in captured.out

    @patch("app.services.cli_commands.stats_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.stats_commands.SeasonStatsService")
    def test_update_season_stats_error(self, mock_service_class, mock_get_session, capsys):
        """Test season stats update with error."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_service = MagicMock()
        mock_service.update_all_season_stats.side_effect = Exception("Database error")
        mock_service_class.return_value = mock_service

        # Execute
        StatsCommands.update_season_stats()

        # Verify
        captured = capsys.readouterr()
        assert "Error updating season statistics: Database error" in captured.out
        assert "Please check that the database has been initialized" in captured.out
