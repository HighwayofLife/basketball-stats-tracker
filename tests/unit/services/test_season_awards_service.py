# tests/unit/services/test_season_awards_service.py

from datetime import date
from unittest.mock import Mock, patch

import pytest

from app.services.season_awards_service import _get_season_player_stats


class TestPlayerSeasonStats:
    """Test season statistics aggregation functions."""

    def test_get_player_season_stats_aggregates_correctly(self):
        """Test that player season stats are aggregated correctly from game stats."""
        # Mock Game objects with PlayerGameStats
        mock_game1 = Mock()
        mock_game1.date = date(2024, 1, 15)

        mock_game2 = Mock()
        mock_game2.date = date(2024, 2, 15)

        # Mock PlayerGameStats objects with correct attribute names
        mock_stat1 = Mock()
        mock_stat1.player_id = 1
        mock_stat1.total_2pm = 5
        mock_stat1.total_2pa = 10
        mock_stat1.total_3pm = 2
        mock_stat1.total_3pa = 6
        mock_stat1.total_ftm = 8
        mock_stat1.total_fta = 10
        mock_stat1.fouls = 3  # Note: PlayerGameStats has 'fouls', not 'total_fouls'

        mock_stat2 = Mock()
        mock_stat2.player_id = 1  # Same player, different game
        mock_stat2.total_2pm = 3
        mock_stat2.total_2pa = 8
        mock_stat2.total_3pm = 1
        mock_stat2.total_3pa = 4
        mock_stat2.total_ftm = 4
        mock_stat2.total_fta = 6
        mock_stat2.fouls = 2

        mock_stat3 = Mock()
        mock_stat3.player_id = 2  # Different player
        mock_stat3.total_2pm = 6
        mock_stat3.total_2pa = 12
        mock_stat3.total_3pm = 0
        mock_stat3.total_3pa = 2
        mock_stat3.total_ftm = 5
        mock_stat3.total_fta = 7
        mock_stat3.fouls = 1

        # Assign game stats to games
        mock_game1.player_game_stats = [mock_stat1, mock_stat3]
        mock_game2.player_game_stats = [mock_stat2]

        mock_session = Mock()

        # Mock the crud calls and functions
        with (
            patch("app.services.season_awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.season_awards_service.get_season_from_date") as mock_get_season,
        ):
            mock_get_games.return_value = [mock_game1, mock_game2]
            mock_get_season.side_effect = lambda d: "2024"  # All games are in 2024

            result = _get_season_player_stats(mock_session, "2024")

        # Verify player 1 aggregation
        assert 1 in result
        player1_stats = result[1]
        assert player1_stats["total_2pm"] == 8  # 5 + 3
        assert player1_stats["total_2pa"] == 18  # 10 + 8
        assert player1_stats["total_3pm"] == 3  # 2 + 1
        assert player1_stats["total_3pa"] == 10  # 6 + 4
        assert player1_stats["total_ftm"] == 12  # 8 + 4
        assert player1_stats["total_fta"] == 16  # 10 + 6
        assert player1_stats["total_fouls"] == 5  # 3 + 2

        # Verify player 2 aggregation
        assert 2 in result
        player2_stats = result[2]
        assert player2_stats["total_2pm"] == 6
        assert player2_stats["total_2pa"] == 12
        assert player2_stats["total_3pm"] == 0
        assert player2_stats["total_3pa"] == 2
        assert player2_stats["total_ftm"] == 5
        assert player2_stats["total_fta"] == 7
        assert player2_stats["total_fouls"] == 1

    def test_get_player_season_stats_empty_input(self):
        """Test that empty game stats return empty result."""
        mock_session = Mock()
        with patch("app.services.season_awards_service.crud_game.get_all_games") as mock_get_games:
            mock_get_games.return_value = []
            result = _get_season_player_stats(mock_session, "2024")
            assert result == {}

    def test_get_player_season_stats_single_player_single_game(self):
        """Test aggregation with single player and single game."""
        mock_stat = Mock()
        mock_stat.player_id = 42
        mock_stat.total_2pm = 7
        mock_stat.total_2pa = 15
        mock_stat.total_3pm = 3
        mock_stat.total_3pa = 8
        mock_stat.total_ftm = 6
        mock_stat.total_fta = 8
        mock_stat.fouls = 4

        mock_game = Mock()
        mock_game.date = date(2024, 1, 1)
        mock_game.player_game_stats = [mock_stat]

        mock_session = Mock()
        with (
            patch("app.services.season_awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.season_awards_service.get_season_from_date") as mock_get_season,
        ):
            mock_get_games.return_value = [mock_game]
            mock_get_season.return_value = "2024"
            result = _get_season_player_stats(mock_session, "2024")

        assert len(result) == 1
        assert 42 in result
        player_stats = result[42]
        assert player_stats["total_2pm"] == 7
        assert player_stats["total_2pa"] == 15
        assert player_stats["total_3pm"] == 3
        assert player_stats["total_3pa"] == 8
        assert player_stats["total_ftm"] == 6
        assert player_stats["total_fta"] == 8
        assert player_stats["total_fouls"] == 4


class TestSeasonAwardsEndToEnd:
    """End-to-end tests for season awards calculation to catch attribute errors."""

    @patch("app.services.season_awards_service.crud_game.get_all_games")
    @patch("app.services.season_awards_service.get_season_from_date")
    @patch("app.services.season_awards_service.create_player_award_safe")
    def test_calculate_top_scorer_uses_correct_attributes(self, mock_create_award, mock_get_season, mock_get_games):
        """Test that calculate_top_scorer uses correct PlayerGameStats attributes."""
        from app.services.season_awards_service import calculate_top_scorer

        # Create mock PlayerGameStats with correct attributes
        mock_stat = Mock()
        mock_stat.player_id = 1
        mock_stat.total_2pm = 10
        mock_stat.total_2pa = 20
        mock_stat.total_3pm = 5
        mock_stat.total_3pa = 10
        mock_stat.total_ftm = 8
        mock_stat.total_fta = 10
        mock_stat.fouls = 3  # Correct attribute name, not 'total_fouls'

        # Create mock game
        mock_game = Mock()
        mock_game.date = Mock()
        mock_game.player_game_stats = [mock_stat]

        # Setup mocks
        mock_get_games.return_value = [mock_game]
        mock_get_season.return_value = "2024"
        mock_create_award.return_value = Mock()

        mock_session = Mock()

        # This should not raise an AttributeError
        try:
            result = calculate_top_scorer(mock_session, "2024", recalculate=False)
            assert isinstance(result, int)
        except AttributeError as e:
            if "total_fouls" in str(e):
                pytest.fail(f"PlayerGameStats 'total_fouls' attribute error: {e}")
            else:
                raise

    @patch("app.services.season_awards_service.crud_game.get_all_games")
    @patch("app.services.season_awards_service.get_season_from_date")
    @patch("app.services.season_awards_service.create_player_award_safe")
    def test_calculate_defensive_tackle_uses_correct_attributes(
        self, mock_create_award, mock_get_season, mock_get_games
    ):
        """Test that calculate_defensive_tackle uses correct fouls attribute."""
        from app.services.season_awards_service import calculate_defensive_tackle

        # Create mock PlayerGameStats with correct attributes
        mock_stat1 = Mock()
        mock_stat1.player_id = 1
        mock_stat1.total_2pm = 5
        mock_stat1.total_2pa = 10
        mock_stat1.total_3pm = 2
        mock_stat1.total_3pa = 5
        mock_stat1.total_ftm = 3
        mock_stat1.total_fta = 4
        mock_stat1.fouls = 1  # Low fouls (good for this award)

        mock_stat2 = Mock()
        mock_stat2.player_id = 2
        mock_stat2.total_2pm = 8
        mock_stat2.total_2pa = 15
        mock_stat2.total_3pm = 1
        mock_stat2.total_3pa = 3
        mock_stat2.total_ftm = 5
        mock_stat2.total_fta = 7
        mock_stat2.fouls = 5  # High fouls (bad for this award)

        # Create mock games
        mock_game1 = Mock()
        mock_game1.date = Mock()
        mock_game1.player_game_stats = [mock_stat1]

        mock_game2 = Mock()
        mock_game2.date = Mock()
        mock_game2.player_game_stats = [mock_stat2]

        # Setup mocks
        mock_get_games.return_value = [mock_game1, mock_game2]
        mock_get_season.return_value = "2024"
        mock_create_award.return_value = Mock()

        mock_session = Mock()

        # This should not raise an AttributeError about 'total_fouls'
        try:
            result = calculate_defensive_tackle(mock_session, "2024", recalculate=False)
            assert isinstance(result, int)
        except AttributeError as e:
            if "total_fouls" in str(e):
                pytest.fail(f"PlayerGameStats 'total_fouls' attribute error: {e}")
            else:
                raise
