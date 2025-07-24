# tests/unit/services/test_awards_service_comprehensive.py

from datetime import date
from unittest.mock import Mock, patch

import pytest

from app.services.awards_service import _calculate_clutch_man_winners, _calculate_quarterly_firepower_winners


class TestWeeklyAwardsAttributeAccess:
    """Test that weekly award calculations use correct model attributes."""

    @patch("app.services.awards_service.crud_game.get_games_by_date_range")
    def test_quarterly_firepower_uses_correct_quarter_stats_relationship(self, mock_get_games):
        """Test that quarterly firepower uses correct quarter_stats relationship."""
        mock_session = Mock()

        # Create mock PlayerQuarterStats with correct attributes
        mock_quarter_stat1 = Mock()
        mock_quarter_stat1.fg2m = 3  # Correct attribute name
        mock_quarter_stat1.fg3m = 2  # Correct attribute name
        mock_quarter_stat1.ftm = 4  # Correct attribute name

        mock_quarter_stat2 = Mock()
        mock_quarter_stat2.fg2m = 1  # Correct attribute name
        mock_quarter_stat2.fg3m = 1  # Correct attribute name
        mock_quarter_stat2.ftm = 2  # Correct attribute name

        # Create mock PlayerGameStats with correct relationship name
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.quarter_stats = [mock_quarter_stat1, mock_quarter_stat2]  # Correct attribute name

        # Create mock Game
        mock_game = Mock()
        mock_game.player_game_stats = [mock_game_stat]

        # Setup mock
        mock_get_games.return_value = [mock_game]

        week_start = date(2024, 1, 1)
        week_end = date(2024, 1, 7)

        # This should not raise AttributeError about 'player_quarter_stats'
        try:
            result = _calculate_quarterly_firepower_winners(mock_session, [mock_game], week_start, "2024", False)
            assert isinstance(result, list)
        except AttributeError as e:
            if "player_quarter_stats" in str(e):
                pytest.fail(f"PlayerGameStats 'player_quarter_stats' attribute error: {e}")
            else:
                raise

    @patch("app.services.awards_service.crud_game.get_games_by_date_range")
    def test_clutch_man_uses_correct_quarter_stats_relationship(self, mock_get_games):
        """Test that clutch man calculation uses correct quarter_stats relationship."""
        mock_session = Mock()

        # Create mock PlayerQuarterStats for Q4
        mock_q4_stat = Mock()
        mock_q4_stat.quarter_number = 4  # Q4 - correct attribute name
        mock_q4_stat.fg2m = 2  # Correct attribute name
        mock_q4_stat.fg3m = 1  # Correct attribute name
        mock_q4_stat.ftm = 3  # Correct attribute name

        mock_other_quarter = Mock()
        mock_other_quarter.quarter_number = 1  # Q1 (should be ignored) - correct attribute name
        mock_other_quarter.fg2m = 5  # Correct attribute name
        mock_other_quarter.fg3m = 2  # Correct attribute name
        mock_other_quarter.ftm = 1  # Correct attribute name

        # Create mock PlayerGameStats with correct relationship name
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.quarter_stats = [mock_q4_stat, mock_other_quarter]  # Correct attribute name

        # Create mock Game
        mock_game = Mock()
        mock_game.player_game_stats = [mock_game_stat]

        # Setup mock
        mock_get_games.return_value = [mock_game]

        week_start = date(2024, 1, 1)
        week_end = date(2024, 1, 7)

        # This should not raise AttributeError about 'player_quarter_stats'
        try:
            result = _calculate_clutch_man_winners(mock_session, [mock_game], week_start, "2024", False)
            assert isinstance(result, list)
        except AttributeError as e:
            if "player_quarter_stats" in str(e):
                pytest.fail(f"PlayerGameStats 'player_quarter_stats' attribute error: {e}")
            else:
                raise

    @patch("app.services.awards_service.crud_game.get_games_by_date_range")
    def test_quarterly_firepower_empty_quarter_stats(self, mock_get_games):
        """Test quarterly firepower with empty quarter stats."""
        mock_session = Mock()

        # Create mock PlayerGameStats with empty quarter_stats
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.quarter_stats = []  # Empty quarter stats

        # Create mock Game
        mock_game = Mock()
        mock_game.player_game_stats = [mock_game_stat]

        # Setup mock
        mock_get_games.return_value = [mock_game]

        week_start = date(2024, 1, 1)
        week_end = date(2024, 1, 7)

        # Should handle empty quarter stats gracefully
        result = _calculate_quarterly_firepower_winners(mock_session, [mock_game], week_start, "2024", False)
        assert result == []

    @patch("app.services.awards_service.crud_game.get_games_by_date_range")
    def test_clutch_man_no_q4_stats(self, mock_get_games):
        """Test clutch man with no Q4 stats."""
        mock_session = Mock()

        # Create mock PlayerQuarterStats for non-Q4 quarters only
        mock_q1_stat = Mock()
        mock_q1_stat.quarter = 1
        mock_q1_stat.q_2pm = 2
        mock_q1_stat.q_3pm = 1
        mock_q1_stat.q_ftm = 3

        mock_q2_stat = Mock()
        mock_q2_stat.quarter = 2
        mock_q2_stat.q_2pm = 1
        mock_q2_stat.q_3pm = 2
        mock_q2_stat.q_ftm = 1

        # Create mock PlayerGameStats with no Q4 stats
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.quarter_stats = [mock_q1_stat, mock_q2_stat]  # No Q4

        # Create mock Game
        mock_game = Mock()
        mock_game.player_game_stats = [mock_game_stat]

        # Setup mock
        mock_get_games.return_value = [mock_game]

        week_start = date(2024, 1, 1)
        week_end = date(2024, 1, 7)

        # Should handle missing Q4 stats gracefully
        result = _calculate_clutch_man_winners(mock_session, [mock_game], week_start, "2024", False)
        assert result == []


class TestAwardsServiceRegressionTests:
    """Regression tests to prevent common attribute errors."""

    def test_player_game_stats_has_quarter_stats_relationship(self):
        """Test that PlayerGameStats model has quarter_stats relationship."""
        from app.data_access.models import PlayerGameStats

        # Verify the relationship exists (this will fail if the model changes)
        assert hasattr(PlayerGameStats, "quarter_stats"), "PlayerGameStats must have 'quarter_stats' relationship"

        # Check it's not called 'player_quarter_stats'
        assert not hasattr(PlayerGameStats, "player_quarter_stats"), (
            "PlayerGameStats should not have 'player_quarter_stats' attribute"
        )

    def test_player_game_stats_has_fouls_attribute(self):
        """Test that PlayerGameStats model has fouls attribute."""
        from app.data_access.models import PlayerGameStats

        # Verify the attribute exists
        assert hasattr(PlayerGameStats, "fouls"), "PlayerGameStats must have 'fouls' attribute"

        # Check it's not called 'total_fouls'
        assert not hasattr(PlayerGameStats, "total_fouls"), "PlayerGameStats should not have 'total_fouls' attribute"
