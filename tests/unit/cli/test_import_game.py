"""
Unit tests for the import-game CLI command.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from app.cli import cli


@pytest.fixture
def cli_runner():
    """Returns a CLI runner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_import_game_stats():
    """Mocks the import_game_stats_from_csv function."""
    with patch("app.cli.import_game_stats_from_csv") as mock:
        yield mock


def test_import_game_command_success(cli_runner, mock_import_game_stats):
    """Test the import-game command with valid input."""
    # Setup mock to return True for successful import
    mock_import_game_stats.return_value = True

    # Run the CLI command
    result = cli_runner.invoke(cli, ["import-game", "--file", "game_stats_template.csv"])

    # Assertions
    assert result.exit_code == 0
    mock_import_game_stats.assert_called_once_with("game_stats_template.csv", False)


def test_import_game_command_failure(cli_runner, mock_import_game_stats):
    """Test the import-game command when import fails."""
    # Setup mock to return False for failed import
    mock_import_game_stats.return_value = False

    # Run the CLI command
    result = cli_runner.invoke(cli, ["import-game", "--file", "game_stats_template.csv"])

    # Assertions
    assert result.exit_code == 0  # Typer still returns 0 even if our function returns False
    mock_import_game_stats.assert_called_once_with("game_stats_template.csv", False)


def test_import_game_command_dry_run(cli_runner, mock_import_game_stats):
    """Test the import-game command with --dry-run flag."""
    # Setup mock
    mock_import_game_stats.return_value = True

    # Run the CLI command with dry run flag
    result = cli_runner.invoke(cli, ["import-game", "--file", "game_stats_template.csv", "--dry-run"])

    # Assertions
    assert result.exit_code == 0
    mock_import_game_stats.assert_called_once_with("game_stats_template.csv", True)


def test_import_game_command_missing_file(cli_runner):
    """Test the import-game command when file parameter is missing."""
    # Run the CLI command without required file parameter
    result = cli_runner.invoke(cli, ["import-game"])

    # Assertions
    assert result.exit_code != 0
    assert "Missing option" in result.output
