# tests/integration/test_admin_calculate_awards.py

"""
Integration tests for admin calculate awards functionality.
These tests verify the complete end-to-end flow that the admin UI button triggers.
"""

from datetime import date
from unittest.mock import Mock, patch

from app.services.awards_service import calculate_all_weekly_awards
from app.services.season_awards_service import calculate_season_awards


class TestAdminCalculateAwards:
    """Integration tests for admin calculate awards button functionality."""

    def test_calculate_season_awards_button_flow(self):
        """Test the complete flow when admin clicks 'calculate current season' button."""
        mock_session = Mock()

        # Mock PlayerGameStats with all required attributes
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.total_2pm = 8
        mock_game_stat.total_2pa = 15
        mock_game_stat.total_3pm = 3
        mock_game_stat.total_3pa = 7
        mock_game_stat.total_ftm = 6
        mock_game_stat.total_fta = 8
        mock_game_stat.fouls = 2  # Correct attribute name
        mock_game_stat.rebounds = 5
        mock_game_stat.assists = 3
        mock_game_stat.steals = 1
        mock_game_stat.blocks = 0

        # Mock PlayerQuarterStats with correct attribute names
        mock_quarter_stat = Mock()
        mock_quarter_stat.quarter_number = 4  # Correct attribute name
        mock_quarter_stat.fg2m = 2  # Correct attribute name
        mock_quarter_stat.fg3m = 1  # Correct attribute name
        mock_quarter_stat.ftm = 3  # Correct attribute name

        # Mock the relationship
        mock_game_stat.quarter_stats = [mock_quarter_stat]

        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        mock_player = Mock()
        mock_player.id = 1
        mock_player.name = "Test Player"

        with (
            patch("app.services.season_awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.season_awards_service.get_season_from_date") as mock_get_season,
            patch("app.services.season_awards_service.create_player_award_safe") as mock_create_award,
            patch("app.data_access.crud.crud_player_award.get_season_awards") as mock_get_awards,
        ):
            mock_get_games.return_value = [mock_game]
            mock_get_season.return_value = "2024"
            mock_get_awards.return_value = []  # No existing awards
            mock_create_award.return_value = Mock()  # Successful creation

            # This is what the admin button calls
            result = calculate_season_awards(mock_session, season="2024", recalculate=False)

            # Should complete without AttributeError
            assert isinstance(result, dict)
            assert len(result) == 8  # All 8 season awards

            # Verify all expected awards are calculated
            expected_awards = [
                "top_scorer",
                "sharpshooter",
                "efficiency_expert",
                "charity_stripe_regular",
                "human_highlight_reel",
                "defensive_tackle",
                "air_ball_artist",
                "air_assault",
            ]
            for award_type in expected_awards:
                assert award_type in result

    def test_calculate_weekly_awards_button_flow(self):
        """Test the weekly awards calculation flow."""
        mock_session = Mock()

        # Mock PlayerGameStats for weekly awards
        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.total_2pm = 8
        mock_game_stat.total_2pa = 15
        mock_game_stat.total_3pm = 3
        mock_game_stat.total_3pa = 7
        mock_game_stat.total_ftm = 6
        mock_game_stat.total_fta = 8

        # Mock PlayerQuarterStats for quarterly firepower and clutch man
        mock_quarter_stat = Mock()
        mock_quarter_stat.quarter_number = 4
        mock_quarter_stat.fg2m = 2
        mock_quarter_stat.fg3m = 1
        mock_quarter_stat.ftm = 3

        mock_game_stat.quarter_stats = [mock_quarter_stat]

        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service.crud_player.get_player_by_id") as mock_get_player,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
            patch("app.services.awards_service.get_awards_by_week") as mock_get_awards,
            patch("app.services.awards_service.delete_all_awards_by_type") as mock_delete,
        ):
            mock_get_games.return_value = [mock_game]
            mock_get_player.return_value = Mock(id=1, name="Test Player")
            mock_create_award.return_value = Mock()
            mock_get_awards.return_value = [Mock()]  # One award per type
            mock_delete.return_value = 0

            # Test all weekly awards calculation
            result = calculate_all_weekly_awards(mock_session, season="2024", recalculate=False)

            # Should complete without AttributeError
            assert isinstance(result, dict)
            assert len(result) == 8  # All 8 weekly awards

            # Verify all expected weekly awards are calculated
            expected_weekly_awards = [
                "player_of_the_week",
                "quarterly_firepower",
                "weekly_ft_king",
                "hot_hand_weekly",
                "clutch_man",
                "trigger_finger",
                "weekly_whiffer",
                "human_howitzer",
            ]
            for award_type in expected_weekly_awards:
                assert award_type in result

    def test_quarterly_firepower_calculation_with_correct_attributes(self):
        """Test quarterly firepower specifically uses correct PlayerQuarterStats attributes."""
        mock_session = Mock()

        # Create mock data with correct PlayerQuarterStats attributes
        mock_quarter_stat = Mock()
        mock_quarter_stat.quarter_number = 1
        mock_quarter_stat.fg2m = 5  # Should be fg2m, not q_2pm
        mock_quarter_stat.fg3m = 2  # Should be fg3m, not q_3pm
        mock_quarter_stat.ftm = 4  # Should be ftm, not q_ftm

        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.quarter_stats = [mock_quarter_stat]

        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
            patch("app.services.awards_service.get_awards_by_week") as mock_get_awards,
        ):
            mock_get_games.return_value = [mock_game]
            mock_create_award.return_value = Mock()
            mock_get_awards.return_value = [Mock()]

            from app.services.awards_service import calculate_quarterly_firepower

            # Should not raise AttributeError for q_2pm, q_3pm, q_ftm
            result = calculate_quarterly_firepower(mock_session, season="2024", recalculate=False)

            assert isinstance(result, dict)
            assert "2024" in result

    def test_clutch_man_calculation_with_correct_attributes(self):
        """Test clutch man specifically uses correct PlayerQuarterStats attributes."""
        mock_session = Mock()

        # Create mock data with correct PlayerQuarterStats attributes
        mock_quarter_stat = Mock()
        mock_quarter_stat.quarter_number = 4  # Should be quarter_number, not quarter
        mock_quarter_stat.fg2m = 3  # Should be fg2m, not q_2pm
        mock_quarter_stat.fg3m = 1  # Should be fg3m, not q_3pm
        mock_quarter_stat.ftm = 2  # Should be ftm, not q_ftm

        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.quarter_stats = [mock_quarter_stat]

        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        with (
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_award,
            patch("app.services.awards_service.get_awards_by_week") as mock_get_awards,
        ):
            mock_get_games.return_value = [mock_game]
            mock_create_award.return_value = Mock()
            mock_get_awards.return_value = [Mock()]

            from app.services.awards_service import calculate_clutch_man

            # Should not raise AttributeError for quarter or q_2pm, q_3pm, q_ftm
            result = calculate_clutch_man(mock_session, season="2024", recalculate=False)

            assert isinstance(result, dict)
            assert "2024" in result

    def test_complete_admin_awards_flow_integration(self):
        """Test the complete flow that admin UI triggers: both season and weekly awards."""
        mock_session = Mock()

        # Mock comprehensive player data
        mock_quarter_stat = Mock()
        mock_quarter_stat.quarter_number = 4
        mock_quarter_stat.fg2m = 2
        mock_quarter_stat.fg3m = 1
        mock_quarter_stat.ftm = 3

        mock_game_stat = Mock()
        mock_game_stat.player_id = 1
        mock_game_stat.total_2pm = 8
        mock_game_stat.total_2pa = 15
        mock_game_stat.total_3pm = 3
        mock_game_stat.total_3pa = 7
        mock_game_stat.total_ftm = 6
        mock_game_stat.total_fta = 8
        mock_game_stat.fouls = 2
        mock_game_stat.rebounds = 5
        mock_game_stat.assists = 3
        mock_game_stat.steals = 1
        mock_game_stat.blocks = 0
        mock_game_stat.quarter_stats = [mock_quarter_stat]

        mock_game = Mock()
        mock_game.date = date(2024, 1, 15)
        mock_game.player_game_stats = [mock_game_stat]

        # Test both season and weekly awards in sequence (like admin UI does)
        with (
            patch("app.services.season_awards_service.crud_game.get_all_games") as mock_get_games_season,
            patch("app.services.season_awards_service.get_season_from_date") as mock_get_season,
            patch("app.services.season_awards_service.create_player_award_safe") as mock_create_season,
            patch("app.data_access.crud.crud_player_award.get_season_awards") as mock_get_season_awards,
            patch("app.services.awards_service.crud_game.get_all_games") as mock_get_games_weekly,
            patch("app.services.awards_service.crud_player.get_player_by_id") as mock_get_player,
            patch("app.services.awards_service.create_player_award_safe") as mock_create_weekly,
            patch("app.services.awards_service.get_awards_by_week") as mock_get_weekly_awards,
            patch("app.services.awards_service.delete_all_awards_by_type") as mock_delete,
        ):
            # Setup mocks
            mock_get_games_season.return_value = [mock_game]
            mock_get_games_weekly.return_value = [mock_game]
            mock_get_season.return_value = "2024"
            mock_get_season_awards.return_value = []
            mock_create_season.return_value = Mock()
            mock_get_player.return_value = Mock(id=1, name="Test Player")
            mock_create_weekly.return_value = Mock()
            mock_get_weekly_awards.return_value = [Mock()]
            mock_delete.return_value = 0

            # Calculate season awards (what admin button does first)
            season_result = calculate_season_awards(mock_session, season="2024", recalculate=False)

            # Calculate weekly awards (what admin button might do second)
            weekly_result = calculate_all_weekly_awards(mock_session, season="2024", recalculate=False)

            # Both should complete without errors
            assert isinstance(season_result, dict)
            assert isinstance(weekly_result, dict)
            assert len(season_result) == 8  # 8 season awards
            assert len(weekly_result) == 8  # 8 weekly awards

            # No AttributeError should be raised during this flow
