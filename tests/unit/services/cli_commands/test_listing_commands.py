"""Unit tests for listing-related CLI command handlers."""

from datetime import date
from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.services.cli_commands.listing_commands import ListingCommands


class TestListingCommands:
    """Test listing-related CLI commands."""

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
        player.jersey_number = 23
        player.position = "PG"
        player.height = 72
        player.weight = 180
        player.year = "Senior"
        player.team.name = "Lakers"
        return player

    @pytest.fixture
    def mock_team(self):
        """Create a mock team object."""
        team = MagicMock()
        team.id = 1
        team.name = "Lakers"
        team.players = []
        return team

    @patch("app.services.cli_commands.listing_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.listing_commands.get_all_games")
    @patch("app.data_access.crud.crud_player_game_stats.get_player_game_stats_by_game")
    def test_list_games_no_filters(self, mock_get_stats, mock_get_games, mock_get_session, mock_game, capsys):
        """Test listing games without filters."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_games.return_value = [mock_game]
        mock_get_stats.return_value = []  # No stats = scheduled game

        # Execute
        ListingCommands.list_games()

        # Verify
        captured = capsys.readouterr()
        assert "Found 1 game(s)" in captured.out
        assert "Lakers" in captured.out
        assert "Warriors" in captured.out
        assert "2024-12-01" in captured.out
        assert "Scheduled" in captured.out

    @patch("app.services.cli_commands.listing_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.listing_commands.get_all_games")
    @patch("app.data_access.crud.crud_player_game_stats.get_player_game_stats_by_game")
    def test_list_games_with_team_filter(self, mock_get_stats, mock_get_games, mock_get_session, mock_game):
        """Test listing games with team filter."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_games.return_value = [mock_game]
        mock_get_stats.return_value = []

        # Execute
        ListingCommands.list_games(team="Lakers")

        # Should still find the game since Lakers is involved

    @patch("app.services.cli_commands.listing_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.listing_commands.get_all_games")
    @patch("app.data_access.crud.crud_player_game_stats.get_player_game_stats_by_game")
    def test_list_games_csv_output(self, mock_get_stats, mock_get_games, mock_get_session, mock_game):
        """Test listing games with CSV output."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_games.return_value = [mock_game]
        mock_get_stats.return_value = []

        # Mock file operations
        m = mock_open()
        with patch("builtins.open", m):
            # Execute
            ListingCommands.list_games(output_format="csv", output_file="test.csv")

        # Verify file was written
        m.assert_called_once_with("test.csv", "w", newline="", encoding="utf-8")

    @patch("app.services.cli_commands.listing_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.listing_commands.get_all_players")
    def test_list_players_no_filters(self, mock_get_players, mock_get_session, mock_player, capsys):
        """Test listing players without filters."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_players.return_value = [mock_player]

        # Execute
        ListingCommands.list_players()

        # Verify
        captured = capsys.readouterr()
        assert "Found 1 player(s)" in captured.out
        assert "John Doe" in captured.out
        assert "Lakers" in captured.out
        assert "23" in captured.out
        assert "PG" in captured.out

    @patch("app.services.cli_commands.listing_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.listing_commands.get_all_players")
    def test_list_players_with_name_filter(self, mock_get_players, mock_get_session, mock_player):
        """Test listing players with name filter."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_players.return_value = [mock_player]

        # Execute
        ListingCommands.list_players(name="John")

        # Should find the player

    @patch("app.services.cli_commands.listing_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.listing_commands.get_all_teams")
    def test_list_teams_simple(self, mock_get_teams, mock_get_session, mock_team, capsys):
        """Test listing teams without players."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_teams.return_value = [mock_team]

        # Execute
        ListingCommands.list_teams()

        # Verify
        captured = capsys.readouterr()
        assert "Found 1 team(s)" in captured.out
        assert "Lakers" in captured.out
        assert "Player Count" in captured.out

    @patch("app.services.cli_commands.listing_commands.db_manager.get_db_session")
    @patch("app.services.cli_commands.listing_commands.get_all_teams")
    def test_list_teams_with_players(self, mock_get_teams, mock_get_session, mock_team, mock_player, capsys):
        """Test listing teams with players."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_team.players = [mock_player]
        mock_get_teams.return_value = [mock_team]

        # Execute
        ListingCommands.list_teams(with_players=True)

        # Verify
        captured = capsys.readouterr()
        assert "Found 1 team(s)" in captured.out
        assert "Lakers" in captured.out
        assert "John Doe" in captured.out
        assert "Jersey #" in captured.out
