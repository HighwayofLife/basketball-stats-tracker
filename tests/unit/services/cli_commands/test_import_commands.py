"""Unit tests for import-related CLI command handlers."""

from unittest.mock import patch

from app.services.cli_commands.import_commands import ImportCommands


class TestImportCommands:
    """Test import-related CLI commands."""

    @patch("app.services.cli_commands.import_commands.import_roster_from_csv")
    def test_import_roster_default(self, mock_import):
        """Test roster import with default parameters."""
        test_file = "test_roster.csv"
        mock_import.return_value = None

        ImportCommands.import_roster(test_file)

        mock_import.assert_called_once_with(test_file, False)

    @patch("app.services.cli_commands.import_commands.import_roster_from_csv")
    def test_import_roster_dry_run(self, mock_import):
        """Test roster import with dry run enabled."""
        test_file = "test_roster.csv"
        mock_import.return_value = None

        ImportCommands.import_roster(test_file, dry_run=True)

        mock_import.assert_called_once_with(test_file, True)

    @patch("app.services.cli_commands.import_commands.import_game_stats_from_csv")
    def test_import_game_stats_default(self, mock_import):
        """Test game stats import with default parameters."""
        test_file = "test_game.csv"
        mock_import.return_value = None

        ImportCommands.import_game_stats(test_file)

        mock_import.assert_called_once_with(test_file, False)

    @patch("app.services.cli_commands.import_commands.import_game_stats_from_csv")
    def test_import_game_stats_dry_run(self, mock_import):
        """Test game stats import with dry run enabled."""
        test_file = "test_game.csv"
        mock_import.return_value = None

        ImportCommands.import_game_stats(test_file, dry_run=True)

        mock_import.assert_called_once_with(test_file, True)
