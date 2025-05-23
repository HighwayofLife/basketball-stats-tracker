"""
Integration test for the import-game CLI command with the real game_stats_template.csv file.
"""

import os
import shutil
import tempfile
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typer.testing import CliRunner

from app.cli import cli
from app.data_access.database_manager import DatabaseManager
from app.data_access.models import Base, Game, Player, PlayerGameStats, PlayerQuarterStats, Team


class TestImportGameIntegration:
    """Integration tests for the import-game CLI command."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up a temporary directory and database for testing."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()

        # Create a temporary database
        self.db_path = os.path.join(self.temp_dir, "test_db.sqlite")
        self.db_url = f"sqlite:///{self.db_path}"

        # Setup the database
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)

        # Setup a session
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        # Create a temporary DatabaseManager and patch it
        self.original_db_manager = None

        # Get project root directory and CSV paths
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.template_csv_path = os.path.join(project_root, "game_stats_template.csv")
        self.test_csv_path = os.path.join(self.temp_dir, "game_stats_template.csv")
        shutil.copy(self.template_csv_path, self.test_csv_path)

        # Setup CLI runner
        self.runner = CliRunner()

        # Patch the database manager
        import app.data_access.database_manager as db_manager_module

        self.original_db_manager = db_manager_module.db_manager

        # Create a new DatabaseManager instance
        new_db_manager = DatabaseManager()

        # Override get_engine and get_db_session methods to use our test database
        original_get_engine = new_db_manager.get_engine
        new_db_manager.get_engine = lambda db_url=None: original_get_engine(self.db_url)

        # Replace the global db_manager with our test instance
        db_manager_module.db_manager = new_db_manager

        yield

        # Clean up
        self.db.close()

        # Restore the original database manager
        if self.original_db_manager:
            import app.data_access.database_manager as db_manager_module

            db_manager_module.db_manager = self.original_db_manager

        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_import_game_with_real_csv(self):
        """Test importing game stats from the actual template CSV file."""
        # Run the import command with the real CSV file
        result = self.runner.invoke(cli, ["import-game", "--file", self.test_csv_path])

        # Check that the command executed successfully
        assert result.exit_code == 0

        # Verify database contents
        # 1. Check teams
        teams = self.db.query(Team).all()
        assert len(teams) == 2
        team_names = [team.name for team in teams]
        assert "Team A" in team_names
        assert "Team B" in team_names

        # 2. Check players
        players = self.db.query(Player).all()
        assert len(players) == 4
        player_names = [player.name for player in players]
        assert "Player One" in player_names
        assert "Player Two" in player_names
        assert "Player Alpha" in player_names
        assert "Player Beta" in player_names

        # 3. Check game
        game = self.db.query(Game).first()
        assert game is not None
        expected_date = datetime.strptime("2025-05-15", "%Y-%m-%d").date()
        assert game.date == expected_date

        # 4. Check player game stats
        player_game_stats = self.db.query(PlayerGameStats).all()
        assert len(player_game_stats) == 4  # One for each player

        # 5. Check player quarter stats
        player_quarter_stats = self.db.query(PlayerQuarterStats).all()
        # Should have multiple quarter stats (not empty)
        assert len(player_quarter_stats) > 0

        # Additional check: verify player quarter stats exist
        # We should have at least one player with QT1 stats for the "22-1x" pattern

        # First find Team A
        team_a = self.db.query(Team).filter(Team.name == "Team A").first()
        assert team_a is not None

        # Find Player One
        player_one = self.db.query(Player).filter((Player.name == "Player One") & (Player.team_id == team_a.id)).first()
        assert player_one is not None

        # Find the game
        game = self.db.query(Game).first()
        assert game is not None

        # Get game stats for player one
        game_stats = (
            self.db.query(PlayerGameStats)
            .filter((PlayerGameStats.player_id == player_one.id) & (PlayerGameStats.game_id == game.id))
            .first()
        )
        assert game_stats is not None

        # Get quarter stats for the first quarter
        quarter_stats = (
            self.db.query(PlayerQuarterStats)
            .filter(
                (PlayerQuarterStats.player_game_stat_id == game_stats.id) & (PlayerQuarterStats.quarter_number == 1)
            )
            .first()
        )

        # Check the quarter stats reflect the "22-1x" pattern from the CSV
        assert quarter_stats is not None
        assert quarter_stats.ftm == 1  # Made 1 free throw
        assert quarter_stats.fta == 2  # Attempted 2 free throws
        assert quarter_stats.fg2m == 2  # Made 2 two-pointers
        assert quarter_stats.fg2a == 3  # Attempted 3 two-pointers
