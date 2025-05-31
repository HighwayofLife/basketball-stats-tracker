"""
Integration test for the import-game CLI command to ensure it works with game_stats_template.csv.
"""

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli import cli
from app.data_access.models import Game, Player, PlayerGameStats, PlayerQuarterStats, Team


@pytest.fixture
def cli_runner():
    """Fixture for creating a CLI runner for testing Typer apps."""
    return CliRunner()


@pytest.fixture
def template_csv_path():
    """Fixture to get the absolute path to the template CSV."""
    # Get the path to the project root directory
    project_root = Path(__file__).parent.parent.parent
    return os.path.join(project_root, "game_stats_template.csv")


@pytest.mark.skip(reason="Session isolation issues - functionality tested elsewhere")
def test_import_game_template(cli_runner, template_csv_path, db_session, monkeypatch):
    """Test importing the game_stats_template.csv file via the CLI."""
    # First, ensure the file exists
    assert os.path.exists(template_csv_path), f"Template CSV file not found at {template_csv_path}"

    # Mock the db_manager's get_db_session method to use our test session
    @contextmanager
    def mock_get_db_session():
        try:
            yield db_session
        finally:
            pass

    # Apply the monkeypatch to the db_manager singleton instance
    import app.data_access.database_manager

    monkeypatch.setattr(app.data_access.database_manager.db_manager, "get_db_session", mock_get_db_session)

    # Run the CLI command to import the game stats
    result = cli_runner.invoke(cli, ["import-game", "--file", template_csv_path])

    # Check if the command executed successfully
    assert result.exit_code == 0, f"Command failed with output: {result.stdout}"
    assert "Game stats import completed successfully" in result.stdout

    # Verify that the data was imported correctly
    # Check teams
    teams = db_session.query(Team).all()
    team_names = [team.name for team in teams]
    assert "Team A" in team_names
    assert "Team B" in team_names

    # Check players
    players = db_session.query(Player).all()
    player_names = [player.name for player in players]
    assert "Player One" in player_names
    assert "Player Two" in player_names
    assert "Player Alpha" in player_names
    assert "Player Beta" in player_names

    # Check the game was created
    games = db_session.query(Game).all()
    assert len(games) == 1
    expected_date = datetime.strptime("2025-05-15", "%Y-%m-%d").date()
    assert games[0].date == expected_date

    # Refresh the session to see committed changes
    db_session.commit()
    db_session.expire_all()

    # Check game stats were created
    player_game_stats = db_session.query(PlayerGameStats).all()
    # Also check quarter stats
    player_quarter_stats = db_session.query(PlayerQuarterStats).all()
    print(f"Number of player game stats: {len(player_game_stats)}")
    print(f"Number of player quarter stats: {len(player_quarter_stats)}")
    assert len(player_game_stats) == 4

    # Check quarter stats were created
    player_quarter_stats = db_session.query(PlayerQuarterStats).all()
    assert len(player_quarter_stats) > 0
