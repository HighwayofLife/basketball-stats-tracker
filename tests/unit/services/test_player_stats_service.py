"""Unit tests for PlayerStatsService."""

from unittest.mock import Mock

import pytest

from app.services.player_stats_service import PlayerStatsService


class TestPlayerStatsService:
    """Test cases for PlayerStatsService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def player_stats_service(self, mock_db_session):
        """Create a PlayerStatsService instance with mock database session."""
        return PlayerStatsService(mock_db_session)

    @pytest.fixture
    def mock_player(self):
        """Create a mock player object."""
        player = Mock()
        player.id = 1
        player.name = "John Doe"
        player.jersey_number = "23"
        player.team_id = 1
        player.position = "PG"
        player.team = Mock()
        player.team.display_name = "Lakers"
        player.team.name = "Lakers"
        return player

    @pytest.fixture
    def mock_game_stats(self):
        """Create mock game stats for testing."""
        stats1 = Mock()
        stats1.fouls = 2
        stats1.total_ftm = 4
        stats1.total_fta = 5
        stats1.total_2pm = 3
        stats1.total_2pa = 6
        stats1.total_3pm = 2
        stats1.total_3pa = 4

        stats2 = Mock()
        stats2.fouls = 3
        stats2.total_ftm = 2
        stats2.total_fta = 3
        stats2.total_2pm = 5
        stats2.total_2pa = 8
        stats2.total_3pm = 1
        stats2.total_3pa = 3

        return [stats1, stats2]

    def test_calculate_effective_fg_percentage(self, player_stats_service):
        """Test effective field goal percentage calculation."""
        # Test normal case
        result = player_stats_service._calculate_effective_fg_percentage(10, 4, 20)
        expected = (10 + 0.5 * 4) / 20 * 100  # (10 + 2) / 20 * 100 = 60.0
        assert result == 60.0

        # Test zero attempts
        result = player_stats_service._calculate_effective_fg_percentage(0, 0, 0)
        assert result == 0

        # Test with only 2-pointers
        result = player_stats_service._calculate_effective_fg_percentage(8, 0, 10)
        expected = 8 / 10 * 100  # 80.0
        assert result == 80.0

    def test_calculate_true_shooting_percentage(self, player_stats_service):
        """Test true shooting percentage calculation."""
        # Test normal case
        result = player_stats_service._calculate_true_shooting_percentage(20, 15, 5)
        expected = 20 / (2 * (15 + 0.44 * 5)) * 100  # 20 / (2 * 17.2) * 100 ≈ 58.14
        assert abs(result - 58.14) < 0.01

        # Test zero attempts
        result = player_stats_service._calculate_true_shooting_percentage(0, 0, 0)
        assert result == 0

        # Test with only field goals
        result = player_stats_service._calculate_true_shooting_percentage(10, 5, 0)
        expected = 10 / (2 * 5) * 100  # 100.0
        assert result == 100.0

    def test_calculate_player_stats(self, player_stats_service, mock_player, mock_game_stats):
        """Test calculation of player statistics."""
        result = player_stats_service._calculate_player_stats(mock_player, mock_game_stats)

        # Verify basic info
        assert result["player_id"] == 1
        assert result["player_name"] == "John Doe"
        assert result["jersey_number"] == "23"
        assert result["team_id"] == 1
        assert result["team_name"] == "Lakers"
        assert result["position"] == "PG"
        assert result["games_played"] == 2

        # Verify aggregated totals
        assert result["total_fouls"] == 5  # 2 + 3
        assert result["total_ftm"] == 6  # 4 + 2
        assert result["total_fta"] == 8  # 5 + 3
        assert result["total_2pm"] == 8  # 3 + 5
        assert result["total_2pa"] == 14  # 6 + 8
        assert result["total_3pm"] == 3  # 2 + 1
        assert result["total_3pa"] == 7  # 4 + 3
        assert result["total_fgm"] == 11  # (3+2) + (5+1) = 8 + 3
        assert result["total_fga"] == 21  # (6+4) + (8+3) = 14 + 7

        # Verify calculated points (FTM + 2PM*2 + 3PM*3)
        assert result["total_points"] == 31  # 6 + (8*2) + (3*3) = 6 + 16 + 9

        # Verify percentages and averages
        assert result["points_per_game"] == 15.5  # 31 / 2
        assert result["fouls_per_game"] == 2.5  # 5 / 2
        assert result["ft_percentage"] == 75.0  # 6/8 * 100
        assert result["fg_percentage"] == 52.4  # 11/21 * 100 (rounded to 1 decimal)
        assert result["fg2_percentage"] == 57.1  # 8/14 * 100 (rounded to 1 decimal)
        assert result["fg3_percentage"] == 42.9  # 3/7 * 100 (rounded to 1 decimal)

    def test_calculate_player_stats_zero_games(self, player_stats_service, mock_player):
        """Test calculation with zero games played."""
        result = player_stats_service._calculate_player_stats(mock_player, [])

        assert result["games_played"] == 0
        assert result["total_points"] == 0
        assert result["points_per_game"] == 0
        assert result["fouls_per_game"] == 0
        assert result["ft_percentage"] == 0
        assert result["fg_percentage"] == 0
        assert result["fg2_percentage"] == 0
        assert result["fg3_percentage"] == 0
        assert result["effective_fg_percentage"] == 0
        assert result["true_shooting_percentage"] == 0

    def test_calculate_player_stats_zero_attempts(self, player_stats_service, mock_player):
        """Test calculation with zero shot attempts."""
        stats = Mock()
        stats.fouls = 1
        stats.total_ftm = 0
        stats.total_fta = 0
        stats.total_2pm = 0
        stats.total_2pa = 0
        stats.total_3pm = 0
        stats.total_3pa = 0

        result = player_stats_service._calculate_player_stats(mock_player, [stats])

        assert result["games_played"] == 1
        assert result["total_points"] == 0
        assert result["points_per_game"] == 0.0
        assert result["fouls_per_game"] == 1.0
        assert result["ft_percentage"] == 0
        assert result["fg_percentage"] == 0
        assert result["fg2_percentage"] == 0
        assert result["fg3_percentage"] == 0
        assert result["effective_fg_percentage"] == 0
        assert result["true_shooting_percentage"] == 0

    def test_get_player_stats_integration(self, player_stats_service, mock_db_session, mock_player, mock_game_stats):
        """Test integration of get_player_stats method."""
        # Mock the database calls
        from unittest.mock import patch

        with (
            patch("app.services.player_stats_service.get_all_players") as mock_get_players,
            patch("app.services.player_stats_service.get_all_player_game_stats_for_player") as mock_get_stats,
        ):
            mock_get_players.return_value = [mock_player]
            mock_get_stats.return_value = mock_game_stats

            result = player_stats_service.get_player_stats()

            assert len(result) == 1
            assert result[0]["player_name"] == "John Doe"
            assert result[0]["total_points"] == 31

            # Verify database session was passed correctly
            mock_get_players.assert_called_once_with(mock_db_session)
            mock_get_stats.assert_called_once_with(mock_db_session, 1)

    def test_get_player_stats_with_team_filter(
        self, player_stats_service, mock_db_session, mock_player, mock_game_stats
    ):
        """Test get_player_stats with team filter."""
        from unittest.mock import patch

        # Create players from different teams
        player1 = Mock()
        player1.id = 1
        player1.team_id = 1
        player1.name = "Player 1"
        player1.jersey_number = "1"
        player1.position = "PG"
        player1.team = Mock()
        player1.team.name = "Team 1"

        player2 = Mock()
        player2.id = 2
        player2.team_id = 2
        player2.name = "Player 2"
        player2.jersey_number = "2"
        player2.position = "SG"
        player2.team = Mock()
        player2.team.name = "Team 2"

        with (
            patch("app.services.player_stats_service.get_all_players") as mock_get_players,
            patch("app.services.player_stats_service.get_all_player_game_stats_for_player") as mock_get_stats,
        ):
            mock_get_players.return_value = [player1, player2]
            mock_get_stats.return_value = []

            # Test filtering by team_id = 1
            result = player_stats_service.get_player_stats(team_id=1)

            assert len(result) == 1
            assert result[0]["player_name"] == "Player 1"
            assert result[0]["team_id"] == 1

            # Verify database session was passed correctly
            mock_get_players.assert_called_once_with(mock_db_session)
